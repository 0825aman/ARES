"""GET /projects/{project_id}/runs/{run_id}/review — Phase 4 M4.5.

Returns the latest CriticReview for a given run.
The Critic only runs for multi-agent runs; returns 404 for sequential runs
that have no review.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.critic_review import CriticReview
from app.schemas.critic import CriticReviewResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def _parse_json_list(value: str | None) -> list[str]:
    """Safely parse a JSON-encoded list field from the DB."""
    if not value:
        return []
    try:
        result = json.loads(value)
        return result if isinstance(result, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


@router.get(
    "/{project_id}/runs/{run_id}/review",
    response_model=CriticReviewResponse,
    summary="Get latest Critic review for a run",
    responses={
        404: {"description": "No review exists for this run"},
    },
)
async def get_critic_review(
    project_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
) -> CriticReviewResponse:
    """Return the latest (highest review_version) CriticReview for the run."""
    result = await db.execute(
        select(CriticReview)
        .where(CriticReview.run_id == run_id)
        .order_by(CriticReview.review_version.desc())
        .limit(1)
    )
    review = result.scalar_one_or_none()

    if review is None:
        raise HTTPException(
            status_code=404,
            detail=f"No critic review found for run {run_id}",
        )

    return CriticReviewResponse(
        id=review.id,
        run_id=review.run_id,
        review_version=review.review_version,
        overall_assessment=review.overall_assessment,
        review_status=review.review_status,
        recommended_action=review.recommended_action,
        unsupported_claims=_parse_json_list(review.unsupported_claims),
        citation_issues=_parse_json_list(review.citation_issues),
        contradictory_findings=_parse_json_list(review.contradictory_findings),
        missing_evidence=_parse_json_list(review.missing_evidence),
        source_quality_issues=_parse_json_list(review.source_quality_issues),
        reasoning_issues=_parse_json_list(review.reasoning_issues),
        review_summary=review.review_summary,
        created_at=review.created_at,
    )
