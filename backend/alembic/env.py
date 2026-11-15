import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

from alembic import context

# Ensure the backend app is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import all models so autogenerate detects all tables
from app.models.base import Base  # noqa: E402
from app.models import project  # noqa: E402, F401
from app.models import run  # noqa: E402, F401
from app.models import document  # noqa: E402, F401
from app.models import evidence  # noqa: E402, F401
from app.models import report  # noqa: E402, F401
# Phase 3 models
from app.models import plan  # noqa: E402, F401
from app.models import task  # noqa: E402, F401
from app.models import event  # noqa: E402, F401
# Phase 4 models
from app.models import chunk  # noqa: E402, F401
from app.models import source  # noqa: E402, F401
from app.models import claim  # noqa: E402, F401
from app.models import claim_verification  # noqa: E402, F401
from app.models import critic_review  # noqa: E402, F401
from app.models import citation  # noqa: E402, F401
# Phase 5 models
from app.models import approval  # noqa: E402, F401
from app.models import report_version  # noqa: E402, F401
from app.models import export_record  # noqa: E402, F401
# Phase 6 models
from app.models import user  # noqa: E402, F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_sync_url() -> str:
    """Return a synchronous SQLite URL (no aiosqlite driver)."""
    from app.core.config import settings
    return settings.DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")


def run_migrations_offline() -> None:
    url = get_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Use a synchronous engine for Alembic migrations (SQLite compatible)."""
    url = get_sync_url()
    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        do_run_migrations(connection)
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
