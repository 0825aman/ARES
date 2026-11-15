"""Claim service — Phase 4 M4.4. CRUD for Claim and ClaimVerification records."""
from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.claim import Claim
from app.models.claim_verification import ClaimVerification

logger = logging.getLogger(__name__)


async def get_claims_for_run(
    db: AsyncSession,
    run_id: str,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[Claim], int]:
    count_result = await db.execute(
        select(func.count(Claim.id)).where(Claim.run_id == run_id)
    )
    total = count_result.scalar_one()
    items_result = await db.execute(
        select(Claim)
        .where(Claim.run_id == run_id)
        .order_by(Claim.created_at)
        .offset(offset)
        .limit(limit)
    )
    return list(items_result.scalars().all()), total


async def get_verification_for_claim(
    db: AsyncSession,
    claim_id: str,
) -> ClaimVerification | None:
    result = await db.execute(
        select(ClaimVerification).where(ClaimVerification.claim_id == claim_id)
    )
    return result.scalar_one_or_none()


async def get_all_verifications_for_run(
    db: AsyncSession,
    run_id: str,
) -> list[ClaimVerification]:
    result = await db.execute(
        select(ClaimVerification).where(ClaimVerification.run_id == run_id)
    )
    return list(result.scalars().all())
