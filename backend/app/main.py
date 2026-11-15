import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router, auth_router, health_router, protected_router
from app.api.v1.routes.metrics import router as metrics_router
from app.core.config import get_allowed_origins, settings
from app.core.database import AsyncSessionLocal
from app.core.logging_config import configure_logging
from app.core.middleware import RequestIDMiddleware, RequestLoggingMiddleware
from app.core.security import get_current_user

# Configure logging immediately — before any other module uses logging
configure_logging(settings.LOG_FORMAT)

logger = logging.getLogger(__name__)


def _run_alembic_upgrade() -> None:
    """Run alembic upgrade head synchronously at startup.

    If the database is fresh (no tables or missing research_projects), creates
    the schema from Base.metadata and stamps Alembic to head.
    Otherwise applies pending incremental migrations.
    """
    from alembic.config import Config
    from alembic import command
    from sqlalchemy import inspect, create_engine
    from app.core.database import get_sync_database_url
    from app.models.base import Base

    ini_path = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
    alembic_cfg = Config(os.path.abspath(ini_path))

    try:
        sync_url = get_sync_database_url(settings.DATABASE_URL)
        sync_engine = create_engine(sync_url)
        inspector = inspect(sync_engine)
        existing_tables = inspector.get_table_names()

        if not existing_tables or "research_projects" not in existing_tables:
            Base.metadata.create_all(sync_engine)
            command.stamp(alembic_cfg, "head")
            logger.info("Initialized fresh database schema (%d tables) and stamped Alembic to head.", len(Base.metadata.tables))
        else:
            command.upgrade(alembic_cfg, "head")
        sync_engine.dispose()
    except Exception as exc:
        logger.warning("Database schema check failed, attempting standard upgrade head: %s", exc)
        command.upgrade(alembic_cfg, "head")


async def _recover_stuck_runs() -> None:
    """Mark any runs stuck in 'running' or 'pending' state as failed (server restart recovery).

    'running' runs were interrupted mid-execution.
    'pending' runs were queued but the background task never started (process died before dispatch).

    Phase 3: also marks any research_tasks with status='running' as failed.
    """
    from sqlalchemy import or_, select, update
    from app.models.run import ResearchRun

    async with AsyncSessionLocal() as db:
        # Recover stuck runs
        result = await db.execute(
            select(ResearchRun).where(
                or_(ResearchRun.status == "running", ResearchRun.status == "pending")
            )
        )
        stuck = result.scalars().all()
        if stuck:
            now = datetime.now(timezone.utc)
            for run in stuck:
                run.status = "failed"
                run.error_message = "Server restart — run was not executed. Please start a new run."
                run.completed_at = now
            await db.commit()
            logger.warning(
                "Startup recovery: marked %d stuck run(s) as failed.", len(stuck),
                extra={"event": "startup_recovery", "stuck_runs": len(stuck)},
            )

        # Phase 3: recover stuck research tasks (tasks marked running when server died)
        try:
            from app.models.task import ResearchTask
            task_result = await db.execute(
                select(ResearchTask).where(ResearchTask.status == "running")
            )
            stuck_tasks = task_result.scalars().all()
            if stuck_tasks:
                now = datetime.now(timezone.utc)
                for task in stuck_tasks:
                    task.status = "failed"
                    task.error_message = "Server restart during task execution."
                    task.completed_at = now
                await db.commit()
                logger.warning(
                    "Startup recovery: marked %d stuck task(s) as failed.", len(stuck_tasks),
                    extra={"event": "startup_recovery_tasks", "stuck_tasks": len(stuck_tasks)},
                )
        except Exception as exc:
            # ResearchTask table may not exist yet (pre-migration) — safe to ignore
            logger.debug("Task recovery skipped (table may not exist yet): %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Apply all pending database migrations
    _run_alembic_upgrade()
    # Recover any runs/tasks that were interrupted by a server restart
    await _recover_stuck_runs()
    # Seed admin user if none exists (reads ADMIN_USERNAME / ADMIN_PASSWORD_HASH)
    async with AsyncSessionLocal() as db:
        from app.services import auth_service
        await auth_service.seed_admin_user(db)
    # Create upload and export directories if they don't exist
    import pathlib
    pathlib.Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    pathlib.Path(settings.EXPORT_DIR).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="ARES API",
    description="ARES — Autonomous Research & Evidence System — Production Ready",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID", "Last-Event-ID", "Accept", "Cache-Control"],
)
# Note: Starlette processes middleware in reverse registration order.
# RequestIDMiddleware must run first (outermost), so it is added last.
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)

app.include_router(health_router, tags=["health"])
app.include_router(metrics_router, tags=["metrics"])

# Mount protected business routes with get_current_user dependency.
# In development with AUTO_LOGIN_DEV=true, get_current_user automatically returns a synthetic dev user.
# In production, get_current_user strictly validates the session cookie against the database.
app.include_router(
    protected_router,
    prefix="/api/v1",
    dependencies=[Depends(get_current_user)],
)
# Auth endpoints (login, logout, me) handle their own credentials and sessions
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global catch-all for unhandled exceptions.

    Returns a consistent JSON error body with the correlation ID so callers
    can link logs to the failing request. Never leaks internal details.
    """
    request_id = getattr(request.state, "request_id", "-")
    logger.error(
        "Unhandled exception on %s %s [request_id=%s]: %s",
        request.method,
        request.url.path,
        request_id,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
        headers={"X-Request-ID": request_id},
    )


@app.get("/")
async def root():
    return {"message": "ARES API", "version": settings.APP_VERSION}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)

