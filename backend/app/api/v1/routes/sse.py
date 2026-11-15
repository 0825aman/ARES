"""SSE stream endpoint — Phase 5 M5.1.

GET /runs/{run_id}/stream

Opens a Server-Sent Events stream for a research run.  The client receives
live events as the graph executes.

SSE message format:
    id: {sequence_number}
    event: {event_type}
    data: {json_payload}

Event types:
    connected          — emitted immediately on stream open
    activity_event     — new AgentExecutionEvent (replayed on reconnect + live)
    run_status_changed — ResearchRun status/stage change
    source_added       — new ResearchSource persisted
    evidence_added     — new Evidence persisted
    heartbeat          — every 30 seconds to prevent proxy timeouts
    run_completed      — run reached "completed" terminal state
    run_failed         — run reached "failed" terminal state

Reconnect / replay:
    If the request includes a ``Last-Event-ID`` header (or ``last_event_id``
    query param) the server replays all activity_event rows with
    sequence > last_event_id from the DB before switching to live delivery.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.run_service import run_service
from app.services.event_service import get_events, get_events_since

logger = logging.getLogger(__name__)

router = APIRouter()

# Heartbeat interval in seconds
_HEARTBEAT_INTERVAL = 30


async def _build_event_generator(
    run_id: str,
    last_seq: int | None = None,
    db_factory=None,
) -> AsyncGenerator[dict, None]:
    """
    Core async generator that yields SSE event dicts for a given run.

    Extracted from the route handler so it can be called directly in tests
    without going through the HTTP layer (which hangs when using httpx ASGI
    transport with an infinite response body).

    Each yielded dict has keys: ``event``, ``data``, and optionally ``id``.

    Steps:
    1. Emit ``connected`` immediately.
    2. Replay missed ``activity_event`` rows from the DB.
    3. Subscribe to ``sse_manager`` and stream live events.
    4. Emit ``heartbeat`` every 30 seconds via a background task.
    5. Exit cleanly on client disconnect (CancelledError).
    """
    from app.services.sse_manager import sse_manager
    from app.core.database import AsyncSessionLocal

    _session_factory = db_factory if db_factory is not None else AsyncSessionLocal

    # ── 1. Emit connected immediately ─────────────────────────────────────────
    yield {
        "event": "connected",
        "data": json.dumps({"run_id": run_id, "message": "Stream connected"}),
    }

    # ── 2. Replay missed activity_event rows from DB ───────────────────────────
    try:
        async with _session_factory() as db:
            if last_seq is not None:
                missed = await get_events_since(db, run_id, last_seq)
            else:
                missed = await get_events(db, run_id, limit=1000)

        for ev in missed:
            data = {
                "id": ev.id,
                "run_id": ev.run_id,
                "agent_name": ev.agent_name,
                "event_type": ev.event_type,
                "summary": ev.summary,
                "input_ref": ev.input_ref,
                "output_ref": ev.output_ref,
                "iteration": ev.iteration,
                "sequence": ev.sequence,
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
            }
            yield {
                "id": str(ev.sequence) if ev.sequence is not None else "",
                "event": "activity_event",
                "data": json.dumps(data),
            }
    except Exception as exc:
        logger.warning("sse: replay failed for run %s: %s", run_id, exc)

    # ── 3. Subscribe to live events and heartbeat ──────────────────────────────
    async with sse_manager.subscribe(run_id) as queue:
        heartbeat_task = asyncio.create_task(_heartbeat_producer(queue))
        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=35)
                except asyncio.TimeoutError:
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps(
                            {"timestamp": datetime.now(timezone.utc).isoformat()}
                        ),
                    }
                    continue

                if item is None:
                    break

                event_type = item.get("event_type", "message")
                payload = item.get("data", {})

                if event_type == "heartbeat":
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps(payload),
                    }
                elif event_type == "activity_event":
                    seq = payload.get("sequence")
                    yield {
                        "id": str(seq) if seq is not None else "",
                        "event": "activity_event",
                        "data": json.dumps(payload),
                    }
                else:
                    yield {
                        "event": event_type,
                        "data": json.dumps(payload),
                    }

                if event_type in ("run_completed", "run_failed"):
                    break

        except asyncio.CancelledError:
            logger.debug("sse: client disconnected from run %s", run_id)
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass


@router.get("/{project_id}/runs/{run_id}/stream")
async def stream_run_events(
    project_id: str,
    run_id: str,
    last_event_id: str | None = Query(None, alias="last_event_id"),
    last_event_id_header: str | None = Header(None, alias="last-event-id"),
    db: AsyncSession = Depends(get_db),
):
    """Open an SSE stream for a research run.

    - Returns 404 if the run does not exist.
    - Replays missed events when ``Last-Event-ID`` is present.
    - Emits ``connected`` immediately on open.
    - Emits ``heartbeat`` every 30 seconds.
    - Cleans up subscriber on client disconnect.
    """
    from sse_starlette.sse import EventSourceResponse

    # Use header value preferentially; fall back to query param
    raw_last_id = last_event_id_header or last_event_id

    run = await run_service.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")

    # Parse last_event_id — may be plain integer or "{run_id}:{seq}" format
    last_seq: int | None = None
    if raw_last_id:
        try:
            part = raw_last_id.split(":")[-1]
            last_seq = int(part)
        except (ValueError, IndexError):
            last_seq = None

    return EventSourceResponse(_build_event_generator(run_id, last_seq=last_seq))


async def _heartbeat_producer(queue: asyncio.Queue) -> None:
    """Place heartbeat events into the subscriber queue every
    ``_HEARTBEAT_INTERVAL`` seconds.  Cancelled when the consumer exits.
    """
    while True:
        await asyncio.sleep(_HEARTBEAT_INTERVAL)
        payload = {
            "event_type": "heartbeat",
            "data": {"timestamp": datetime.now(timezone.utc).isoformat()},
        }
        try:
            queue.put_nowait(payload)
        except asyncio.QueueFull:
            pass
