from __future__ import annotations

import os
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Set test environment BEFORE importing app — the app registers routers at
# import time based on settings, so AUTO_LOGIN_DEV must be set first.
# This bypasses authentication in ALL tests (the auth tests use their own
# fixtures that work around the dev bypass as needed).
# ---------------------------------------------------------------------------
os.environ.setdefault("AUTO_LOGIN_DEV", "true")
os.environ.setdefault("APP_ENV", "development")

from app.core.database import configure_sqlite_pragmas, get_db
from app.core.config import settings
from app.main import app
from app.models.base import Base
from app.models import project as _project_models  # noqa: F401
from app.models import run as _run_models  # noqa: F401
from app.models import document as _document_models  # noqa: F401
from app.models import evidence as _evidence_models  # noqa: F401
from app.models import report as _report_models  # noqa: F401
# Phase 3 models — required so test in-memory DB includes their tables
from app.models import plan as _plan_models  # noqa: F401
from app.models import task as _task_models  # noqa: F401
from app.models import event as _event_models  # noqa: F401
# Phase 4 models
from app.models import chunk as _chunk_models  # noqa: F401
from app.models import source as _source_models  # noqa: F401
from app.models import claim as _claim_models  # noqa: F401
from app.models import claim_verification as _claim_verification_models  # noqa: F401
from app.models import critic_review as _critic_review_models  # noqa: F401
from app.models import citation as _citation_models  # noqa: F401
# Phase 5 models
from app.models import approval as _approval_models  # noqa: F401
from app.models import report_version as _report_version_models  # noqa: F401
from app.models import export_record as _export_record_models  # noqa: F401
# Phase 6 models
from app.models import user as _user_models  # noqa: F401
import app.graph.checkpointer as _checkpointer_module
import app.graph.workflow as _workflow_module

# ---------------------------------------------------------------------------
# In-memory SQLite engine for tests — each test gets a fresh schema
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)

# Apply WAL (no-op for :memory:) and busy_timeout to the test engine.
# foreign_keys is intentionally NOT set on the test engine — many test
# fixtures insert partial data that would violate FK constraints.
# FK enforcement is verified against a dedicated file-based engine in
# test_database_config.py.
configure_sqlite_pragmas(
    test_engine.sync_engine,
    wal_mode=settings.DB_WAL_MODE,
    busy_timeout_ms=settings.DB_BUSY_TIMEOUT_MS,
    enforce_foreign_keys=False,
)

TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


# ---------------------------------------------------------------------------
# Function-scoped: recreate schema before each test (full isolation)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def reset_db():
    """Drop and recreate all tables before every test for full isolation.

    Also resets the LangGraph checkpointer singleton and compiled graph so
    that each test gets a fresh aiosqlite connection bound to its own event
    loop.  Without this, tests that run the graph would fail with
    'Lock is bound to a different event loop'.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Reset checkpointer + graph singletons so the next test opens a fresh
    # aiosqlite connection on its own event loop.
    if _checkpointer_module._conn is not None:
        try:
            await _checkpointer_module._conn.close()
        except Exception:
            pass
    _checkpointer_module._checkpointer = None
    _checkpointer_module._conn = None
    _workflow_module._graph = None

    yield


# ---------------------------------------------------------------------------
# Dependency override: inject the test session instead of the real DB
# ---------------------------------------------------------------------------


async def override_get_db():
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


# ---------------------------------------------------------------------------
# HTTP test client fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def async_client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Convenience fixture: a raw DB session for test setup helpers
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with TestSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# Auth fixtures — user, session, authenticated client
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Create a test admin user in the in-memory DB."""
    from app.core.security import hash_password
    from app.models.user import User
    from datetime import datetime, timezone

    user = User(
        id="test-user-00000000-0000-0000-0000-000000000001",
        username="testadmin",
        hashed_password=hash_password("testpass123"),
        role="admin",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def test_session(test_user, db_session: AsyncSession):
    """Create a valid session for the test user."""
    from app.services.auth_service import create_session
    return await create_session(db_session, test_user.id, ip_address="127.0.0.1")


@pytest_asyncio.fixture
async def authenticated_client(test_session) -> AsyncClient:
    """An AsyncClient pre-loaded with a valid session cookie."""
    from app.core.security import SESSION_COOKIE_NAME
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={SESSION_COOKIE_NAME: test_session.id},
    ) as client:
        yield client
