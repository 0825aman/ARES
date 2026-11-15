"""Source schemas — Phase 4 M4.2."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator


class SourceResponse(BaseModel):
    """API response for a single Source record."""
    id: str
    run_id: str
    source_type: str
    title: str | None
    url: str | None
    doi: str | None
    authors: list[str] | None = None  # deserialized from JSON TEXT
    publisher: str | None = None
    venue: str | None = None
    publication_date: str | None = None
    is_peer_reviewed: bool
    retrieval_provider: str
    retrieved_at: datetime
    is_accessible: bool
    credibility_notes: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @field_validator("authors", mode="before")
    @classmethod
    def _parse_authors(cls, v: Any) -> list[str] | None:
        """Convert authors JSON TEXT → list[str]."""
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(a) for a in parsed]
            except (json.JSONDecodeError, ValueError):
                return None
        return None

    @field_serializer("retrieved_at", "created_at")
    def serialize_dt(self, dt: datetime) -> str:
        if dt is None:
            return ""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")


class SourceListResponse(BaseModel):
    items: list[SourceResponse]
    total: int
    run_id: str
