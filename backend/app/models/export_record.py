"""ExportRecord ORM model — Phase 5 M5.6.

Tracks export requests and their status for research report files.
Formats: pdf, docx, markdown.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ExportRecord(Base):
    __tablename__ = "export_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("research_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("research_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    # pdf | docx | markdown
    format: Mapped[str] = mapped_column(String(10), nullable=False)
    # pending | generating | ready | failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # Relative path from EXPORT_DIR; set when status = ready
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    run: Mapped["ResearchRun"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ResearchRun", back_populates="export_records"
    )
