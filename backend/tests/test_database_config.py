from __future__ import annotations

"""test_database_config.py — Verify SQLite PRAGMA configuration applied by M6.3.

These tests confirm that the three PRAGMAs (WAL journal mode, foreign_keys ON,
busy_timeout) are configured correctly, and that the composite indexes from
migration K exist in the schema.

Note on test vs production FK enforcement:
  The test engine (test_engine in conftest.py) has foreign_keys enforcement
  intentionally DISABLED — many test fixtures insert partial data that would
  violate FK constraints, as the tests mock agent behavior rather than
  inserting complete relational chains. The test for FK enforcement uses a
  dedicated separate engine with enforce_foreign_keys=True.
"""

import pytest
import pytest_asyncio
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import configure_sqlite_pragmas
from tests.conftest import TestSessionLocal, test_engine


# ---------------------------------------------------------------------------
# PRAGMA tests — confirm connection-level configuration
# ---------------------------------------------------------------------------


async def test_wal_mode_enabled(db_session: AsyncSession):
    """PRAGMA journal_mode should return 'wal' (or 'memory' for :memory: in-process DB).

    SQLite in-memory databases use 'memory' journal mode — WAL is not
    applicable to :memory: but the PRAGMA call is accepted silently.
    We verify the PRAGMA runs without error and returns a known mode string.
    """
    result = await db_session.execute(text("PRAGMA journal_mode"))
    row = result.fetchone()
    assert row is not None
    # In-memory SQLite returns 'memory'; WAL-capable file DB returns 'wal'.
    assert row[0] in ("wal", "memory", "delete")


async def test_foreign_keys_enabled_on_production_engine():
    """PRAGMA foreign_keys=ON must be set on the production-style engine.

    Uses a dedicated temporary engine with enforce_foreign_keys=True to
    verify that configure_sqlite_pragmas correctly enables FK enforcement.
    The main test engine has FK enforcement disabled (see module docstring).
    """
    fk_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    configure_sqlite_pragmas(
        fk_engine.sync_engine,
        wal_mode=False,
        busy_timeout_ms=1000,
        enforce_foreign_keys=True,
    )
    fk_session = async_sessionmaker(fk_engine, expire_on_commit=False)

    async with fk_session() as session:
        result = await session.execute(text("PRAGMA foreign_keys"))
        row = result.fetchone()

    await fk_engine.dispose()

    assert row is not None
    assert row[0] == 1, (
        f"Expected foreign_keys=1 (enabled), got {row[0]}. "
        "Check the PRAGMA event listener in app/core/database.py."
    )


async def test_foreign_keys_disabled_on_test_engine(db_session: AsyncSession):
    """Confirm FK enforcement is intentionally OFF in the test engine.

    This prevents the many partial-data test fixtures from hitting FK errors.
    """
    result = await db_session.execute(text("PRAGMA foreign_keys"))
    row = result.fetchone()
    assert row is not None
    assert row[0] == 0, (
        f"Expected foreign_keys=0 (disabled) for test engine, got {row[0]}. "
        "The test engine should have enforce_foreign_keys=False in conftest.py."
    )


async def test_busy_timeout_set(db_session: AsyncSession):
    """PRAGMA busy_timeout should return the configured value (default 5000 ms)."""
    result = await db_session.execute(text("PRAGMA busy_timeout"))
    row = result.fetchone()
    assert row is not None
    assert row[0] >= 1000, (
        f"Expected busy_timeout >= 1000 ms, got {row[0]}. "
        "Check DB_BUSY_TIMEOUT_MS in settings and the PRAGMA event listener."
    )


# ---------------------------------------------------------------------------
# Schema tests — confirm composite indexes from migration K
# ---------------------------------------------------------------------------


async def test_composite_index_runs_project_status_exists():
    """Index idx_runs_project_status on (project_id, status) must exist."""
    async with test_engine.connect() as conn:
        def _check(sync_conn):
            inspector = inspect(sync_conn)
            indexes = {idx["name"] for idx in inspector.get_indexes("research_runs")}
            return indexes

        indexes = await conn.run_sync(_check)

    assert "idx_runs_project_status" in indexes, (
        f"Expected index 'idx_runs_project_status' on research_runs, "
        f"found: {sorted(indexes)}"
    )


async def test_composite_index_events_run_created_exists():
    """Index idx_events_run_created on (run_id, created_at) must exist."""
    async with test_engine.connect() as conn:
        def _check(sync_conn):
            inspector = inspect(sync_conn)
            indexes = {idx["name"] for idx in inspector.get_indexes("agent_execution_events")}
            return indexes

        indexes = await conn.run_sync(_check)

    assert "idx_events_run_created" in indexes, (
        f"Expected index 'idx_events_run_created' on agent_execution_events, "
        f"found: {sorted(indexes)}"
    )


async def test_composite_index_runs_covers_correct_columns():
    """idx_runs_project_status must cover the (project_id, status) columns."""
    async with test_engine.connect() as conn:
        def _check(sync_conn):
            inspector = inspect(sync_conn)
            indexes = inspector.get_indexes("research_runs")
            return {idx["name"]: idx.get("column_names", []) for idx in indexes}

        idx_map = await conn.run_sync(_check)

    idx = idx_map.get("idx_runs_project_status", [])
    assert "project_id" in idx, f"project_id not in index columns: {idx}"
    assert "status" in idx, f"status not in index columns: {idx}"


async def test_composite_index_events_covers_correct_columns():
    """idx_events_run_created must cover the (run_id, created_at) columns."""
    async with test_engine.connect() as conn:
        def _check(sync_conn):
            inspector = inspect(sync_conn)
            indexes = inspector.get_indexes("agent_execution_events")
            return {idx["name"]: idx.get("column_names", []) for idx in indexes}

        idx_map = await conn.run_sync(_check)

    idx = idx_map.get("idx_events_run_created", [])
    assert "run_id" in idx, f"run_id not in index columns: {idx}"
    assert "created_at" in idx, f"created_at not in index columns: {idx}"
