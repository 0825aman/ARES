"""ApprovalService — Phase 5 M5.5.

Manages the human-in-the-loop approval workflow:
  - Creating ApprovalRequest records when LangGraph suspends
  - Processing user decisions (approve / reject / revision_requested)
  - Resuming or aborting the graph based on the decision
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import ApprovalRequest
from app.models.run import ResearchRun

logger = logging.getLogger(__name__)

APPROVAL_EXPIRY_HOURS = 24  # default; override via settings


async def create_approval(
    db: AsyncSession,
    run_id: str,
    checkpoint_name: str,
    node_name: str,
    context_snapshot: dict,
    expiry_hours: int = APPROVAL_EXPIRY_HOURS,
) -> ApprovalRequest:
    """Create a pending ApprovalRequest for a suspended graph run.

    Idempotent: if a pending approval already exists for this run_id, that
    existing approval is returned instead of creating a duplicate.

    Does NOT commit — the caller commits.
    """
    # Idempotency check — return existing pending approval if one exists
    existing_result = await db.execute(
        select(ApprovalRequest)
        .where(
            ApprovalRequest.run_id == run_id,
            ApprovalRequest.status == "pending",
        )
        .order_by(ApprovalRequest.created_at.desc())
        .limit(1)
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        logger.info(
            "create_approval: returning existing pending approval %s for run %s",
            existing.id,
            run_id,
        )
        return existing

    now = datetime.now(timezone.utc)
    approval = ApprovalRequest(
        id=str(uuid.uuid4()),
        run_id=run_id,
        checkpoint_name=checkpoint_name,
        node_name=node_name,
        context_snapshot=json.dumps(context_snapshot),
        status="pending",
        created_at=now,
        expires_at=now + timedelta(hours=expiry_hours),
    )
    db.add(approval)
    return approval


async def get_pending_approval(
    db: AsyncSession,
    run_id: str,
) -> Optional[ApprovalRequest]:
    """Return the first pending ApprovalRequest for a run, or None.

    Also checks for expiry and transitions expired records.
    """
    result = await db.execute(
        select(ApprovalRequest)
        .where(
            ApprovalRequest.run_id == run_id,
            ApprovalRequest.status == "pending",
        )
        .order_by(ApprovalRequest.created_at.desc())
        .limit(1)
    )
    approval = result.scalar_one_or_none()

    if approval is None:
        return None

    # Check-on-access expiry
    now = datetime.now(timezone.utc)
    # expires_at may be naive or aware — normalise
    exp = approval.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if now > exp:
        approval.status = "expired"
        await db.commit()
        return None

    return approval


async def get_approval_by_id(
    db: AsyncSession,
    approval_id: str,
    run_id: str,
) -> Optional[ApprovalRequest]:
    """Return an ApprovalRequest by id, scoped to run_id."""
    result = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.run_id == run_id,
        )
    )
    return result.scalar_one_or_none()


async def list_approvals(
    db: AsyncSession,
    run_id: str,
) -> list[ApprovalRequest]:
    """Return all ApprovalRequests for a run, newest first."""
    result = await db.execute(
        select(ApprovalRequest)
        .where(ApprovalRequest.run_id == run_id)
        .order_by(ApprovalRequest.created_at.desc())
    )
    return list(result.scalars().all())


async def process_decision(
    db: AsyncSession,
    approval: ApprovalRequest,
    decision: str,
    notes: Optional[str],
) -> dict:
    """Apply a user decision to an ApprovalRequest and resume/abort the graph.

    Returns a dict with 'run_status' after the action.

    Decisions:
        "approved"            — resume graph as-is
        "revision_requested"  — resume graph with revision_notes injected
        "rejected"            — mark run failed, do not resume graph
    """
    if approval.status != "pending":
        raise ValueError(f"Approval {approval.id} is not pending (status={approval.status})")

    # Check expiry
    now = datetime.now(timezone.utc)
    exp = approval.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if now > exp:
        approval.status = "expired"
        await db.commit()
        raise ValueError("Approval has expired")

    # Record decision
    approval.decision = decision
    approval.decision_notes = notes
    approval.decided_at = now

    if decision == "rejected":
        approval.status = "rejected"

        # Mark run failed
        run_result = await db.execute(select(ResearchRun).where(ResearchRun.id == approval.run_id))
        run = run_result.scalar_one_or_none()
        if run and run.status not in ("completed", "failed"):
            run.status = "failed"
            run.error_message = "Research aborted by user at approval checkpoint."
            run.completed_at = now
        await db.commit()

        # Publish SSE
        try:
            from app.services.sse_manager import sse_manager
            await sse_manager.publish(
                approval.run_id,
                "approval_resolved",
                {"approval_id": approval.id, "decision": "rejected", "run_continuing": False},
            )
            await sse_manager.publish(
                approval.run_id,
                "run_failed",
                {
                    "run_id": approval.run_id,
                    "status": "failed",
                    "error": "Research aborted by user.",
                },
            )
        except Exception as sse_exc:
            logger.warning("process_decision: SSE publish failed: %s", sse_exc)

        return {"run_status": "failed"}

    # For "approved" and "revision_requested": resume the graph
    approval.status = "approved" if decision == "approved" else decision
    await db.commit()

    # Resume in background (don't block the HTTP response)
    import asyncio
    asyncio.create_task(
        _resume_graph(
            run_id=approval.run_id,
            approval_id=approval.id,
            decision=decision,
            notes=notes,
        )
    )

    # Publish SSE immediately
    try:
        from app.services.sse_manager import sse_manager
        await sse_manager.publish(
            approval.run_id,
            "approval_resolved",
            {
                "approval_id": approval.id,
                "decision": decision,
                "run_continuing": True,
            },
        )
    except Exception as sse_exc:
        logger.warning("process_decision: SSE publish failed: %s", sse_exc)

    return {"run_status": "running"}


async def _resume_graph(
    run_id: str,
    approval_id: str,
    decision: str,
    notes: Optional[str],
) -> None:
    """Resume the LangGraph graph after an approval decision.

    For "approved": resume with no state changes.
    For "revision_requested": inject revision_notes into state before resuming.
    """
    from app.graph.workflow import get_research_graph
    from app.core.database import AsyncSessionLocal
    from app.models.run import ResearchRun
    from sqlalchemy import select

    try:
        graph = await get_research_graph()
        graph_config = {
            "configurable": {"thread_id": run_id},
            "recursion_limit": 100,
        }

        # Mark run running again
        async with AsyncSessionLocal() as db:
            run_result = await db.execute(select(ResearchRun).where(ResearchRun.id == run_id))
            run = run_result.scalar_one_or_none()
            if run and run.status == "awaiting_approval":
                run.status = "running"
                await db.commit()

        if decision == "revision_requested":
            # Inject revision notes — graph resumes from the suspended checkpoint
            # with this state update merged in
            update_input = {
                "revision_notes": notes or "Please revise the plan based on user feedback.",
                "supervisor_decision": "revise_plan",
            }
            await graph.ainvoke(update_input, config=graph_config)
        else:
            # approved — resume with no additional input
            await graph.ainvoke(None, config=graph_config)

        # Check if the graph suspended again (e.g. next checkpoint)
        try:
            snap = await graph.aget_state(graph_config)
            if snap.next:
                suspended_node = snap.next[0]
                logger.info(
                    "_resume_graph: graph suspended before '%s' for run %s",
                    suspended_node,
                    run_id,
                )
                from app.graph.executor import _handle_suspension
                await _handle_suspension(run_id, suspended_node, snap.values)
        except Exception as snap_exc:
            logger.warning(
                "_resume_graph: could not inspect graph state for run %s: %s",
                run_id,
                snap_exc,
            )

        logger.info(
            "_resume_graph: graph resumed for run %s (decision=%s)", run_id, decision
        )

    except Exception as exc:
        logger.error("_resume_graph: failed to resume run %s: %s", run_id, exc)
        # Mark run failed so it doesn't stay stuck
        try:
            from app.core.database import AsyncSessionLocal as ASL
            from app.models.run import ResearchRun as RR
            from sqlalchemy import select as sel
            from datetime import datetime as dt, timezone as tz

            async with ASL() as db:
                r = await db.execute(sel(RR).where(RR.id == run_id))
                run = r.scalar_one_or_none()
                if run and run.status not in ("completed", "failed"):
                    run.status = "failed"
                    run.error_message = f"Graph resume failed: {exc}"
                    run.completed_at = dt.now(tz.utc)
                    await db.commit()
        except Exception:
            pass
