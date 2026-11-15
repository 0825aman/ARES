"""tests/test_sse_stream.py — Phase 5 M5.1 SSE stream endpoint tests.

Test IDs:
  SSE-01  GET /runs/{run_id}/stream — 404 for unknown run_id
  SSE-02  GET /runs/{run_id}/stream — event_generator yields connected event immediately
  SSE-03  GET /runs/{run_id}/stream — connected event contains correct run_id
  SSE-04  GET /runs/{run_id}/stream — replays all events on fresh connection
  SSE-05  GET /runs/{run_id}/stream — Last-Event-ID replays only newer events
  SSE-06  GET /runs/{run_id}/stream — last_event_id query param replays correctly
  SSE-07  activity_event published when publish_event called after log_event
  SSE-08  run_completed published when run status → completed

Testing strategy:
  httpx ASGI transport does not support infinite-body streaming (it buffers the
  full response, so any infinite generator hangs the test).  For tests SSE-02
  through SSE-06 we therefore call the route's async generator directly via
  the FastAPI app's dependency injection, bypassing httpx.

  SSE-01 uses a plain (non-streaming) GET so httpx is fine there.
  SSE-07 and SSE-08 test the SSEManager directly — no HTTP layer at all.
"""
from __future__ import annotations

import asyncio
import json
import uuid
import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock

from tests.conftest import TestSessionLocal
from app.models.run import ResearchRun
from app.services.sse_manager import sse_manager

BASE = "/api/v1"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_project(client: AsyncClient) -> str:
    r = await client.post(
        f"{BASE}/projects/",
        json={"title": "SSE Test", "research_question": "Test?"},
    )
    assert r.status_code == 201
    return r.json()["id"]


async def _create_run(project_id: str) -> str:
    from datetime import datetime, timezone
    run_id = str(uuid.uuid4())
    async with TestSessionLocal() as db:
        run = ResearchRun(
            id=run_id,
            project_id=project_id,
            research_question="Test question?",
            use_web=True,
            use_documents=False,
            status="running",
            workflow_mode="sequential",
            verification_depth="basic",
            created_at=datetime.now(timezone.utc),
        )
        db.add(run)
        await db.commit()
    return run_id


async def _create_project_and_run(client: AsyncClient) -> tuple[str, str]:
    project_id = await _create_project(client)
    run_id = await _create_run(project_id)
    return project_id, run_id


def _parse_sse_events(raw_text: str) -> list[dict]:
    """Parse raw SSE text into a list of event dicts."""
    events: list[dict] = []
    current: dict = {}
    for line in raw_text.splitlines():
        if line.startswith("id:"):
            current["id"] = line[3:].strip()
        elif line.startswith("event:"):
            current["event"] = line[6:].strip()
        elif line.startswith("data:"):
            current["data"] = line[5:].strip()
        elif line == "" and current:
            events.append(current)
            current = {}
    if current:
        events.append(current)
    return events


async def _collect_generator_events(
    run_id: str,
    *,
    last_event_id: int | None = None,
    n_events: int = 1,
    timeout: float = 3.0,
) -> list[dict]:
    """
    Invoke the SSE route's event_generator directly (no HTTP) and collect
    up to `n_events` yielded dicts, then cancel.

    Each dict has keys: event, data (and optionally id).
    Uses TestSessionLocal so the generator reads from the in-memory test DB.
    """
    from app.api.v1.routes.sse import _build_event_generator
    from tests.conftest import TestSessionLocal as _TestDB

    collected: list[dict] = []
    done = asyncio.Event()

    async def consume():
        gen = _build_event_generator(
            run_id, last_seq=last_event_id, db_factory=_TestDB
        )
        async for item in gen:
            if isinstance(item, dict):
                collected.append(item)
            if len(collected) >= n_events:
                done.set()
                return

    task = asyncio.create_task(consume())
    try:
        await asyncio.wait_for(done.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        pass
    finally:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
    return collected


# ---------------------------------------------------------------------------
# SSE-01: 404 for unknown run_id (plain HTTP — no streaming)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sse01_unknown_run_returns_404(async_client: AsyncClient):
    project_id = await _create_project(async_client)
    fake_run_id = str(uuid.uuid4())
    r = await async_client.get(f"{BASE}/projects/{project_id}/runs/{fake_run_id}/stream")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# SSE-02: event_generator yields connected event immediately
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sse02_connected_event_yielded_immediately(async_client: AsyncClient):
    project_id, run_id = await _create_project_and_run(async_client)

    events = await _collect_generator_events(run_id, n_events=1, timeout=3.0)

    assert len(events) >= 1, f"No events collected: {events}"
    assert events[0].get("event") == "connected", (
        f"First event should be 'connected', got: {events[0]}"
    )


# ---------------------------------------------------------------------------
# SSE-03: connected event data contains run_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sse03_connected_event_contains_run_id(async_client: AsyncClient):
    project_id, run_id = await _create_project_and_run(async_client)

    events = await _collect_generator_events(run_id, n_events=1, timeout=3.0)

    connected = next((e for e in events if e.get("event") == "connected"), None)
    assert connected is not None, f"No connected event in: {events}"
    data = json.loads(connected["data"])
    assert data["run_id"] == run_id


# ---------------------------------------------------------------------------
# SSE-04: Fresh connection replays all existing events
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sse04_fresh_connection_replays_all_events(async_client: AsyncClient):
    from app.services.event_service import log_event

    project_id, run_id = await _create_project_and_run(async_client)

    # Insert 3 events
    async with TestSessionLocal() as db:
        for i in range(3):
            await log_event(
                db,
                run_id=run_id,
                agent_name="system",
                event_type="workflow_start",
                summary=f"Event {i + 1}",
                iteration=i,
            )
        await db.commit()

    # Collect 4 events: 1 connected + 3 activity_event
    events = await _collect_generator_events(run_id, n_events=4, timeout=5.0)

    activity_events = [e for e in events if e.get("event") == "activity_event"]
    assert len(activity_events) >= 3, (
        f"Expected ≥3 activity_event entries, got {len(activity_events)}: {events}"
    )


# ---------------------------------------------------------------------------
# SSE-05: Last-Event-ID replays only events after that sequence
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sse05_last_event_id_replays_only_newer_events(async_client: AsyncClient):
    from app.services.event_service import log_event
    from sqlalchemy import select
    from app.models.event import AgentExecutionEvent

    project_id, run_id = await _create_project_and_run(async_client)

    async with TestSessionLocal() as db:
        for i in range(5):
            await log_event(
                db,
                run_id=run_id,
                agent_name="system",
                event_type="workflow_start",
                summary=f"Event {i + 1}",
                iteration=i,
            )
        await db.commit()

    async with TestSessionLocal() as db:
        result = await db.execute(
            select(AgentExecutionEvent)
            .where(AgentExecutionEvent.run_id == run_id)
            .order_by(AgentExecutionEvent.sequence)
        )
        db_events = list(result.scalars().all())

    assert len(db_events) == 5
    after_seq = db_events[1].sequence  # after 2nd → should replay 3, 4, 5

    # Collect: 1 connected + 3 activity_event = 4 events
    events = await _collect_generator_events(
        run_id, last_event_id=after_seq, n_events=4, timeout=5.0
    )

    activity_events = [e for e in events if e.get("event") == "activity_event"]
    assert len(activity_events) == 3, (
        f"Expected 3 activity_event entries after seq {after_seq}, "
        f"got {len(activity_events)}: {events}"
    )
    for ae in activity_events:
        data = json.loads(ae["data"])
        assert data["sequence"] > after_seq, (
            f"Replayed event seq {data['sequence']} ≤ after_seq {after_seq}"
        )


# ---------------------------------------------------------------------------
# SSE-06: last_event_id=0 replays all events (edge case)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sse06_last_event_id_zero_replays_all(async_client: AsyncClient):
    from app.services.event_service import log_event

    project_id, run_id = await _create_project_and_run(async_client)

    async with TestSessionLocal() as db:
        for i in range(3):
            await log_event(
                db,
                run_id=run_id,
                agent_name="system",
                event_type="workflow_start",
                summary=f"Event {i + 1}",
                iteration=i,
            )
        await db.commit()

    # last_event_id=0 → sequences 1, 2, 3 all > 0 → all 3 replayed
    events = await _collect_generator_events(
        run_id, last_event_id=0, n_events=4, timeout=5.0
    )

    activity_events = [e for e in events if e.get("event") == "activity_event"]
    assert len(activity_events) == 3, (
        f"Expected 3 activity_events, got {len(activity_events)}: {events}"
    )


# ---------------------------------------------------------------------------
# SSE-07: activity_event published to SSEManager when publish_event called
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sse07_activity_event_published_on_log_event(async_client: AsyncClient):
    from app.services.event_service import log_event, publish_event

    project_id, run_id = await _create_project_and_run(async_client)

    received = []

    async def consume():
        async with sse_manager.subscribe(run_id) as q:
            item = await asyncio.wait_for(q.get(), timeout=2.0)
            if item is not None:
                received.append(item)

    consumer_task = asyncio.create_task(consume())
    await asyncio.sleep(0.02)  # let consumer register

    async with TestSessionLocal() as db:
        ev = await log_event(
            db,
            run_id=run_id,
            agent_name="system",
            event_type="workflow_start",
            summary="Live test event",
            iteration=0,
        )
        await db.commit()
        await publish_event(ev)

    await asyncio.wait_for(consumer_task, timeout=3.0)

    assert len(received) == 1
    assert received[0]["event_type"] == "activity_event"
    assert received[0]["data"]["summary"] == "Live test event"
    assert received[0]["data"]["sequence"] == 1


# ---------------------------------------------------------------------------
# SSE-08: run_completed event published when run status → completed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sse08_run_completed_published_on_update_status(async_client: AsyncClient):
    from app.services.run_service import run_service
    from sqlalchemy import select

    project_id, run_id = await _create_project_and_run(async_client)

    received = []

    async def consume():
        async with sse_manager.subscribe(run_id) as q:
            item = await asyncio.wait_for(q.get(), timeout=2.0)
            if item is not None:
                received.append(item)

    consumer_task = asyncio.create_task(consume())
    await asyncio.sleep(0.02)

    async with TestSessionLocal() as db:
        result = await db.execute(
            select(ResearchRun).where(ResearchRun.id == run_id)
        )
        run = result.scalar_one()
        await run_service.update_status(db, run, "completed", stage="Complete")

    await asyncio.wait_for(consumer_task, timeout=3.0)

    assert len(received) == 1
    assert received[0]["event_type"] in ("run_completed", "run_status_changed")
    assert received[0]["data"]["run_id"] == run_id
