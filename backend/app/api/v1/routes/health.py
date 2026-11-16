from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.schemas.project import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health/live")
async def liveness_check():
    """Liveness probe — always returns 200 as long as the process is running.

    Use this for container/orchestrator liveness checks.
    Does NOT check the database — that is the readiness check's job.
    """
    return {"status": "alive"}


@router.get("/health/version")
async def version_check(db: AsyncSession = Depends(get_db)):
    """Diagnostic version and deployment check."""
    import os
    import pathlib
    import traceback
    from app.models.user import User
    from sqlalchemy import select, func
    from app.services.export_service import _get_unicode_font_name

    user_count = 0
    db_err = None
    try:
        res = await db.execute(select(func.count()).select_from(User))
        user_count = res.scalar_one()
    except Exception as exc:
        db_err = str(exc)

    font_err = None
    active_font = None
    try:
        active_font = _get_unicode_font_name()
    except Exception as exc:
        font_err = f"{exc}\n{traceback.format_exc()}"

    curr_p = pathlib.Path(__file__).resolve()
    base_dir = curr_p.parent.parent.parent.parent
    font_candidates = [
        str(base_dir / "assets" / "fonts" / "FreeSerif.ttf"),
        str(pathlib.Path("app/assets/fonts/FreeSerif.ttf").resolve()),
        str(pathlib.Path("backend/app/assets/fonts/FreeSerif.ttf").resolve()),
    ]
    font_existence = {p: pathlib.Path(p).is_file() for p in font_candidates}

    return {
        "version": settings.APP_VERSION,
        "commit": os.environ.get("RENDER_GIT_COMMIT", "local"),
        "user_count": user_count,
        "admin_hash_configured": bool(settings.ADMIN_PASSWORD_HASH),
        "db_error": db_err,
        "active_pdf_font": active_font,
        "font_error": font_err,
        "font_existence": font_existence,
        "cwd": os.getcwd(),
        "file_path": str(curr_p),
    }


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness probe — returns 200 only when the database is accessible.

    Returns 503 when the database is unavailable so load-balancers and
    container orchestrators stop routing traffic to an unhealthy instance.
    """
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception as exc:
        logger.error("Readiness check — database unavailable: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "error"},
        )


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Full health check — returns application version/environment and DB status.

    Returns HTTP 200 when healthy, HTTP 503 when the database is unavailable.
    The ``status`` field is always ``"ok"``; use the HTTP status code to
    determine overall health in automated tooling.
    """
    try:
        await db.execute(text("SELECT 1"))
        db_status: Literal["ok", "error"] = "ok"
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        db_status = "error"

    response_body = HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        database=db_status,
    )

    if db_status == "error":
        return JSONResponse(
            status_code=503,
            content=response_body.model_dump(),
        )

    return response_body
