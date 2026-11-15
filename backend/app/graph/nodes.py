"""Deterministic (non-LLM) graph nodes for the multi-agent workflow.

Three nodes:
  initialize_run_node  — validates the run, logs workflow_start event
  finalize_report_node — uses Phase 2 report generation on all collected evidence
  fail_workflow_node   — marks run failed, cleans up running tasks, logs event

All three follow the same contract: accept (state, config) and return a
partial state update dict.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from langchain_core.runnables import RunnableConfig

from app.core.database import AsyncSessionLocal
from app.core.errors import safe_error_message
from app.graph.state import ResearchWorkflowState
from app.providers.llm import get_llm_provider

logger = logging.getLogger(__name__)


async def initialize_run_node(
    state: ResearchWorkflowState,
    config: RunnableConfig,
) -> dict:
    """Validate the run record and log workflow_start.

    Returns ``{"workflow_status": "planning"}`` on success.
    Returns ``{"workflow_status": "failed", "error_message": ...}`` if the
    run record is missing, already completed, or has an unexpected status.
    """
    run_id = state["run_id"]

    try:
        from app.models.run import ResearchRun
        from app.services.event_service import log_event, publish_event
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            run_result = await db.execute(select(ResearchRun).where(ResearchRun.id == run_id))
            run = run_result.scalar_one_or_none()

            if run is None:
                return {
                    "workflow_status": "failed",
                    "error_message": f"Run {run_id} not found in database.",
                }

            if run.status not in ("running", "pending"):
                return {
                    "workflow_status": "failed",
                    "error_message": (
                        f"Run {run_id} has unexpected status '{run.status}' "
                        "at graph initialization."
                    ),
                }

            run.current_stage = "Initializing"

            _ev = await log_event(
                db,
                run_id=run_id,
                agent_name="system",
                event_type="workflow_start",
                summary="Multi-agent workflow started",
                iteration=0,
            )
            await db.commit()
            await publish_event(_ev)

        logger.info("initialize_run_node: run %s initialised", run_id)
        return {"workflow_status": "planning"}

    except Exception as exc:
        logger.error("initialize_run_node: failed for run %s: %s", run_id, exc)
        return {
            "workflow_status": "failed",
            "error_message": safe_error_message(exc),
        }


async def finalize_report_node(
    state: ResearchWorkflowState,
    config: RunnableConfig,
) -> dict:
    """Generate the research report from all collected evidence.

    Reuses Phase 2 functions unchanged:
      build_evidence_context(), build_prompt(), generate_report()

    Loads evidence content fresh from the DB (evidence content is NOT
    in state — only IDs are stored there).

    In the multi-agent workflow, this node generates the report (draft) and
    returns workflow_status="claim_verifying" so the graph routes to
    claim_extraction_node.  In the sequential workflow this node handles claim
    verification inline (no critic).

    Returns ``{"workflow_status": "claim_verifying"|"completed", "final_report_id": ...}``.
    """
    run_id = state["run_id"]
    research_question = state["research_question"]
    # Read workflow_mode from the DB run record — never trust state for this field
    # because the checkpointer may not persist it across node boundaries.
    iteration = state.get("iteration_count", 0)

    try:
        from app.models.run import ResearchRun
        from app.models.evidence import EvidenceRecord
        from app.models.report import ResearchReport
        from app.services.context_builder import build_evidence_context, build_prompt, SYSTEM_PROMPT
        from app.services.report_generator import generate_report
        from app.services.evidence_normalizer import NormalizedEvidence
        from app.services.event_service import log_event, publish_event
        from app.core.config import settings
        from sqlalchemy import select

        llm = get_llm_provider()

        # Load run to determine workflow_mode reliably from DB
        async with AsyncSessionLocal() as db:
            run_mode_result = await db.execute(
                select(ResearchRun).where(ResearchRun.id == run_id)
            )
            run_for_mode = run_mode_result.scalar_one_or_none()
            workflow_mode = (
                run_for_mode.workflow_mode if run_for_mode else "sequential"
            ) or "sequential"

        # Load all evidence records for this run
        async with AsyncSessionLocal() as db:
            ev_result = await db.execute(
                select(EvidenceRecord).where(EvidenceRecord.run_id == run_id)
            )
            evidence_rows = ev_result.scalars().all()

        # Convert ORM rows back to NormalizedEvidence for Phase 2 functions
        evidence_list: list[NormalizedEvidence] = []
        for row in evidence_rows:
            ev = NormalizedEvidence(
                source_type=row.source_type,
                content=row.content or "",
                source_label=row.source_label or "",
                relevance_score=row.relevance_score,
                url=row.url,
                page_title=row.page_title,
                retrieved_at=row.retrieved_at,
                document_id=row.document_id,
                filename=None,
                chunk_index=row.chunk_index,
                page_number=row.page_number,
            )
            evidence_list.append(ev)

        if not evidence_list:
            logger.warning("finalize_report_node: no evidence found for run %s", run_id)
            # Allow Phase 2 to handle empty evidence gracefully

        # Phase 2 context builder — selects and labels evidence within budget
        selected_evidence = build_evidence_context(
            evidence_list,
            research_question,
            budget_chars=settings.LLM_CONTEXT_BUDGET_CHARS,
        )

        user_prompt = build_prompt(selected_evidence, research_question)

        report_data, raw_llm_response = await generate_report(
            llm=llm,
            research_question=research_question,
            evidence_list=selected_evidence,
            user_prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT,
            max_retries=1,
        )

        # Persist report — upsert: if a report already exists for this run
        # (e.g. critic requested revise_report), update it rather than insert.
        async with AsyncSessionLocal() as db:
            existing_r = await db.execute(
                select(ResearchReport).where(ResearchReport.run_id == run_id)
                .order_by(ResearchReport.generated_at.desc())
                .limit(1)
            )
            existing_report = existing_r.scalar_one_or_none()

            if existing_report:
                # Update existing report with fresh LLM output
                report_id = existing_report.id
                for field, value in report_data.items():
                    setattr(existing_report, field, value)
                existing_report.raw_llm_response = (
                    raw_llm_response[:10000] if raw_llm_response else None
                )
                existing_report.generated_at = datetime.now(timezone.utc)
                logger.info(
                    "finalize_report_node: updated existing report %s for run %s",
                    report_id, run_id,
                )
            else:
                report_id = str(uuid.uuid4())
                report = ResearchReport(
                    id=report_id,
                    run_id=run_id,
                    raw_llm_response=raw_llm_response[:10000] if raw_llm_response else None,
                    generated_at=datetime.now(timezone.utc),
                    **report_data,
                )
                db.add(report)

            _ev_draft = await log_event(
                db,
                run_id=run_id,
                agent_name="system",
                event_type="report_draft",
                summary=f"Research report draft generated ({len(selected_evidence)} evidence items used)",
                output_ref=f"report_id:{report_id}",
                iteration=iteration,
            )
            await db.commit()
            await publish_event(_ev_draft)

        logger.info(
            "finalize_report_node: report draft persisted for run %s, report %s",
            run_id, report_id
        )

        # ── Multi-agent: route to claim_extraction_node then critic ───────────
        if workflow_mode == "multi_agent":
            return {
                "workflow_status": "claim_verifying",
                "final_report_id": report_id,
            }

        # ── Sequential: run claim verification inline; mark run completed ─────
        run_result_state: dict = {
            "final_report_id": report_id,
            "claim_ids": [],
            "verification_summary": None,
        }

        try:
            from app.services.claim_verifier import verify_claims_for_run

            depth = state.get("verification_depth", "basic") or settings.VERIFICATION_DEPTH

            async with AsyncSessionLocal() as db:
                v_summary = await verify_claims_for_run(
                    db=db,
                    run_id=run_id,
                    report_id=report_id,
                    depth=depth,
                    max_claims=settings.MAX_CLAIMS_PER_RUN,
                    llm_provider=llm,
                )
                await db.commit()
            run_result_state["verification_summary"] = v_summary
            run_result_state["claim_ids"] = v_summary.get("claim_ids", [])
            logger.info(
                "finalize_report_node: sequential claim verification done — %d claims",
                len(run_result_state["claim_ids"]),
            )
        except Exception as verif_exc:
            logger.warning(
                "finalize_report_node: sequential claim verification failed: %s", verif_exc
            )

        # Mark run completed
        async with AsyncSessionLocal() as db:
            run_result = await db.execute(select(ResearchRun).where(ResearchRun.id == run_id))
            run = run_result.scalar_one_or_none()
            if run:
                run.status = "completed"
                run.current_stage = "Complete"
                run.completed_at = datetime.now(timezone.utc)

            _ev_wf = await log_event(
                db,
                run_id=run_id,
                agent_name="system",
                event_type="workflow_complete",
                summary="Research completed — sequential workflow",
                output_ref=f"report_id:{report_id}",
                iteration=iteration,
            )
            await db.commit()
            await publish_event(_ev_wf)

        run_result_state["workflow_status"] = "completed"
        return run_result_state

    except Exception as exc:
        logger.error("finalize_report_node: failed for run %s: %s", run_id, exc)
        return {
            "workflow_status": "failed",
            "error_message": safe_error_message(exc),
        }


async def claim_extraction_node(
    state: ResearchWorkflowState,
    config: RunnableConfig,
) -> dict:
    """Run claim verification for a multi-agent run after the report draft.

    Calls the shared verify_claims_for_run service (no app.graph.* imports).
    Always non-fatal — if verification fails the workflow continues to critic_node
    with an empty verification_summary.

    Returns partial state with claim_ids and verification_summary.
    """
    run_id = state["run_id"]
    report_id = state.get("final_report_id")

    # Checkpointer may not persist final_report_id — fall back to DB lookup
    if not report_id:
        try:
            from app.models.report import ResearchReport
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                r = await db.execute(
                    select(ResearchReport.id)
                    .where(ResearchReport.run_id == run_id)
                    .order_by(ResearchReport.created_at.desc())
                    .limit(1)
                )
                report_id = r.scalar_one_or_none()
        except Exception:
            pass

    if not report_id:
        logger.warning(
            "claim_extraction_node: no report_id found for run %s — skipping", run_id
        )
        return {"verification_summary": None, "claim_ids": []}

    try:
        from app.services.claim_verifier import verify_claims_for_run
        from app.core.config import settings

        llm = get_llm_provider()
        depth = state.get("verification_depth", "basic") or settings.VERIFICATION_DEPTH

        async with AsyncSessionLocal() as db:
            v_summary = await verify_claims_for_run(
                db=db,
                run_id=run_id,
                report_id=report_id,
                depth=depth,
                max_claims=settings.MAX_CLAIMS_PER_RUN,
                llm_provider=llm,
            )
            await db.commit()

        claim_ids = v_summary.get("claim_ids", [])
        logger.info(
            "claim_extraction_node: %d claims verified for run %s", len(claim_ids), run_id
        )
        return {
            "verification_summary": v_summary,
            "claim_ids": claim_ids,
        }

    except Exception as exc:
        logger.warning(
            "claim_extraction_node: verification failed for run %s: %s — continuing", run_id, exc
        )
        return {"verification_summary": None, "claim_ids": []}


async def critic_node(
    state: ResearchWorkflowState,
    config: RunnableConfig,
) -> dict:
    """Critic / Reviewer Agent node — multi-agent runs only.

    Evaluates research quality and produces a CriticReview record.
    Increments critic_cycles counter.

    Returns critic_review_id, critic_decision, critic_cycles in state update.
    The Supervisor then decides whether to approve, revise, or terminate based
    on critic_decision and the current critic_cycles count.
    """
    run_id = state["run_id"]
    research_question = state["research_question"]
    report_id = state.get("final_report_id")
    current_cycles = state.get("critic_cycles", 0)
    verification_summary = state.get("verification_summary")
    iteration = state.get("iteration_count", 0)

    new_cycles = current_cycles + 1

    try:
        from app.models.report import ResearchReport
        from app.models.critic_review import CriticReview
        from app.agents.critic import run_critic_review
        from app.services.event_service import log_event, publish_event
        from sqlalchemy import select
        import json as _json

        # Checkpointer may not persist final_report_id — fall back to DB lookup
        if not report_id:
            try:
                async with AsyncSessionLocal() as db:
                    r = await db.execute(
                        select(ResearchReport.id)
                        .where(ResearchReport.run_id == run_id)
                        .order_by(ResearchReport.created_at.desc())
                        .limit(1)
                    )
                    report_id = r.scalar_one_or_none()
            except Exception:
                pass

        if not report_id:
            logger.error("critic_node: no report_id found for run %s", run_id)
            return {
                "critic_decision": "revise_report",
                "critic_review_id": None,
                "critic_cycles": new_cycles,
                "supervisor_decision": "revise_report",
                "workflow_status": "finalizing",
            }

        # Load report for critic context
        async with AsyncSessionLocal() as db:
            rpt_result = await db.execute(
                select(ResearchReport).where(ResearchReport.id == report_id)
            )
            rpt = rpt_result.scalar_one_or_none()

        if rpt is None:
            logger.error(
                "critic_node: report %s not found for run %s", report_id, run_id
            )
            return {
                "critic_decision": "revise_report",
                "critic_review_id": None,
                "critic_cycles": new_cycles,
                "supervisor_decision": "revise_report",
                "workflow_status": "finalizing",
            }

        # Build report dict for critic
        def _safe_json_list(val: str | None) -> list:
            if not val:
                return []
            try:
                result = _json.loads(val)
                return result if isinstance(result, list) else [val]
            except Exception:
                return [val] if val else []

        report_dict = {
            "executive_summary": rpt.executive_summary or "",
            "key_findings": _safe_json_list(rpt.key_findings),
            "observations": rpt.observations or "",
            "contradictions": rpt.contradictions or "",
            "limitations": rpt.limitations or "",
            "sources": _safe_json_list(rpt.sources),
        }

        llm = get_llm_provider()

        # Run the critic review
        review_data = await run_critic_review(
            run_id=run_id,
            research_question=research_question,
            report=report_dict,
            review_version=new_cycles,
            verification_summary=verification_summary,
            llm_provider=llm,
        )

        # Enforce max review cycles — prevent infinite review loops
        from app.core.config import settings
        max_critic_cycles = settings.CRITIC_MAX_REVIEW_CYCLES
        if new_cycles >= max_critic_cycles and review_data["recommended_action"] not in (
            "approve_report",
            "reject",
        ):
            if review_data["overall_assessment"] in ("strong", "adequate"):
                review_data["recommended_action"] = "approve_report"
                review_data["review_status"] = "approved"
            else:
                review_data["recommended_action"] = "mark_needs_attention"
                review_data["review_status"] = "needs_attention"
            logger.info(
                "critic_node: reached max review cycles (%d/%d) — forced recommended_action=%s",
                new_cycles,
                max_critic_cycles,
                review_data["recommended_action"],
            )

        # Persist CriticReview
        review_id = review_data["id"]
        async with AsyncSessionLocal() as db:
            review = CriticReview(
                id=review_id,
                run_id=run_id,
                review_version=review_data["review_version"],
                overall_assessment=review_data["overall_assessment"],
                review_status=review_data["review_status"],
                recommended_action=review_data["recommended_action"],
                unsupported_claims=review_data.get("unsupported_claims"),
                citation_issues=review_data.get("citation_issues"),
                contradictory_findings=review_data.get("contradictory_findings"),
                missing_evidence=review_data.get("missing_evidence"),
                source_quality_issues=review_data.get("source_quality_issues"),
                reasoning_issues=review_data.get("reasoning_issues"),
                review_summary=review_data.get("review_summary"),
                created_at=review_data["created_at"],
            )
            db.add(review)

            _ev_critic = await log_event(
                db,
                run_id=run_id,
                agent_name="critic",
                event_type="critic_review",
                summary=(
                    f"Critic review {new_cycles}: {review_data['overall_assessment']} — "
                    f"{review_data['recommended_action']}"
                ),
                output_ref=f"review_id:{review_id}",
                iteration=iteration,
            )
            await db.commit()
            await publish_event(_ev_critic)

        critic_decision = review_data["recommended_action"]
        logger.info(
            "critic_node: review %d for run %s — assessment=%s, action=%s",
            new_cycles, run_id, review_data["overall_assessment"], critic_decision,
        )

        return {
            "critic_review_id": review_id,
            "critic_decision": critic_decision,
            "critic_cycles": new_cycles,
            "supervisor_decision": critic_decision,
            "workflow_status": "finalizing",
        }

    except Exception as exc:
        logger.error("critic_node: failed for run %s: %s", run_id, exc)
        # Non-fatal: route back to supervisor with a revision recommendation
        return {
            "critic_decision": "revise_report",
            "critic_review_id": None,
            "critic_cycles": new_cycles,
            "supervisor_decision": "revise_report",
            "workflow_status": "finalizing",
            "error_message": safe_error_message(exc),
        }


async def fail_workflow_node(
    state: ResearchWorkflowState,
    config: RunnableConfig,
) -> dict:
    """Mark the run as failed, clean up running tasks, log the failure event.

    This is a terminal node — always returns ``{"workflow_status": "failed"}``.
    It is safe to call multiple times (all writes are idempotent).
    """
    run_id = state["run_id"]
    error_message = state.get("error_message") or "Multi-agent workflow failed."
    iteration = state.get("iteration_count", 0)

    try:
        from app.models.run import ResearchRun
        from app.models.task import ResearchTask
        from app.services.event_service import log_event, publish_event
        from sqlalchemy import select, update

        async with AsyncSessionLocal() as db:
            # Update run status
            run_result = await db.execute(select(ResearchRun).where(ResearchRun.id == run_id))
            run = run_result.scalar_one_or_none()
            if run and run.status not in ("failed", "completed"):
                run.status = "failed"
                run.error_message = safe_error_message(Exception(error_message))
                run.completed_at = datetime.now(timezone.utc)

            # Mark any running tasks as failed
            await db.execute(
                update(ResearchTask)
                .where(
                    ResearchTask.run_id == run_id,
                    ResearchTask.status == "running",
                )
                .values(
                    status="failed",
                    completed_at=datetime.now(timezone.utc),
                    error_message="Workflow failed before task could complete.",
                )
            )

            _ev_fail = await log_event(
                db,
                run_id=run_id,
                agent_name="system",
                event_type="workflow_failed",
                summary=f"Workflow failed: {error_message[:200]}",
                iteration=iteration,
            )
            await db.commit()
            await publish_event(_ev_fail)

        logger.error("fail_workflow_node: run %s failed — %s", run_id, error_message)

    except Exception as exc:
        logger.error(
            "fail_workflow_node: could not write failure state for run %s: %s",
            run_id,
            exc,
        )

    return {"workflow_status": "failed"}


async def citation_validation_node(
    state: ResearchWorkflowState,
    config: RunnableConfig,
) -> dict:
    """Create Citation records and run validation — multi-agent runs, post-critic.

    Called when supervisor decision is "approve_report".
    Calls the shared citation_service and citation_validator services.
    Always non-fatal — if citation creation or validation fails, the workflow
    still completes, just without citation validation.

    Marks the run as completed after citation validation.
    """
    run_id = state["run_id"]
    report_id = state.get("final_report_id")
    iteration = state.get("iteration_count", 0)

    if not report_id:
        logger.warning(
            "citation_validation_node: no report_id in state for run %s — skipping", run_id
        )
        return {"citation_validation_passed": False, "workflow_status": "completed"}

    citation_validation_passed = False

    try:
        from app.services.citation_service import create_citations_for_run
        from app.services.citation_validator import validate_citations_for_run
        from app.models.run import ResearchRun
        from app.services.event_service import log_event
        from sqlalchemy import select

        # Step 1: Create citation records
        async with AsyncSessionLocal() as db:
            citation_ids = await create_citations_for_run(
                db=db,
                run_id=run_id,
                report_id=report_id,
            )
            await db.commit()

        # Step 2: Validate citations
        async with AsyncSessionLocal() as db:
            validation_summary = await validate_citations_for_run(
                db=db,
                run_id=run_id,
                report_id=report_id,
            )
            await db.commit()

        citation_validation_passed = validation_summary.get("failed_count", 1) == 0

        logger.info(
            "citation_validation_node: run %s — %d/%d citations verified",
            run_id,
            validation_summary.get("verified_count", 0),
            validation_summary.get("total_citations", 0),
        )

    except Exception as exc:
        logger.warning(
            "citation_validation_node: citation validation failed for run %s: %s — continuing",
            run_id, exc
        )

    # Mark run completed (this node is always the last step in multi-agent)
    try:
        from app.models.run import ResearchRun
        from app.services.event_service import log_event, publish_event
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            run_result = await db.execute(select(ResearchRun).where(ResearchRun.id == run_id))
            run = run_result.scalar_one_or_none()
            if run:
                run.status = "completed"
                run.current_stage = "Complete"
                run.completed_at = datetime.now(timezone.utc)

            _ev_complete = await log_event(
                db,
                run_id=run_id,
                agent_name="system",
                event_type="workflow_complete",
                summary="Multi-agent research completed with citation validation",
                output_ref=f"report_id:{report_id}",
                iteration=iteration,
            )
            await db.commit()
            await publish_event(_ev_complete)

    except Exception as exc:
        logger.error(
            "citation_validation_node: failed to mark run %s complete: %s", run_id, exc
        )

    return {
        "citation_validation_passed": citation_validation_passed,
        "workflow_status": "completed",
    }


# ── Phase 5 M5.5: Human approval checkpoint nodes ──────────────────────────────
# These are the nodes listed in interrupt_before=[...].
# When the graph is interrupted BEFORE these nodes, execution pauses here.
# The body of each node only runs AFTER the user approves (graph.ainvoke resumes).

async def planning_complete_node(
    state: ResearchWorkflowState,
    config: RunnableConfig,
) -> dict:
    """Human approval checkpoint inserted after planning_node.

    Executed only after the user approves the plan.
    If the user requested revisions, the executor resumes with revision_notes
    already injected into the state before invoking this node — this node is
    effectively a no-op pass-through, and the graph routes back to planning_node
    via the supervisor.

    If the user rejected, the executor marks the run failed and does NOT call
    graph.ainvoke, so this node never runs in the rejected case.
    """
    run_id = state["run_id"]
    iteration = state.get("iteration_count", 0)

    try:
        from app.services.event_service import log_event, publish_event
        from app.models.run import ResearchRun
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            run_result = await db.execute(select(ResearchRun).where(ResearchRun.id == run_id))
            run = run_result.scalar_one_or_none()
            if run:
                run.current_stage = "Research Starting"
                run.status = "running"

            _ev = await log_event(
                db,
                run_id=run_id,
                agent_name="system",
                event_type="plan_approved",
                summary="Research plan approved — beginning research tasks",
                iteration=iteration,
            )
            await db.commit()
            await publish_event(_ev)

        logger.info("planning_complete_node: plan approved, proceeding for run %s", run_id)

    except Exception as exc:
        logger.error("planning_complete_node: error for run %s: %s", run_id, exc)

    return {}


async def critic_review_approval_node(
    state: ResearchWorkflowState,
    config: RunnableConfig,
) -> dict:
    """Human approval checkpoint inserted after critic_node.

    Only reached when the critic flagged `needs_attention`.
    If `critic_decision` is NOT `needs_attention`, this node is a pass-through.

    After user approves:  supervisor routes to citation_validation.
    After user requests revision: supervisor routes to research / plan.
    After user rejects: executor marks run failed, never reaches here.
    """
    run_id = state["run_id"]
    critic_decision = state.get("critic_decision", "")
    iteration = state.get("iteration_count", 0)

    # If the critic approved, this node is a pure pass-through
    if critic_decision not in ("mark_needs_attention", "needs_attention"):
        return {}

    try:
        from app.services.event_service import log_event, publish_event

        async with AsyncSessionLocal() as db:
            _ev = await log_event(
                db,
                run_id=run_id,
                agent_name="system",
                event_type="approval_checkpoint",
                summary="Critic review approved by user — proceeding to report generation",
                iteration=iteration,
            )
            await db.commit()
            await publish_event(_ev)

        logger.info(
            "critic_review_approval_node: critic approval resolved for run %s", run_id
        )

    except Exception as exc:
        logger.error("critic_review_approval_node: error for run %s: %s", run_id, exc)

    return {}
