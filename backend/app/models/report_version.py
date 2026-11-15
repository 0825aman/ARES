"""ReportVersion ORM model — Phase 5 M5.6.

Archive table that snapshots a ResearchReport before it is superseded
by a new version. Append-only — no updates after insert.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ReportVersion(Base):
    __tablename__ = "report_versions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    report_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("research_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    archived_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    # JSON-serialised snapshot of the full report content at archival time
    content_snapshot: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationship back to the report
    report: Mapped["ResearchReport"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ResearchReport", back_populates="versions"
    )
