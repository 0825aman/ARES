"""Evidence API routes — Phase 4 M4.3.

Endpoint: GET /projects/{project_id}/runs/{run_id}/evidence
"""
from __future__ import annotations

import logging
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.evidence import EvidenceRecord
from app.schemas.evidence import EvidenceListResponse, EvidenceResponse
from app.services.project_service import project_service
from app.services.run_service import run_service

logger = logging.getLogger(__name__)
router = APIRouter()


def _validate_uuid(id_str: str, field_name: str) -> str:
    try:
        uuid.UUID(id_str)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=422, detail=f"Invalid UUID format for {field_name}.")
    return id_str


@router.get("/{project_id}/runs/{run_id}/evidence", response_model=EvidenceListResponse)
async def list_run_evidence(
    project_id: str,
    run_id: str,
    offset: int = 0,
    limit: int = 50,
    evidence_type: str | None = Query(default=None, description="Filter by evidence_type"),
    evidence_relationship: str | None = Query(default=None, description="Filter by evidence_relationship"),
    db: AsyncSession = Depends(get_db),
) -> EvidenceListResponse:
    """Return paginated evidence records for a run.

    Optional filters:
      - evidence_type: statistical|experimental|observational|expert_opinion|historical|official|survey|interpretative|other
      - evidence_relationship: supports|contradicts|qualifies|contextualizes|neutral
    """
    _validate_uuid(project_id, "project_id")
    _validate_uuid(run_id, "run_id")
    try:
        project = await project_service.get_project(db, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        run = await run_service.get_run(db, run_id)
        if run is None or run.project_id != project_id:
            raise HTTPException(status_code=404, detail="Run not found.")

        # Build base query
        base_q = select(EvidenceRecord).where(EvidenceRecord.run_id == run_id)
        count_q = select(func.count(EvidenceRecord.id)).where(EvidenceRecord.run_id == run_id)

        if evidence_type:
            base_q = base_q.where(EvidenceRecord.evidence_type == evidence_type)
            count_q = count_q.where(EvidenceRecord.evidence_type == evidence_type)
        if evidence_relationship:
            base_q = base_q.where(EvidenceRecord.evidence_relationship == evidence_relationship)
            count_q = count_q.where(EvidenceRecord.evidence_relationship == evidence_relationship)

        count_result = await db.execute(count_q)
        total = count_result.scalar_one()

        items_result = await db.execute(
            base_q.order_by(EvidenceRecord.relevance_score.desc()).offset(offset).limit(limit)
        )
        items = list(items_result.scalars().all())

    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in list_run_evidence: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")

    return EvidenceListResponse(
        items=[EvidenceResponse.model_validate(e) for e in items],
        total=total,
        run_id=run_id,
    )
