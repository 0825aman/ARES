"""GET /projects/{project_id}/runs/{run_id}/citations — Phase 4 M4.6.

Returns the full bibliography (all Citation records) for a given run.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.citation import Citation
from app.schemas.citation import BibliographyResponse, CitationResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/{project_id}/runs/{run_id}/citations",
    response_model=BibliographyResponse,
    summary="Get all citations for a run",
)
async def get_citations(
    project_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
) -> BibliographyResponse:
    """Return the full bibliography for a run, ordered by citation_key."""
    result = await db.execute(
        select(Citation)
        .where(Citation.run_id == run_id)
        .order_by(Citation.citation_key)
    )
    citations = result.scalars().all()

    citation_responses = [
        CitationResponse.model_validate(c) for c in citations
    ]

    verified_count = sum(1 for c in citations if c.is_verified)

    # Determine report_id from first citation (all share the same report)
    report_id = citations[0].report_id if citations else None

    return BibliographyResponse(
        run_id=run_id,
        report_id=report_id,
        total=len(citation_responses),
        verified_count=verified_count,
        citations=citation_responses,
    )
