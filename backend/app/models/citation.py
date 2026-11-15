"""Citation ORM model — Phase 4 M4.6.

Links every report source reference to a traceable evidence-source chain.
One Citation is created per [SOURCE N] label found in a report.

Design notes:
- evidence_id is NOT NULL — every citation must be traceable to evidence
- claim_id is nullable — only populated when claim_verifier ran
- source_id is nullable — only populated when a Source record exists
- apa_formatted and ieee_formatted are computed deterministically from Source data
- is_verified tracks whether all 7 validator checks passed
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("research_runs.id", ondelete="CASCADE", name="fk_citations_run_id"),
        nullable=False,
        index=True,
    )
    report_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("research_reports.id", ondelete="CASCADE", name="fk_citations_report_id"),
        nullable=False,
        index=True,
    )
    # Optional FK to a Claim — set when claim_verifier ran for this run
    claim_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("claims.id", ondelete="SET NULL", name="fk_citations_claim_id"),
        nullable=True,
        index=True,
    )
    # FK to EvidenceRecord — required; every citation must have evidence
    evidence_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("evidence_records.id", ondelete="CASCADE", name="fk_citations_evidence_id"),
        nullable=False,
        index=True,
    )
    # Optional FK to Source — set when Source record exists for the evidence
    source_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("sources.id", ondelete="SET NULL", name="fk_citations_source_id"),
        nullable=True,
        index=True,
    )
    # "[SOURCE 1]" — matches the label used in the report text
    citation_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    page_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    section_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    doi: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Deterministic formatted citations (never LLM-generated)
    apa_formatted: Mapped[str | None] = mapped_column(Text, nullable=True)
    ieee_formatted: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    validation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
