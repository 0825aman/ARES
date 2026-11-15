"""Pydantic schemas for Citation management — Phase 4 M4.6."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CitationResponse(BaseModel):
    """API response shape for a single Citation ORM row."""

    id: str
    run_id: str
    report_id: str
    claim_id: str | None
    evidence_id: str
    source_id: str | None
    citation_key: str
    page_reference: str | None
    section_reference: str | None
    url: str | None
    doi: str | None
    apa_formatted: str | None
    ieee_formatted: str | None
    is_verified: bool
    validation_notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BibliographyResponse(BaseModel):
    """API response for the full bibliography of a run."""

    run_id: str
    report_id: str | None
    total: int
    verified_count: int
    citations: list[CitationResponse]
