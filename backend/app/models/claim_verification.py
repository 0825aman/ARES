"""ClaimVerification ORM model — Phase 4 M4.4.

The result of verifying a single Claim against collected evidence.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ClaimVerification(Base):
    __tablename__ = "claim_verifications"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    claim_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("claims.id", ondelete="CASCADE", name="fk_claim_verifications_claim_id"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("research_runs.id", ondelete="CASCADE", name="fk_claim_verifications_run_id"),
        nullable=False,
        index=True,
    )
    # supported / partially_supported / contradicted /
    # insufficient_evidence / unverified / not_applicable
    verification_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="unverified"
    )
    supporting_evidence_ids: Mapped[str | None] = mapped_column(Text, nullable=True)    # JSON array
    contradicting_evidence_ids: Mapped[str | None] = mapped_column(Text, nullable=True) # JSON array
    reasoning_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_limitations: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
