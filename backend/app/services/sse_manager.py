"""SSEManager — in-process Server-Sent Events fan-out service.

Manages per-run subscriber queues so that multiple browser tabs can each
receive their own stream of events while the backend publishes to all of them.

Usage:
    # Publishing (from event_service, run_service, etc.)
    from app.services.sse_manager import sse_manager
    await sse_manager.publish(run_id, "activity_event", data_dict)

    # Subscribing (from SSE route)
    async with sse_manager.subscribe(run_id) as queue:
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# Maximum events buffered per subscriber before dropping (slow-client protection).
_QUEUE_MAX_SIZE = 200


class SSEManager:
    """Fan-out SSE manager using asyncio.Queue per subscriber.

    Thread-safety note: this is designed for a single asyncio event loop
    (standard FastAPI/uvicorn single-process deployment).  It is NOT safe to
    share across processes — no Redis required.
    """

    def __init__(self) -> None:
        # run_id → list[asyncio.Queue]
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    # ── Publishing ────────────────────────────────────────────────────────────

    async def publish(self, run_id: str, event_type: str, data: dict) -> None:
        """Push an event to every active subscriber for the given run.

        If a subscriber's queue is full the event is dropped for that
        subscriber — the client will replay from DB on reconnect using
        Last-Event-ID.
        """
        payload = {"event_type": event_type, "data": data}
        queues = list(self._subscribers.get(run_id, []))
        for q in queues:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                logger.warning(
                    "sse_manager: queue full for run %s — dropping event %s",
                    run_id,
                    event_type,
                )

    # ── Subscribing ───────────────────────────────────────────────────────────

    @asynccontextmanager
    async def subscribe(self, run_id: str) -> AsyncGenerator[asyncio.Queue, None]:
        """Context manager that registers a new subscriber queue for a run.

        Yields the queue.  On exit (normal or exception) the queue is removed
        from the subscriber list.  A ``None`` sentinel is placed into the
        queue on exit so any consumer loop can detect the end cleanly.

        Example::

            async with sse_manager.subscribe(run_id) as queue:
                while True:
                    item = await asyncio.wait_for(queue.get(), timeout=30)
                    if item is None:
                        break
                    yield item
        """
        q: asyncio.Queue = asyncio.Queue(maxsize=_QUEUE_MAX_SIZE)
        self._subscribers.setdefault(run_id, []).append(q)
        logger.debug(
            "sse_manager: new subscriber for run %s (total=%d)",
            run_id,
            len(self._subscribers[run_id]),
        )
        try:
            yield q
        finally:
            self._unsubscribe(run_id, q)

    def _unsubscribe(self, run_id: str, q: asyncio.Queue) -> None:
        """Remove a queue from the subscriber list."""
        subs = self._subscribers.get(run_id)
        if subs is None:
            return
        try:
            subs.remove(q)
        except ValueError:
            pass
        if not subs:
            self._subscribers.pop(run_id, None)
        logger.debug(
            "sse_manager: subscriber removed for run %s (remaining=%d)",
            run_id,
            len(self._subscribers.get(run_id, [])),
        )
        # Signal the consumer that the stream is closing
        try:
            q.put_nowait(None)
        except asyncio.QueueFull:
            pass

    # ── Introspection (for tests) ─────────────────────────────────────────────

    def subscriber_count(self, run_id: str) -> int:
        """Return the number of active subscribers for a run."""
        return len(self._subscribers.get(run_id, []))


# Module-level singleton — imported everywhere in the app
sse_manager = SSEManager()
