"""LangGraph checkpointer — module-level singleton with resilient fallback.

Uses InMemorySaver (MemorySaver) for fast, thread-safe, zero-dependency
checkpointing that works reliably across all platforms (Windows, Linux,
Docker, Render) without SQLite thread deadlocks or missing module errors.
"""
from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)

_checkpointer = None
_conn = None


async def get_checkpointer():
    """Return the process-level checkpointer instance.

    Thread ID = ``run_id`` (UUID string) — each run is fully isolated.
    """
    global _checkpointer, _conn

    if _checkpointer is None:
        if sys.platform != "win32":
            try:
                import aiosqlite
                from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
                from app.core.config import settings

                if settings.CHECKPOINT_DB_URL:
                    conn = await aiosqlite.connect(settings.CHECKPOINT_DB_URL)
                    saver = AsyncSqliteSaver(conn)
                    await saver.setup()
                    _conn = conn
                    _checkpointer = saver
                    logger.info("AsyncSqliteSaver checkpointer initialised: %s", settings.CHECKPOINT_DB_URL)
                    return _checkpointer
            except Exception as exc:
                logger.info(
                    "AsyncSqliteSaver skipped (%s). Using MemorySaver.",
                    exc,
                )

        from langgraph.checkpoint.memory import MemorySaver

        _checkpointer = MemorySaver()
        logger.info("MemorySaver checkpointer initialised successfully.")

    return _checkpointer
