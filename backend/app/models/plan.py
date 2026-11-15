import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ResearchPlan(Base):
    """Stores the structured research plan produced by the Planning Agent.

    One plan per run per version — a re-planned run increments plan_version.
    The latest plan_version is the active plan.
    """

    __tablename__ = "research_plans"
    __table_args__ = (
        UniqueConstraint("run_id", "plan_version", name="uq_research_plans_run_version"),
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
    # JSON TEXT array of high-level objective strings (SQLite compatible)
    objectives: Mapped[str] = mapped_column(Text, nullable=False)
    refinement_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    run: Mapped["ResearchRun"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ResearchRun", back_populates="plans"
    )
    tasks: Mapped[list["ResearchTask"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ResearchTask", back_populates="plan", cascade="all, delete-orphan"
    )
