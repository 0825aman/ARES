"""tests/test_sse_fanout.py — Phase 5 M5.1 SSE fan-out tests.

Test IDs:
  FO-01  Multiple clients on the same run receive the same events
  FO-02  Events don't cross between different run_ids
  FO-03  Subscriber count increases on subscribe, decreases on unsubscribe
  FO-04  QueueFull: slow client drops events gracefully without raising
  FO-05  SSEManager.publish to a run with no subscribers is a no-op
  FO-06  Multiple events published to multiple subscribers all arrive
"""
from __future__ import annotations

import asyncio
import uuid
import pytest

from app.services.sse_manager import SSEManager, sse_manager


# ---------------------------------------------------------------------------
# FO-01: Multiple clients on same run receive same events
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fo01_multiple_clients_receive_same_events():
    mgr = SSEManager()
    run_id = str(uuid.uuid4())

    q1_items = []
    q2_items = []

    async def consumer(queue, bucket):
        item = await asyncio.wait_for(queue.get(), timeout=2.0)
        if item is not None:
            bucket.append(item)

    async with mgr.subscribe(run_id) as q1:
        async with mgr.subscribe(run_id) as q2:
            assert mgr.subscriber_count(run_id) == 2

            # Publish one event
            await mgr.publish(run_id, "activity_event", {"msg": "hello"})

            # Both queues should receive it
            t1 = asyncio.create_task(consumer(q1, q1_items))
            t2 = asyncio.create_task(consumer(q2, q2_items))
            await asyncio.gather(t1, t2)

    assert len(q1_items) == 1
    assert len(q2_items) == 1
    assert q1_items[0]["data"]["msg"] == "hello"
    assert q2_items[0]["data"]["msg"] == "hello"


# ---------------------------------------------------------------------------
# FO-02: Events don't cross between different run_ids
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fo02_events_do_not_cross_runs():
    mgr = SSEManager()
    run_a = str(uuid.uuid4())
    run_b = str(uuid.uuid4())

    received_for_b = []

    async with mgr.subscribe(run_a) as q_a:
        async with mgr.subscribe(run_b) as q_b:
            # Publish to run_a only
            await mgr.publish(run_a, "activity_event", {"run": "a"})

            # q_b should be empty after a short wait
            try:
                item = await asyncio.wait_for(q_b.get(), timeout=0.1)
                received_for_b.append(item)
            except asyncio.TimeoutError:
                pass  # Expected — run_b got nothing

    assert len(received_for_b) == 0, (
        f"run_b received an event that was published to run_a: {received_for_b}"
    )


# ---------------------------------------------------------------------------
# FO-03: Subscriber count tracks correctly
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fo03_subscriber_count_tracks():
    mgr = SSEManager()
    run_id = str(uuid.uuid4())

    assert mgr.subscriber_count(run_id) == 0

    async with mgr.subscribe(run_id) as q1:
        assert mgr.subscriber_count(run_id) == 1
        async with mgr.subscribe(run_id) as q2:
            assert mgr.subscriber_count(run_id) == 2
        # q2 context exited → unsubscribed
        # drain the sentinel placed by unsubscribe
        try:
            await asyncio.wait_for(q2.get(), timeout=0.1)
        except asyncio.TimeoutError:
            pass
        assert mgr.subscriber_count(run_id) == 1

    # q1 context exited → unsubscribed; run_id entry removed
    assert mgr.subscriber_count(run_id) == 0


# ---------------------------------------------------------------------------
# FO-04: QueueFull — slow client drops events gracefully
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fo04_queue_full_drops_events_gracefully():
    """A full queue should drop events without raising an exception."""
    run_id = str(uuid.uuid4())

    # Use a tiny maxsize to force overflow quickly
    mgr = SSEManager()
    mgr._QUEUE_MAX_SIZE = 2  # type: ignore[attr-defined] — test override

    q: asyncio.Queue = asyncio.Queue(maxsize=1)
    mgr._subscribers[run_id] = [q]

    # Fill the queue
    await mgr.publish(run_id, "activity_event", {"seq": 1})  # fills the queue
    # This second publish should drop silently (queue is full)
    await mgr.publish(run_id, "activity_event", {"seq": 2})  # dropped

    # Only the first event should be in the queue
    assert q.qsize() == 1
    item = q.get_nowait()
    assert item["data"]["seq"] == 1


# ---------------------------------------------------------------------------
# FO-05: Publish to run with no subscribers is a no-op
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fo05_publish_no_subscribers_is_noop():
    mgr = SSEManager()
    run_id = str(uuid.uuid4())

    # Should not raise
    await mgr.publish(run_id, "activity_event", {"msg": "test"})
    assert mgr.subscriber_count(run_id) == 0


# ---------------------------------------------------------------------------
# FO-06: Multiple events published to multiple subscribers all arrive
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fo06_multiple_events_to_multiple_subscribers():
    mgr = SSEManager()
    run_id = str(uuid.uuid4())

    N_EVENTS = 5
    N_SUBSCRIBERS = 3

    buckets: list[list] = [[] for _ in range(N_SUBSCRIBERS)]

    async def drain(queue: asyncio.Queue, bucket: list, count: int):
        for _ in range(count):
            item = await asyncio.wait_for(queue.get(), timeout=2.0)
            if item is not None:
                bucket.append(item)

    queues = []
    ctx_managers = []

    # Manually enter subscriber contexts
    for i in range(N_SUBSCRIBERS):
        cm = mgr.subscribe(run_id)
        q = await cm.__aenter__()
        queues.append(q)
        ctx_managers.append(cm)

    assert mgr.subscriber_count(run_id) == N_SUBSCRIBERS

    # Publish all events
    for i in range(N_EVENTS):
        await mgr.publish(run_id, "activity_event", {"seq": i + 1})

    # Drain all queues concurrently
    drain_tasks = [
        asyncio.create_task(drain(queues[i], buckets[i], N_EVENTS))
        for i in range(N_SUBSCRIBERS)
    ]
    await asyncio.gather(*drain_tasks)

    # Exit all subscriber contexts
    for i, cm in enumerate(ctx_managers):
        await cm.__aexit__(None, None, None)
        # Drain sentinel
        try:
            await asyncio.wait_for(queues[i].get(), timeout=0.1)
        except asyncio.TimeoutError:
            pass

    for i, bucket in enumerate(buckets):
        assert len(bucket) == N_EVENTS, (
            f"Subscriber {i} received {len(bucket)} events, expected {N_EVENTS}"
        )
        seqs = [item["data"]["seq"] for item in bucket]
        assert seqs == list(range(1, N_EVENTS + 1)), (
            f"Subscriber {i} seq mismatch: {seqs}"
        )


# ---------------------------------------------------------------------------
# FO-07: Module-level singleton is importable and functional
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fo07_module_singleton_is_functional():
    """The module-level sse_manager singleton works correctly."""
    run_id = str(uuid.uuid4())
    received = []

    async with sse_manager.subscribe(run_id) as q:
        await sse_manager.publish(run_id, "heartbeat", {"ts": "now"})
        item = await asyncio.wait_for(q.get(), timeout=1.0)
        if item is not None:
            received.append(item)

    assert len(received) == 1
    assert received[0]["event_type"] == "heartbeat"
