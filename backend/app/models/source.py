"""Source ORM model — Phase 4 M4.2.

Represents a normalized source record per research run.
Sources are separate from EvidenceRecord — one Source can have
multiple EvidenceRecord rows derived from it.

Design notes:
- run_id FK with CASCADE DELETE: sources are scoped to a run
- content_hash is used for run-level dedup (same URL/DOI → one Source per run)
- is_peer_reviewed defaults False — never assume arXiv preprints are peer-reviewed
- authors / metadata stored as JSON TEXT (matches SQLite JSON pattern used elsewhere)
- credibility_notes are factual observations only (no numeric score)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("research_runs.id", ondelete="CASCADE", name="fk_sources_run_id"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # web/academic/document/news
    title: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    doi: Mapped[str | None] = mapped_column(String(200), nullable=True)
    authors: Mapped[str | None] = mapped_column(Text, nullable=True)          # JSON array of strings
    publisher: Mapped[str | None] = mapped_column(String(500), nullable=True)
    venue: Mapped[str | None] = mapped_column(String(500), nullable=True)
    publication_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_peer_reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retrieval_provider: Mapped[str] = mapped_column(String(50), nullable=False)  # tavily/arxiv/semantic_scholar
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    is_accessible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    credibility_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON extra fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    run: Mapped["ResearchRun"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ResearchRun", back_populates="sources"
    )
