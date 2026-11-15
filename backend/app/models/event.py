import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional

from app.models.base import Base


class AgentExecutionEvent(Base):
    """Immutable audit log of significant agent actions.

    New rows are only ever inserted, never updated or deleted.
    This is the primary observability record for the multi-agent workflow.
    The frontend reads these via GET /runs/{id}/activity.
    """

    __tablename__ = "agent_execution_events"
    __table_args__ = (
        # Composite index for activity-feed queries: WHERE run_id = ? ORDER BY created_at
        Index("idx_events_run_created", "run_id", "created_at"),
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
    # "supervisor" | "planner" | "researcher" | "system"
    agent_name: Mapped[str] = mapped_column(String(50), nullable=False)
    # see event_type values in doc 25 section 2.3
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # human-readable one-line description
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    # e.g. "task_id:abc123" or "plan_id:xyz"
    input_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # e.g. "decision:execute_next_task" or "evidence_ids:3"
    output_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # supervisor iteration count at the time of this event
    iteration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Phase 5 M5.1: per-run sequence number for SSE Last-Event-ID replay
    sequence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Relationships
    run: Mapped["ResearchRun"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ResearchRun", back_populates="events"
    )
