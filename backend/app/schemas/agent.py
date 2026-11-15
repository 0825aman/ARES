"""Pydantic schemas for agent coordination — Supervisor output and activity log.

SupervisorDecision is what the Supervisor LLM must produce.
AgentEventResponse / AgentActivityResponse are returned by the
GET /runs/{id}/activity API endpoint.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── Agent-facing (LLM output) schemas ─────────────────────────────────────────

class SupervisorDecision(BaseModel):
    """Structured output produced by the Supervisor Agent LLM call."""

    decision: Literal[
        "request_plan",
        "revise_plan",
        "execute_next_task",
        "continue_research",
        "complete_research",
        "fail_workflow",
        # ── Phase 4 M4.5: Critic routing decisions ──────────────────────────
        "approve_report",
        "request_additional_research",
        "request_reverification",
        "revise_report",
        "reject",
        "mark_needs_attention",
    ] = Field(description="Next workflow action")
    reasoning: str = Field(
        max_length=300,
        description="Brief explanation of the decision (max 300 chars)",
    )
    revision_notes: str | None = Field(
        default=None,
        description="Required when decision == 'revise_plan'",
    )
    next_task_id: str | None = Field(
        default=None,
        description="Required when decision == 'execute_next_task'",
    )


class TaskResult(BaseModel):
    """Result produced by the Research Agent after executing one task."""

    task_id: str
    status: Literal["completed", "partial", "failed", "fatal_error"]
    findings: str = Field(description="2-3 sentence LLM-generated finding summary")
    evidence_ids: list[str] = Field(description="EvidenceRecord.id values persisted to DB")
    evidence_count: int
    unanswered_questions: list[str] = Field(default_factory=list)
    limitations: str | None = None
    error: str | None = None


# ── API response schemas ───────────────────────────────────────────────────────

class AgentEventResponse(BaseModel):
    """API response shape for a single AgentExecutionEvent ORM row."""

    id: str
    agent_name: str
    event_type: str
    summary: str
    input_ref: str | None
    output_ref: str | None
    iteration: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentActivityResponse(BaseModel):
    """API response wrapping the full event timeline for a run."""

    run_id: str
    events: list[AgentEventResponse]
    total: int
