import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.task import ResearchTask
    from app.models.chunk import DocumentChunk
    from app.models.source import Source

from app.models.base import Base


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("research_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_label: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fetch_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="success"
    )
    fetch_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    document_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("uploaded_documents.id"),
        nullable=True,
    )
    chunk_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Phase 3: links evidence to the specific research task that collected it
    task_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("research_tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # ── Phase 4 M4.3 — enriched evidence schema ────────────────────────────────
    source_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("sources.id", ondelete="SET NULL", name="fk_evidence_source_id"),
        nullable=True,
        index=True,
    )
    chunk_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("document_chunks.id", ondelete="SET NULL", name="fk_evidence_chunk_id"),
        nullable=True,
    )
    evidence_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="other"
    )
    evidence_relationship: Mapped[str] = mapped_column(
        String(50), nullable=False, default="neutral"
    )
    section_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    extraction_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    run: Mapped["ResearchRun"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ResearchRun", back_populates="evidence"
    )
    document: Mapped["UploadedDocument | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "UploadedDocument", back_populates="evidence_records"
    )
    task: Mapped["ResearchTask | None"] = relationship(
        "ResearchTask", back_populates="evidence_records"
    )
    source: Mapped["Source | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Source",
    )
    chunk: Mapped["DocumentChunk | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "DocumentChunk",
    )
