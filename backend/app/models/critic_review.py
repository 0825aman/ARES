"""CriticReview ORM model — Phase 4 M4.5.

Stores the structured output of the Critic Agent for a multi-agent research run.
One CriticReview is created per review cycle (review_version is 1-based).
Applies only to multi-agent runs.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CriticReview(Base):
    __tablename__ = "critic_reviews"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("research_runs.id", ondelete="CASCADE", name="fk_critic_reviews_run_id"),
        nullable=False,
        index=True,
    )
    # 1-based review cycle counter (first review = 1, second = 2)
    review_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # "strong" / "adequate" / "weak" / "inadequate"
    overall_assessment: Mapped[str] = mapped_column(
        String(50), nullable=False, default="adequate"
    )
    # "approved" / "needs_attention" / "rejected" / "failed"
    review_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="needs_attention"
    )
    # "approve_report" / "request_additional_research" / "request_reverification"
    # / "revise_report" / "reject"
    recommended_action: Mapped[str] = mapped_column(
        String(50), nullable=False, default="revise_report"
    )

    # JSON arrays stored as TEXT (SQLite compatible)
    unsupported_claims: Mapped[str | None] = mapped_column(Text, nullable=True)
    citation_issues: Mapped[str | None] = mapped_column(Text, nullable=True)
    contradictory_findings: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_quality_issues: Mapped[str | None] = mapped_column(Text, nullable=True)
    reasoning_issues: Mapped[str | None] = mapped_column(Text, nullable=True)

    review_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
