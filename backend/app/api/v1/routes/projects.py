from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectStatus,
    ProjectSummaryResponse,
    ProjectUpdateRequest,
)
from app.services.project_service import project_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _validate_project_id(project_id: str) -> str:
    """Validate that project_id is a valid UUID string, raising 422 if not."""
    try:
        uuid.UUID(project_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "loc": ["path", "project_id"],
                    "msg": "Invalid UUID format",
                    "type": "uuid_parsing",
                }
            ],
        )
    return project_id


# ---------------------------------------------------------------------------
# Route 1: GET /summary — MUST be registered before /{project_id}
# ---------------------------------------------------------------------------


@router.get("/summary", response_model=ProjectSummaryResponse)
async def get_summary(db: AsyncSession = Depends(get_db)) -> ProjectSummaryResponse:
    try:
        return await project_service.get_summary(db)
    except SQLAlchemyError as exc:
        logger.error("Database error in get_summary: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------------------------------------------------------
# Route 2: GET / — list all projects (supports both /projects and /projects/)
# ---------------------------------------------------------------------------


@router.get("", response_model=ProjectListResponse, include_in_schema=False)
@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    status: ProjectStatus | None = None,
    db: AsyncSession = Depends(get_db),
) -> ProjectListResponse:
    try:
        items, total = await project_service.get_projects(db, limit, offset, status)
    except SQLAlchemyError as exc:
        logger.error("Database error in list_projects: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")

    return ProjectListResponse(
        items=[ProjectResponse.model_validate(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# Route 3: POST / — create a project (supports both /projects and /projects/)
# ---------------------------------------------------------------------------


@router.post("", response_model=ProjectResponse, status_code=201, include_in_schema=False)
@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    try:
        project = await project_service.create_project(db, data)
    except SQLAlchemyError as exc:
        logger.error("Database error in create_project: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")
    return ProjectResponse.model_validate(project)


# ---------------------------------------------------------------------------
# Route 4: GET /{project_id} — get a single project
# ---------------------------------------------------------------------------


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    _validate_project_id(project_id)
    try:
        project = await project_service.get_project(db, project_id)
    except SQLAlchemyError as exc:
        logger.error("Database error in get_project: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return ProjectResponse.model_validate(project)


# ---------------------------------------------------------------------------
# Route 5: PATCH /{project_id} — partial update
# ---------------------------------------------------------------------------


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    _validate_project_id(project_id)
    try:
        project = await project_service.get_project(db, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        project = await project_service.update_project(db, project, data)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("Database error in update_project: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")
    return ProjectResponse.model_validate(project)


# ---------------------------------------------------------------------------
# Route 6: DELETE /{project_id} — delete a project
# ---------------------------------------------------------------------------


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    _validate_project_id(project_id)
    try:
        project = await project_service.get_project(db, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        await project_service.delete_project(db, project)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("Database error in delete_project: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")
    return Response(status_code=204)
