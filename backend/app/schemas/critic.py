"""Pydantic schemas for Critic Agent — Phase 4 M4.5.

CriticReviewResponse is the API response shape for a CriticReview ORM row.
CriticDecision is the structured output the Critic LLM must produce.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ── LLM output schema ──────────────────────────────────────────────────────────

class CriticDecision(BaseModel):
    """Structured output produced by the Critic Agent LLM call.

    This is what the LLM must return verbatim.  All issue lists contain
    plain-text descriptions, NOT UUIDs — the Critic is not expected to know
    internal IDs.
    """

    overall_assessment: Literal["strong", "adequate", "weak", "inadequate"] = Field(
        description="Holistic quality assessment of the research report"
    )
    recommended_action: Literal[
        "approve_report",
        "request_additional_research",
        "request_reverification",
        "revise_report",
        "reject",
    ] = Field(description="Recommended next action for the Supervisor")
    unsupported_claims: list[str] = Field(
        default_factory=list,
        description="Claims that lack supporting evidence",
    )
    citation_issues: list[str] = Field(
        default_factory=list,
        description="Citation problems (missing source, broken link, etc.)",
    )
    contradictory_findings: list[str] = Field(
        default_factory=list,
        description="Findings that contradict each other or the evidence",
    )
    missing_evidence: list[str] = Field(
        default_factory=list,
        description="Important research areas that lack evidence coverage",
    )
    source_quality_issues: list[str] = Field(
        default_factory=list,
        description="Source credibility or peer-review concerns",
    )
    reasoning_issues: list[str] = Field(
        default_factory=list,
        description="Logical or inferential errors in the report",
    )
    review_summary: str = Field(
        description="Narrative summary of the review (max 500 characters)",
        default="",
    )

    @field_validator("review_summary", mode="before")
    @classmethod
    def _truncate_summary(cls, v: str) -> str:
        if isinstance(v, str) and len(v) > 500:
            return v[:497] + "..."
        return v or ""


# ── API response schema ────────────────────────────────────────────────────────

class CriticReviewResponse(BaseModel):
    """API response shape for a CriticReview ORM row."""

    id: str
    run_id: str
    review_version: int
    overall_assessment: str
    review_status: str
    recommended_action: str
    unsupported_claims: list[str]
    citation_issues: list[str]
    contradictory_findings: list[str]
    missing_evidence: list[str]
    source_quality_issues: list[str]
    reasoning_issues: list[str]
    review_summary: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
