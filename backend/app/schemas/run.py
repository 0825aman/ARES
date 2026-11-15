from __future__ import annotations
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

class RunStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ALL = [PENDING, RUNNING, COMPLETED, FAILED]

class StartRunRequest(BaseModel):
    research_question: str = Field(..., min_length=1, max_length=1000)
    use_web: bool = True
    use_documents: bool = False
    document_ids: list[str] = Field(default_factory=list)
    workflow_mode: str = Field(
        default="sequential",
        description="'sequential' (Phase 2 default) or 'multi_agent' (Phase 3)",
    )
    # Phase 4 M4.4: verification depth — "basic" (default) or "thorough"
    verification_depth: str = Field(
        default="basic",
        description="'basic' (key findings + high-impact claims) or 'thorough' (full report)",
    )

    @field_validator("research_question", mode="before")
    @classmethod
    def strip_whitespace(cls, v):
        return v.strip() if isinstance(v, str) else v

def _serialize_dt(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")

class RunResponse(BaseModel):
    id: str
    project_id: str
    research_question: str
    use_web: bool
    use_documents: bool
    workflow_mode: str
    # Phase 4 M4.4
    verification_depth: str = "basic"
    # Phase 4 M4.7 — LLM usage tracking (observability)
    llm_call_count: int = 0
    total_tokens_used: int = 0
    estimated_cost_usd: float = 0.0
    status: str
    current_stage: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("started_at", "completed_at", "created_at")
    def serialize_dt(self, dt: datetime | None) -> str | None:
        return _serialize_dt(dt)

class RunListResponse(BaseModel):
    items: list[RunResponse]
    total: int
    limit: int
    offset: int
