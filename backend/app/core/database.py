from collections.abc import AsyncGenerator
import ssl
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


def configure_sqlite_pragmas(
    sync_engine,
    wal_mode: bool,
    busy_timeout_ms: int,
    enforce_foreign_keys: bool = True,
) -> None:
    """Register a SQLAlchemy 'connect' listener that sets SQLite PRAGMAs.

    Call this on any sync engine (or async engine's .sync_engine) that
    connects to SQLite — including test engines.

    - PRAGMA journal_mode=WAL  : allows concurrent reads during writes.
    - PRAGMA foreign_keys=ON   : SQLite ignores FK constraints without this.
    - PRAGMA busy_timeout=N    : wait N ms on a locked DB instead of failing.

    Args:
        sync_engine: SQLAlchemy sync engine (or AsyncEngine.sync_engine).
        wal_mode: Enable WAL journal mode (no-op on :memory: databases).
        busy_timeout_ms: Milliseconds to wait on a locked DB before failing.
        enforce_foreign_keys: Set PRAGMA foreign_keys=ON. Disable in test
            environments where fixtures insert partial FK data.
    """
    @event.listens_for(sync_engine, "connect")
    def _set_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        if wal_mode:
            cursor.execute("PRAGMA journal_mode=WAL")
        if enforce_foreign_keys:
            cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
        cursor.close()


def get_async_database_url(url: str) -> str:
    """Normalize Render/PostgreSQL connection string for SQLAlchemy asyncpg."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Clean query parameters that asyncpg doesn't support as kwargs (e.g. sslmode)
    if "postgresql+asyncpg://" in url:
        parsed = urlparse(url)
        if parsed.query:
            query_dict = parse_qs(parsed.query)
            query_dict.pop("sslmode", None)
            new_query = urlencode(query_dict, doseq=True)
            url = urlunparse(parsed._replace(query=new_query))

    return url


def get_sync_database_url(url: str) -> str:
    """Return a synchronous database URL for Alembic migrations and schema inspection."""
    if url.startswith("sqlite+aiosqlite"):
        return url.replace("sqlite+aiosqlite", "sqlite")
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://") and "+psycopg2" not in url:
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


db_url = get_async_database_url(settings.DATABASE_URL)

connect_args = {}
if "postgresql+asyncpg" in db_url:
    # On remote PostgreSQL (e.g. Render, Neon, Supabase), configure SSL context
    if "localhost" not in db_url and "127.0.0.1" not in db_url:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_ctx

engine_kwargs = {
    "echo": (settings.APP_ENV == "development"),
}
if connect_args:
    engine_kwargs["connect_args"] = connect_args
if "postgresql" in db_url:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300

engine = create_async_engine(db_url, **engine_kwargs)

# Apply PRAGMAs to the production engine when connecting to SQLite
if "sqlite" in db_url:
    configure_sqlite_pragmas(
        engine.sync_engine,
        wal_mode=settings.DB_WAL_MODE,
        busy_timeout_ms=settings.DB_BUSY_TIMEOUT_MS,
    )

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
