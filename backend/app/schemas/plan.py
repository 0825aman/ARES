"""Pydantic schemas for research plan data — used by both the Planning Agent
and the API response layer.

ORM ↔ schema mapping:
  ResearchPlan ORM  ←→  ResearchPlanResponse
  ResearchTask ORM  ←→  ResearchTaskResponse

The agent-facing models (ResearchTask, ResearchPlan) are what the LLM must
produce; the *Response variants are what the API returns to clients.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ── Agent-facing (LLM output) schemas ─────────────────────────────────────────

class ResearchTask(BaseModel):
    """A single independently-searchable research task produced by the Planner."""

    task_id: str = Field(description="UUID string — stable identifier for this task")
    objective: str = Field(description="What to investigate in this task")
    search_query: str = Field(description="Optimised web search query string")
    expected_evidence_type: str = Field(
        description="E.g. 'academic papers', 'news articles', 'statistics'"
    )
    priority: int = Field(ge=1, le=3, description="1=highest, 3=lowest")


class ResearchPlan(BaseModel):
    """Structured research plan produced by the Planning Agent."""

    plan_id: str = Field(description="UUID string for this plan")
    objectives: list[str] = Field(
        min_length=1,
        description="3-6 high-level research objectives",
    )
    tasks: list[ResearchTask] = Field(
        min_length=2,
        max_length=8,
        description="2-8 research tasks sorted by priority",
    )
    refinement_notes: str | None = Field(
        default=None,
        description="Populated when this is a refined plan",
    )

    @field_validator("tasks")
    @classmethod
    def tasks_count_in_bounds(cls, v: list[ResearchTask]) -> list[ResearchTask]:
        if not 2 <= len(v) <= 8:
            raise ValueError(f"Task count must be 2-8, got {len(v)}")
        return v


# ── API response schemas ───────────────────────────────────────────────────────

class ResearchTaskResponse(BaseModel):
    """API response shape for a single ResearchTask ORM row."""

    id: str
    objective: str
    search_query: str
    expected_evidence_type: str | None
    priority: int
    status: str
    findings: str | None
    evidence_count: int
    unanswered_questions: list[str]
    limitations: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResearchPlanResponse(BaseModel):
    """API response shape for a ResearchPlan ORM row (with nested tasks)."""

    id: str
    run_id: str
    objectives: list[str]
    tasks: list[ResearchTaskResponse]
    plan_version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
