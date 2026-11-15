"""Sources API routes — Phase 4 M4.2.

Endpoint: GET /projects/{project_id}/runs/{run_id}/sources
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.source import SourceListResponse, SourceResponse
from app.services.project_service import project_service
from app.services.run_service import run_service
from app.services.source_service import get_sources_for_run

logger = logging.getLogger(__name__)
router = APIRouter()


def _validate_uuid(id_str: str, field_name: str) -> str:
    try:
        uuid.UUID(id_str)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=422, detail=f"Invalid UUID format for {field_name}.")
    return id_str


@router.get("/{project_id}/runs/{run_id}/sources", response_model=SourceListResponse)
async def list_run_sources(
    project_id: str,
    run_id: str,
    offset: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> SourceListResponse:
    """Return paginated sources collected during a research run."""
    _validate_uuid(project_id, "project_id")
    _validate_uuid(run_id, "run_id")
    try:
        project = await project_service.get_project(db, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        run = await run_service.get_run(db, run_id)
        if run is None or run.project_id != project_id:
            raise HTTPException(status_code=404, detail="Run not found.")
        items, total = await get_sources_for_run(db, run_id, offset=offset, limit=limit)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in list_run_sources: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")
    return SourceListResponse(
        items=[SourceResponse.model_validate(s) for s in items],
        total=total,
        run_id=run_id,
    )
