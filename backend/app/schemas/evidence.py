"""Evidence schemas — Phase 4 M4.3."""
from __future__ import annotations

from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, field_serializer


class EvidenceResponse(BaseModel):
    """API response for a single EvidenceRecord."""
    id: str
    run_id: str
    source_type: str
    source_label: str
    content: str | None = None
    relevance_score: float
    fetch_status: str
    url: str | None = None
    page_title: str | None = None
    retrieved_at: datetime | None = None
    document_id: str | None = None
    chunk_index: int | None = None
    page_number: int | None = None
    task_id: str | None = None
    # Phase 4 M4.3 fields
    source_id: str | None = None
    chunk_id: str | None = None
    evidence_type: str = "other"
    evidence_relationship: str = "neutral"
    section_name: str | None = None
    extraction_method: str | None = None
    extraction_confidence: float | None = None
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("retrieved_at")
    def serialize_retrieved_at(self, dt: datetime | None) -> str | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")


class EvidenceListResponse(BaseModel):
    items: list[EvidenceResponse]
    total: int
    run_id: str
