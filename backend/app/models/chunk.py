"""DocumentChunk ORM model — Phase 4 M4.1.

Represents a single structured extract from an uploaded document.
Chunks are created on document upload and are permanent records
that outlive individual research runs.

Design notes:
- document_id FK with CASCADE DELETE: chunks are deleted when the parent document is deleted
- chunk_index is 0-based, sequential within a document
- page_start / page_end are populated for PDF documents only (1-based page numbers)
- section_title / heading_level are populated for DOCX files with Heading paragraphs
- extraction_method records which extractor produced this chunk
- char_count caches len(text) to avoid full-text scans for size queries
- has_tables flags chunks that contain detected table content (future use)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("uploaded_documents.id", ondelete="CASCADE", name="fk_chunks_document_id"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    heading_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extraction_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    has_tables: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    document: Mapped["UploadedDocument"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "UploadedDocument", back_populates="chunks"
    )

    @validates("text", "section_title")
    def _validate_clean_text(self, key: str, value: str | None) -> str | None:
        if isinstance(value, str) and "\x00" in value:
            return value.replace("\x00", "")
        return value
