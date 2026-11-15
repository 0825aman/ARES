"""Claim schemas — Phase 4 M4.4."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator


class ClaimVerificationResponse(BaseModel):
    id: str
    claim_id: str
    run_id: str
    verification_status: str
    supporting_evidence_ids: list[str] = []
    contradicting_evidence_ids: list[str] = []
    reasoning_summary: str | None = None
    evidence_limitations: str | None = None
    confidence: float
    verified_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @field_validator("supporting_evidence_ids", "contradicting_evidence_ids", mode="before")
    @classmethod
    def _parse_json_list(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return [str(x) for x in parsed] if isinstance(parsed, list) else []
            except (json.JSONDecodeError, ValueError):
                return []
        return []

    @field_serializer("verified_at")
    def serialize_dt(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")


class ClaimResponse(BaseModel):
    id: str
    run_id: str
    report_id: str | None = None
    claim_text: str
    claim_type: str
    originating_section: str
    is_high_impact: bool
    created_at: datetime
    verification: ClaimVerificationResponse | None = None
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")


class VerificationSummary(BaseModel):
    total_claims: int
    supported: int
    partially_supported: int
    contradicted: int
    insufficient_evidence: int
    unverified: int
    not_applicable: int
    claim_ids: list[str] = []


class ClaimListResponse(BaseModel):
    items: list[ClaimResponse]
    total: int
    run_id: str
    verification_summary: VerificationSummary | None = None
