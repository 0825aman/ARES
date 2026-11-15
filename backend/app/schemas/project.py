from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator


class ProjectStatus(str, Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"
    archived = "archived"


class ProjectCategory(str, Enum):
    technology = "Technology"
    science = "Science"
    business = "Business"
    health_medicine = "Health & Medicine"
    society_culture = "Society & Culture"
    environment = "Environment"
    economics = "Economics"
    history = "History"
    law_policy = "Law & Policy"
    other = "Other"


def _serialize_dt(dt: datetime) -> str:
    """Serialize a datetime to ISO 8601 with Z suffix.
    SQLite may return naive datetimes; treat them as UTC.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ProjectCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    research_question: str = Field(..., min_length=1, max_length=1000)
    description: str | None = Field(None, max_length=2000)
    category: ProjectCategory | None = Field(None)

    @field_validator("title", "research_question", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


class ProjectUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    research_question: str | None = Field(default=None, min_length=1, max_length=1000)
    description: str | None = Field(default=None, max_length=2000)
    category: ProjectCategory | None = Field(default=None)
    status: ProjectStatus | None = Field(default=None)

    @field_validator("title", "research_question", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if isinstance(v, str) else v

    @model_validator(mode="after")
    def required_fields_cannot_be_null(self) -> "ProjectUpdateRequest":
        for field_name in ("title", "research_question"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} is required and cannot be set to null.")
        return self


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ProjectResponse(BaseModel):
    id: UUID
    title: str
    research_question: str
    description: str | None
    category: ProjectCategory | None
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("category", mode="before")
    @classmethod
    def sanitize_category(cls, v: object) -> ProjectCategory | None:
        if not v:
            return None
        if isinstance(v, ProjectCategory):
            return v
        try:
            return ProjectCategory(v)
        except ValueError:
            return ProjectCategory.other

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime) -> str:
        return _serialize_dt(dt)


class ProjectBriefResponse(BaseModel):
    id: UUID
    title: str
    category: ProjectCategory | None
    status: ProjectStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("category", mode="before")
    @classmethod
    def sanitize_category(cls, v: object) -> ProjectCategory | None:
        if not v:
            return None
        if isinstance(v, ProjectCategory):
            return v
        try:
            return ProjectCategory(v)
        except ValueError:
            return ProjectCategory.other

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime) -> str:
        return _serialize_dt(dt)


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    limit: int
    offset: int


class ProjectSummaryResponse(BaseModel):
    total: int
    by_status: dict[ProjectStatus, int]
    recent_projects: list[ProjectBriefResponse]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str
    environment: str
    database: Literal["ok", "error"]
