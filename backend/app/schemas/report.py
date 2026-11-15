from __future__ import annotations
import json
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, field_serializer, model_validator


class ReportResponse(BaseModel):
    id: str
    run_id: str
    research_question: str
    executive_summary: str
    key_findings: list[str]
    evidence_used: list[dict]
    observations: str | None
    contradictions: str | None
    limitations: str
    sources: list[dict]
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("generated_at")
    def serialize_dt(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")

    @model_validator(mode="before")
    @classmethod
    def parse_json_fields(cls, data):
        """Parse JSON TEXT fields from ORM into Python lists/dicts."""
        if hasattr(data, "__dict__"):
            # ORM object — convert to dict first
            obj_dict = {c.key: getattr(data, c.key) for c in data.__table__.columns}
        else:
            obj_dict = dict(data)

        for field_name in ("key_findings", "evidence_used", "sources"):
            val = obj_dict.get(field_name)
            if isinstance(val, str):
                try:
                    obj_dict[field_name] = json.loads(val)
                except json.JSONDecodeError:
                    obj_dict[field_name] = []
        return obj_dict
