import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.report_version import ReportVersion


class ResearchReport(Base):
    __tablename__ = "research_reports"
    __table_args__ = (
        UniqueConstraint("run_id", "version_number", name="uq_research_reports_run_version"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("research_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Phase 5 M5.6 — Report versioning
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    research_question: Mapped[str] = mapped_column(Text, nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON arrays stored as TEXT (SQLite compatible)
    key_findings: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_used: Mapped[str] = mapped_column(Text, nullable=False)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    contradictions: Mapped[str | None] = mapped_column(Text, nullable=True)
    limitations: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[str] = mapped_column(Text, nullable=False)
    raw_llm_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    # ── Phase 4 M4.6 — Citation validation columns ──────────────────────────
    has_validated_citations: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    # "draft" / "verified" / "needs_attention" / "rejected"
    review_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    run: Mapped["ResearchRun"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ResearchRun", back_populates="report"
    )
    versions: Mapped[list["ReportVersion"]] = relationship(
        "ReportVersion",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="ReportVersion.version_number",
    )

    @validates(
        "research_question", "executive_summary", "key_findings",
        "evidence_used", "observations", "contradictions", "limitations",
        "sources", "raw_llm_response"
    )
    def _validate_clean_text(self, key: str, value: str | None) -> str | None:
        if isinstance(value, str) and "\x00" in value:
            return value.replace("\x00", "")
        return value
