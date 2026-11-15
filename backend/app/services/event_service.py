"""event_service — append-only AgentExecutionEvent log.

Events are immutable records of significant agent actions.
They are never updated or deleted — only inserted.
The frontend reads these via GET /runs/{id}/activity (polling fallback)
or receives them in real time via the SSE stream (GET /runs/{id}/stream).

Phase 5 M5.1 additions:
- Each new event is assigned the next per-run sequence number using
  ``COALESCE(MAX(sequence), 0) + 1`` within the same transaction.
- After the caller commits, ``publish_event`` pushes the event to all
  active SSE subscribers via ``sse_manager.publish``.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import AgentExecutionEvent

logger = logging.getLogger(__name__)


async def log_event(
    db: AsyncSession,
    run_id: str,
    agent_name: str,
    event_type: str,
    summary: str,
    *,
    input_ref: str | None = None,
    output_ref: str | None = None,
    iteration: int = 0,
) -> AgentExecutionEvent:
    """Insert one AgentExecutionEvent row.

    This function does NOT commit — the caller is responsible for the
    transaction.  In most node implementations the commit happens after
    all DB writes for that node are complete.

    The sequence number is assigned atomically within the caller's
    transaction using ``COALESCE(MAX(sequence), 0) + 1``.

    Parameters
    ----------
    db:
        Open AsyncSession from the caller.
    run_id:
        The ResearchRun this event belongs to.
    agent_name:
        One of: "supervisor", "planner", "researcher", "system", "critic".
    event_type:
        One of: "decision", "plan_created", "plan_revised", "task_started",
        "task_completed", "task_failed", "workflow_start",
        "workflow_complete", "workflow_failed".
    summary:
        Human-readable one-line description shown in the frontend timeline.
    input_ref:
        Optional reference to the input object, e.g. ``"task_id:abc123"``.
    output_ref:
        Optional reference to the output, e.g. ``"decision:execute_next_task"``.
    iteration:
        Supervisor iteration count at the time of this event.

    Returns
    -------
    AgentExecutionEvent
        The newly created (not yet committed) event instance.
    """
    # Assign next per-run sequence number atomically within this transaction
    seq_result = await db.execute(
        select(func.coalesce(func.max(AgentExecutionEvent.sequence), 0) + 1).where(
            AgentExecutionEvent.run_id == run_id
        )
    )
    next_sequence: int = seq_result.scalar_one()

    event = AgentExecutionEvent(
        id=str(uuid.uuid4()),
        run_id=run_id,
        agent_name=agent_name,
        event_type=event_type,
        summary=summary,
        input_ref=input_ref,
        output_ref=output_ref,
        iteration=iteration,
        sequence=next_sequence,
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    logger.debug(
        "event_service: logged [%s/%s] seq=%d for run %s — %s",
        agent_name,
        event_type,
        next_sequence,
        run_id,
        summary,
    )
    return event


async def publish_event(event: AgentExecutionEvent) -> None:
    """Publish an already-committed event to all active SSE subscribers.

    Call this AFTER ``db.commit()`` so the event is visible in the DB
    before any client tries to replay from it.
    """
    from app.services.sse_manager import sse_manager

    data = {
        "id": event.id,
        "run_id": event.run_id,
        "agent_name": event.agent_name,
        "event_type": event.event_type,
        "summary": event.summary,
        "input_ref": event.input_ref,
        "output_ref": event.output_ref,
        "iteration": event.iteration,
        "sequence": event.sequence,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
    await sse_manager.publish(event.run_id, "activity_event", data)


async def publish_evidence_added(evidence) -> None:
    """Publish an evidence_added event to all active SSE subscribers for this run.

    Call this AFTER ``db.commit()`` so the record is visible in the DB.
    """
    from app.services.sse_manager import sse_manager

    data = {
        "id": evidence.id,
        "run_id": evidence.run_id,
        "source_type": evidence.source_type,
        "source_label": evidence.source_label,
        "evidence_type": evidence.evidence_type,
        "evidence_relationship": evidence.evidence_relationship,
        "relevance_score": evidence.relevance_score,
        "url": evidence.url,
        "page_title": evidence.page_title,
        "source_id": evidence.source_id,
        "task_id": evidence.task_id,
        "created_at": evidence.retrieved_at.isoformat() if evidence.retrieved_at else None,
    }
    await sse_manager.publish(evidence.run_id, "evidence_added", data)


async def get_events(
    db: AsyncSession,
    run_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[AgentExecutionEvent]:
    """Return AgentExecutionEvent rows for a run, ordered by created_at ascending."""
    result = await db.execute(
        select(AgentExecutionEvent)
        .where(AgentExecutionEvent.run_id == run_id)
        .order_by(AgentExecutionEvent.created_at)
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_events_since(
    db: AsyncSession,
    run_id: str,
    after_sequence: int,
) -> list[AgentExecutionEvent]:
    """Return events with sequence > after_sequence for SSE replay."""
    result = await db.execute(
        select(AgentExecutionEvent)
        .where(
            AgentExecutionEvent.run_id == run_id,
            AgentExecutionEvent.sequence > after_sequence,
        )
        .order_by(AgentExecutionEvent.sequence)
    )
    return list(result.scalars().all())


async def count_events(db: AsyncSession, run_id: str) -> int:
    """Return the total number of events for a run (for pagination)."""
    result = await db.execute(
        select(func.count()).where(AgentExecutionEvent.run_id == run_id)
    )
    return result.scalar_one()
