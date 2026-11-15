"""Claim ORM model — Phase 4 M4.4.

An atomic factual claim extracted from a research report.
Claims are scoped to a run and optionally linked to a report.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("research_runs.id", ondelete="CASCADE", name="fk_claims_run_id"),
        nullable=False,
        index=True,
    )
    report_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("research_reports.id", ondelete="CASCADE", name="fk_claims_report_id"),
        nullable=True,
        index=True,
    )
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="factual"
    )
    # "executive_summary" / "key_findings" / "observations" / etc.
    originating_section: Mapped[str] = mapped_column(String(200), nullable=False, default="key_findings")
    is_high_impact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
