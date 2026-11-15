"""LangGraph AsyncSqliteSaver checkpointer — module-level async singleton.

``AsyncSqliteSaver`` is the async-compatible checkpointer for LangGraph 1.2.x
when using ``graph.ainvoke()``.  It requires an open ``aiosqlite.Connection``.

The connection is opened lazily on first call to ``get_checkpointer()`` and
reused for the lifetime of the process.

``aiosqlite`` is already installed as a transitive dependency of
``sqlalchemy[asyncio]``.
"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

_checkpointer = None
_conn = None


async def get_checkpointer():
    """Return the process-level AsyncSqliteSaver instance.

    Opens the aiosqlite connection on first call and caches it.
    Thread ID = ``run_id`` (UUID string) — each run is fully isolated.
    """
    global _checkpointer, _conn

    if _checkpointer is None:
        import aiosqlite
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        from app.core.config import settings

        _conn = await aiosqlite.connect(settings.CHECKPOINT_DB_URL)
        _checkpointer = AsyncSqliteSaver(_conn)
        # Run setup to create the checkpointer's internal schema tables
        await _checkpointer.setup()
        logger.info("AsyncSqliteSaver checkpointer initialised: %s", settings.CHECKPOINT_DB_URL)

    return _checkpointer
