import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ResearchTask(Base):
    """Stores an individual research task within a ResearchPlan.

    Each task is executed by the Research Agent. Status tracks the lifecycle:
    pending → running → completed | partial | failed
    """

    __tablename__ = "research_tasks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    plan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("research_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Denormalised FK to run — simplifies queries without requiring plan join
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("research_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    search_query: Mapped[str] = mapped_column(Text, nullable=False)
    expected_evidence_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    # pending | running | completed | partial | failed
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    # LLM-generated 2-3 sentence finding summary (set after task completes)
    findings: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # JSON TEXT array of unanswered questions (SQLite compatible)
    unanswered_questions: Mapped[str | None] = mapped_column(Text, nullable=True)
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    plan: Mapped["ResearchPlan"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ResearchPlan", back_populates="tasks"
    )
    run: Mapped["ResearchRun"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ResearchRun", back_populates="tasks"
    )
    evidence_records: Mapped[list["EvidenceRecord"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "EvidenceRecord", back_populates="task"
    )
