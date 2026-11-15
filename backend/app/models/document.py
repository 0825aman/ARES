import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UploadedDocument(Base):
    __tablename__ = "uploaded_documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("research_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("research_projects.id"),
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    extraction_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    # ── Phase 4 M4.1 ──────────────────────────────────────────────────────────
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    has_images: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ocr_attempted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    run: Mapped["ResearchRun"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ResearchRun", back_populates="documents"
    )
    evidence_records: Mapped[list["EvidenceRecord"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "EvidenceRecord", back_populates="document"
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )
