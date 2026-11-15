import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.plan import ResearchPlan
    from app.models.task import ResearchTask
    from app.models.event import AgentExecutionEvent
    from app.models.source import Source

from app.models.base import Base


class ResearchRun(Base):
    __tablename__ = "research_runs"
    __table_args__ = (
        # Composite index for dashboard queries: WHERE project_id = ? AND status = ?
        Index("idx_runs_project_status", "project_id", "status"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("research_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    research_question: Mapped[str] = mapped_column(Text, nullable=False)
    use_web: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    use_documents: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    current_stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    # Phase 3: distinguishes sequential (Phase 2) from multi_agent (Phase 3) runs
    workflow_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="sequential", index=True
    )
    # Phase 4 M4.4: verification depth for claim verification
    verification_depth: Mapped[str] = mapped_column(
        String(20), nullable=False, default="basic"
    )
    # Phase 4 M4.7: LLM usage tracking (observability only — never gates features)
    llm_call_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Relationships
    project: Mapped["ResearchProject"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ResearchProject", back_populates="runs"
    )
    documents: Mapped[list["UploadedDocument"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "UploadedDocument", back_populates="run", cascade="all, delete"
    )
    evidence: Mapped[list["EvidenceRecord"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "EvidenceRecord", back_populates="run", cascade="all, delete-orphan"
    )
    report: Mapped["ResearchReport | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ResearchReport", back_populates="run", cascade="all, delete-orphan", uselist=False
    )
    # Phase 3 relationships
    plans: Mapped[list["ResearchPlan"]] = relationship(
        "ResearchPlan", back_populates="run", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["ResearchTask"]] = relationship(
        "ResearchTask", back_populates="run", cascade="all, delete-orphan"
    )
    events: Mapped[list["AgentExecutionEvent"]] = relationship(
        "AgentExecutionEvent", back_populates="run", cascade="all, delete-orphan"
    )
    # Phase 4 M4.2 relationship
    sources: Mapped[list["Source"]] = relationship(
        "Source", back_populates="run", cascade="all, delete-orphan"
    )
    # Phase 5 M5.5 relationship
    approval_requests: Mapped[list["ApprovalRequest"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ApprovalRequest", back_populates="run", cascade="all, delete-orphan"
    )
    # Phase 5 M5.6 relationship
    export_records: Mapped[list["ExportRecord"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ExportRecord", back_populates="run", cascade="all, delete-orphan"
    )
