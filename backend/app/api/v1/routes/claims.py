"""Claims API routes — Phase 4 M4.4."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.claim import ClaimListResponse, ClaimResponse, ClaimVerificationResponse, VerificationSummary
from app.services.claim_service import get_claims_for_run, get_all_verifications_for_run, get_verification_for_claim
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


@router.get("/{project_id}/runs/{run_id}/claims", response_model=ClaimListResponse)
async def list_run_claims(
    project_id: str,
    run_id: str,
    offset: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> ClaimListResponse:
    """Return all claims with their verification results for a run."""
    _validate_uuid(project_id, "project_id")
    _validate_uuid(run_id, "run_id")
    try:
        project = await project_service.get_project(db, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        run = await run_service.get_run(db, run_id)
        if run is None or run.project_id != project_id:
            raise HTTPException(status_code=404, detail="Run not found.")

        claims, total = await get_claims_for_run(db, run_id, offset=offset, limit=limit)
        verifications = await get_all_verifications_for_run(db, run_id)
        verif_by_claim = {v.claim_id: v for v in verifications}

        items = []
        for claim in claims:
            verif = verif_by_claim.get(claim.id)
            claim_resp = ClaimResponse.model_validate(claim)
            if verif:
                claim_resp.verification = ClaimVerificationResponse.model_validate(verif)
            items.append(claim_resp)

        # Build summary from all verifications for this run
        summary = None
        if verifications:
            status_counts: dict[str, int] = {
                "supported": 0, "partially_supported": 0, "contradicted": 0,
                "insufficient_evidence": 0, "unverified": 0, "not_applicable": 0,
            }
            for v in verifications:
                if v.verification_status in status_counts:
                    status_counts[v.verification_status] += 1
            summary = VerificationSummary(
                total_claims=len(verifications),
                claim_ids=[v.claim_id for v in verifications],
                **status_counts,
            )

    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in list_run_claims: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")

    return ClaimListResponse(
        items=items,
        total=total,
        run_id=run_id,
        verification_summary=summary,
    )
