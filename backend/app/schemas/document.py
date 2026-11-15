from __future__ import annotations
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, field_serializer


class DocumentResponse(BaseModel):
    id: str
    run_id: str | None
    project_id: str
    original_filename: str
    file_size_bytes: int
    mime_type: str
    extraction_status: str
    uploaded_at: datetime
    # Phase 4 M4.1 fields
    chunk_count: int = 0
    has_images: bool = False
    ocr_attempted: bool = False
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("uploaded_at")
    def serialize_dt(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int


class DocumentUploadResult(BaseModel):
    uploaded: list[DocumentResponse]
    rejected: list[dict]  # {"filename": str, "reason": str}


class RejectedFile(BaseModel):
    filename: str
    reason: str


# ── Phase 4 M4.1 ─────────────────────────────────────────────────────────────

class DocumentChunkResponse(BaseModel):
    """Response schema for a single DocumentChunk."""
    id: str
    document_id: str
    chunk_index: int
    text: str
    page_start: int | None
    page_end: int | None
    section_title: str | None
    heading_level: int | None
    extraction_method: str | None
    char_count: int
    has_tables: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")


class DocumentChunkListResponse(BaseModel):
    items: list[DocumentChunkResponse]
    total: int
    document_id: str
