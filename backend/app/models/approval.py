"""ApprovalRequest ORM model — Phase 5 M5.5.

Represents a human approval checkpoint during graph execution.
Created when the LangGraph workflow hits an interrupt_before node.
Resolved when the user submits an approve/reject/revise decision.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("research_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # e.g. "plan_approval" | "critic_needs_attention"
    checkpoint_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # e.g. "planning_complete_node" | "critic_review_approval_node"
    node_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # JSON-serialised snapshot of relevant graph state at checkpoint time
    context_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    # "pending" | "approved" | "rejected" | "revision_requested" | "expired"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # Set when the user submits a decision
    decision: Mapped[str | None] = mapped_column(String(30), nullable=True)
    decision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationship back to the run
    run: Mapped["ResearchRun"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ResearchRun", back_populates="approval_requests"
    )
