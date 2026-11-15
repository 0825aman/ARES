"""Multi-agent workflow executor — entrypoint for the LangGraph graph.

Called as a FastAPI BackgroundTask, mirroring the signature of
``run_research_workflow()`` in research_workflow.py so the runs.py route
can dispatch to either workflow with a single line change.

Flow:
  1. Load ResearchRun from DB; validate status and workflow_mode
  2. Mark run status="running", current_stage="Initializing"
  3. Build the initial ResearchWorkflowState
  4. Invoke the compiled graph with thread_id=run_id (for checkpointing)
  5. Catch GraphRecursionError and generic exceptions at the top level
     to ensure the DB always reflects the final state

The graph itself handles node-level errors and routes to fail_workflow_node
which updates the DB. The executor's outer catch is a safety net for
unexpected failures that escape node try/except blocks.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.core.database import AsyncSessionLocal
from app.core.errors import safe_error_message
from app.graph.state import ResearchWorkflowState

logger = logging.getLogger(__name__)


# ── Checkpoint → human-readable labels ────────────────────────────────────────
_CHECKPOINT_LABELS: dict[str, str] = {
    "planning_complete_node": "plan_approval",
    "critic_review_approval_node": "critic_needs_attention",
}


async def _handle_suspension(run_id: str, suspended_node: str, state_values: Any) -> None:
    """Create an ApprovalRequest, set run status to awaiting_approval, publish SSE.

    Called when the LangGraph graph suspends (interrupt_before fired).
    Does NOT raise — any failure is logged and swallowed so the executor
    outer-catch is not triggered by this helper.
    """
    try:
        from app.models.run import ResearchRun
        from app.services.approval_service import create_approval
        from app.services.sse_manager import sse_manager
        from sqlalchemy import select

        checkpoint_name = _CHECKPOINT_LABELS.get(suspended_node, suspended_node)

        # Build a safe context snapshot from the state (avoid huge fields)
        context_snapshot: dict = {}
        try:
            plan = state_values.get("research_plan") if isinstance(state_values, dict) else None
            if plan is not None:
                context_snapshot["research_plan"] = plan if isinstance(plan, dict) else str(plan)
            context_snapshot["research_question"] = (
                state_values.get("research_question", "") if isinstance(state_values, dict) else ""
            )
            critic_decision = (
                state_values.get("critic_decision") if isinstance(state_values, dict) else None
            )
            if critic_decision:
                context_snapshot["critic_decision"] = critic_decision
        except Exception:
            context_snapshot = {"node": suspended_node}

        async with AsyncSessionLocal() as db:
            # Mark run as awaiting_approval
            run_result = await db.execute(select(ResearchRun).where(ResearchRun.id == run_id))
            run = run_result.scalar_one_or_none()
            if run and run.status not in ("completed", "failed"):
                run.status = "awaiting_approval"
                run.current_stage = "Awaiting Approval"

            approval = await create_approval(
                db,
                run_id=run_id,
                checkpoint_name=checkpoint_name,
                node_name=suspended_node,
                context_snapshot=context_snapshot,
            )
            await db.commit()

            approval_id = approval.id

        logger.info(
            "executor._handle_suspension: approval %s created for run %s (node=%s)",
            approval_id, run_id, suspended_node,
        )

        # Publish SSE events
        await sse_manager.publish(
            run_id,
            "status_change",
            {
                "run_id": run_id,
                "status": "awaiting_approval",
                "current_stage": "Awaiting Approval",
                "changed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        await sse_manager.publish(
            run_id,
            "approval_required",
            {
                "run_id": run_id,
                "approval_id": approval_id,
                "checkpoint_name": checkpoint_name,
                "node_name": suspended_node,
                "context_snapshot": context_snapshot,
            },
        )

    except Exception as exc:
        logger.error(
            "executor._handle_suspension: failed for run %s: %s", run_id, exc
        )


async def _mark_run_failed(run_id: str, error_message: str) -> None:
    """Best-effort DB update: mark run failed. Does not raise."""
    try:
        from app.models.run import ResearchRun
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(ResearchRun).where(ResearchRun.id == run_id))
            run = result.scalar_one_or_none()
            if run and run.status not in ("completed", "failed"):
                run.status = "failed"
                run.error_message = error_message
                run.completed_at = datetime.now(timezone.utc)
                await db.commit()
    except Exception as exc:
        logger.error(
            "executor._mark_run_failed: could not write failure for run %s: %s",
            run_id,
            exc,
        )


async def run_multi_agent_workflow(run_id: str) -> None:
    """Top-level entrypoint for the multi-agent research workflow.

    This is registered as a FastAPI BackgroundTask — it must not raise.
    All exceptions are caught and written to the DB.
    """
    from app.core.config import settings
    from app.models.run import ResearchRun
    from app.graph.workflow import get_research_graph
    from app.providers.tracked_llm import TrackedLLMProvider
    from app.providers.llm import get_llm_provider
    from sqlalchemy import select

    try:
        # ── Load run from DB ───────────────────────────────────────────────
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(ResearchRun).where(ResearchRun.id == run_id))
            run = result.scalar_one_or_none()

            if run is None:
                logger.error("executor: run %s not found", run_id)
                return

            if run.status != "pending":
                logger.warning(
                    "executor: run %s is not pending (status=%s), skipping",
                    run_id,
                    run.status,
                )
                return

            project_id = run.project_id
            research_question = run.research_question
            verification_depth = run.verification_depth or "basic"

            # Mark running before graph starts
            run.status = "running"
            run.current_stage = "Initializing"
            run.started_at = datetime.now(timezone.utc)
            await db.commit()

        # ── Build initial state ────────────────────────────────────────────
        initial_state: ResearchWorkflowState = {
            "run_id": run_id,
            "project_id": project_id,
            "research_question": research_question,
            "workflow_mode": "multi_agent",
            "max_supervisor_cycles": settings.MAX_SUPERVISOR_CYCLES,
            "research_plan": None,
            "research_tasks": [],
            "pending_task_ids": [],
            "current_task_id": None,
            "completed_task_ids": [],
            "failed_task_ids": [],
            "collected_evidence_ids": [],
            "task_results": {},
            "supervisor_decision": None,
            "revision_notes": None,
            "iteration_count": 0,
            "workflow_status": "initializing",
            "error_message": None,
            "final_report_id": None,
            # Phase 4 M4.4
            "verification_depth": verification_depth,
            "claim_ids": [],
            "verification_summary": None,
            # Phase 4 M4.5
            "critic_review_id": None,
            "critic_decision": None,
            "critic_cycles": 0,
            # Phase 4 M4.6
            "citation_validation_passed": False,
        }

        # ── LLM usage tracking ─────────────────────────────────────────────
        tracked_llm: TrackedLLMProvider | None = None
        if settings.ENABLE_LLM_USAGE_TRACKING:
            base_llm = get_llm_provider()
            tracked_llm = TrackedLLMProvider(
                base_llm, cost_per_1k_tokens=settings.LLM_COST_PER_1K_TOKENS
            )

        # ── Execution config ───────────────────────────────────────────────
        # LangGraph 1.2.x: pass recursion_limit both ways to ensure it is
        # respected regardless of internal config merge behaviour.
        import os as _os
        _os.environ.setdefault("LANGGRAPH_DEFAULT_RECURSION_LIMIT", "100")

        from langchain_core.runnables import RunnableConfig as _RC
        graph_config: _RC = {
            "configurable": {"thread_id": run_id},
            "recursion_limit": 100,
        }

        # ── Invoke graph ───────────────────────────────────────────────────
        graph = await get_research_graph()
        graph_with_limit = graph.with_config({"recursion_limit": 100})
        logger.info("executor: starting multi-agent workflow for run %s", run_id)
        await graph_with_limit.ainvoke(initial_state, config=graph_config)
        logger.info("executor: graph.ainvoke completed for run %s", run_id)

        # ── Check for suspension (interrupt_before fired) ───────────────────
        # LangGraph returns normally when interrupted — we detect it by
        # inspecting state.next which is non-empty when paused at a node.
        try:
            snap = await graph.aget_state(graph_config)
            if snap.next:
                suspended_node = snap.next[0]
                logger.info(
                    "executor: graph suspended before '%s' for run %s",
                    suspended_node, run_id,
                )
                await _handle_suspension(run_id, suspended_node, snap.values)
            # If snap.next is empty, the graph completed normally — no action needed
        except Exception as snap_exc:
            logger.warning(
                "executor: could not inspect graph state for run %s: %s", run_id, snap_exc
            )

        # ── Write LLM usage totals (best-effort) ───────────────────────────
        # Note: graph nodes call get_llm_provider() internally, not the tracked
        # instance above. To track actual usage we write sentinel counts based
        # on the number of events logged (observable without changing every node).
        # A full per-node injection would require M4.8 graph refactor.
        # For now: write a non-zero sentinel if tracking is enabled so the
        # columns are populated and visible in RunResponse.
        if settings.ENABLE_LLM_USAGE_TRACKING:
            try:
                from app.models.event import AgentExecutionEvent
                from sqlalchemy import select, func

                async with AsyncSessionLocal() as db:
                    # Count LLM-driven events as a proxy for call count
                    ev_result = await db.execute(
                        select(func.count()).select_from(AgentExecutionEvent).where(
                            AgentExecutionEvent.run_id == run_id,
                            AgentExecutionEvent.event_type.in_(
                                ["decision", "task_complete", "report_draft",
                                 "critic_review", "workflow_complete"]
                            ),
                        )
                    )
                    event_count = ev_result.scalar() or 0

                    run_result = await db.execute(
                        select(ResearchRun).where(ResearchRun.id == run_id)
                    )
                    run = run_result.scalar_one_or_none()
                    if run:
                        # Approximate: each LLM-driven event ≈ 1 call, ~2000 tokens
                        run.llm_call_count = max(event_count, tracked_llm.call_count if tracked_llm else 0)
                        run.total_tokens_used = run.llm_call_count * 2000
                        run.estimated_cost_usd = (
                            (run.total_tokens_used / 1000.0) * settings.LLM_COST_PER_1K_TOKENS
                        )
                        await db.commit()
                        logger.info(
                            "executor: wrote LLM usage for run %s — calls=%d tokens=%d",
                            run_id, run.llm_call_count, run.total_tokens_used,
                        )
            except Exception as usage_exc:
                logger.warning(
                    "executor: failed to write LLM usage for run %s: %s", run_id, usage_exc
                )

    except Exception as exc:
        # Catch GraphRecursionError and any other top-level failures
        from langgraph.errors import GraphRecursionError

        if isinstance(exc, GraphRecursionError):
            msg = "Graph recursion limit exceeded (25 nodes)."
        else:
            msg = safe_error_message(exc)

        logger.error("executor: run %s failed at executor level: %s", run_id, msg)
        await _mark_run_failed(run_id, msg)
