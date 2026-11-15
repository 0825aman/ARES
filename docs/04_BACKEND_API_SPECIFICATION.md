# 04 — Backend API Specification

## Multi-Agent Autonomous Researcher (MAAR)
### Phase 1: Application Foundation

---

## 1. General Conventions

### 1.1 Base URL

| Environment | Base URL |
|---|---|
| Local development | `http://localhost:8000` |
| API version prefix | `/api/v1` |

All project endpoints are prefixed with `/api/v1`.

### 1.2 Content Type

All requests and responses use `Content-Type: application/json`.

### 1.3 Versioning

All endpoints are versioned under `/api/v1/`. This allows introducing `/api/v2/` for breaking changes without disrupting Phase 1 consumers.

### 1.4 HTTP Status Codes

| Code | Meaning | When used |
|---|---|---|
| 200 OK | Success | Successful GET or PATCH |
| 201 Created | Resource created | Successful POST |
| 204 No Content | Success, no body | Successful DELETE |
| 404 Not Found | Resource missing | Resource UUID does not exist |
| 422 Unprocessable Entity | Validation failure | Invalid field values, invalid enum values, malformed UUID, missing required fields |
| 500 Internal Server Error | Unexpected error | Unhandled server error or database failure |

**HTTP 400 is not used.** All input validation failures — including invalid enum values for `category` and `status` — return HTTP 422. HTTP 400 was previously planned for category validation but is inconsistent with how FastAPI and Pydantic communicate field errors to clients. Using 422 throughout allows clients to apply a single error-handling path for all validation problems.

### 1.5 Error Response Format

All error responses use a consistent structure:

```json
{
  "detail": "Human-readable error message"
}
```

FastAPI/Pydantic validation errors (422) use an array form:

```json
{
  "detail": [
    {
      "loc": ["body", "category"],
      "msg": "Input should be 'Technology', 'Science', 'Business', 'Health & Medicine', 'Society & Culture', 'Environment', 'Economics', 'History', 'Law & Policy' or 'Other'",
      "type": "enum"
    }
  ]
}
```

Both forms are produced by FastAPI automatically when using Pydantic models and Python Enums as field types.

---

## 2. Shared Type Definitions

### 2.1 `ProjectStatus` Enum

Defined once in `app/schemas/project.py`. All route handlers, service methods, and response schemas import from this single location.

```python
class ProjectStatus(str, Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed   = "completed"
    archived    = "archived"
```

Default on creation: `not_started`.

### 2.2 `ProjectCategory` Enum

Defined once in `app/schemas/project.py`. Replaces the plain string + `VALID_CATEGORIES` list from the original design. Using an enum means Pydantic validates category values automatically and returns a 422 with a descriptive message — no custom service-layer validation needed.

```python
class ProjectCategory(str, Enum):
    technology       = "Technology"
    science          = "Science"
    business         = "Business"
    health_medicine  = "Health & Medicine"
    society_culture  = "Society & Culture"
    environment      = "Environment"
    economics        = "Economics"
    history          = "History"
    law_policy       = "Law & Policy"
    other            = "Other"
```

A `null` category is always valid (the field is optional). An unrecognised string returns HTTP 422.

### 2.3 Frontend Synchronization

The frontend must not maintain a separate hardcoded category list that can drift from the backend. Two strategies are available; **Strategy A** is used in Phase 1:

**Strategy A — Shared constants file (Phase 1)**  
`frontend/src/lib/constants/categories.ts` exports the category strings. This file is the single source of truth for the frontend. When backend categories change, only this file needs updating. The values must match `ProjectCategory` enum values exactly.

```typescript
// frontend/src/lib/constants/categories.ts
export const PROJECT_CATEGORIES = [
  "Technology",
  "Science",
  "Business",
  "Health & Medicine",
  "Society & Culture",
  "Environment",
  "Economics",
  "History",
  "Law & Policy",
  "Other",
] as const;

export type ProjectCategoryValue = typeof PROJECT_CATEGORIES[number];
```

**Strategy B — API-served categories (Phase 2 option)**  
A `GET /api/v1/meta/categories` endpoint returns the enum values at runtime, eliminating the need to keep the frontend file in sync manually. Deferred to Phase 2.

### 2.4 Timestamp Convention

All timestamps are timezone-aware UTC values throughout the system.

- **Storage**: `DATETIME` column in SQLite; Python `datetime.now(timezone.utc)` for all assignments.
- **Serialization**: ISO 8601 with explicit UTC offset `Z` suffix, e.g. `"2025-01-15T14:30:00Z"`.
- **Pydantic config**: `json_encoders` or `model_config` with `json_serialization='iso8601'` ensures consistent output.
- **`created_at`**: Set once at INSERT. Never mutated by any update operation.
- **`updated_at`**: Set at INSERT and updated by every PATCH. Always reflects the last modification time.

Pydantic response model configuration to enforce serialization:

```python
class ProjectResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda dt: dt.isoformat().replace("+00:00", "Z")}
    )
```

---

## 3. Endpoints

### 3.1 Health Check

**`GET /health`**

Returns the operational status of the API, including a database connectivity check.

**Request**: No body, no parameters.

**Response: 200 OK — healthy**

```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "development",
  "database": "ok"
}
```

**Response: 200 OK — database unreachable**

```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "development",
  "database": "error"
}
```

The health endpoint always returns HTTP 200. The `database` field communicates database readiness separately. This allows load balancers and the frontend to distinguish "API is running" from "API + DB are both healthy" without treating a DB issue as an HTTP failure at the health check level.

The database check executes a lightweight query — `SELECT 1` — within a try/except block. If the query fails, `database` is set to `"error"` and the exception is logged.

**Response Schema**

```python
class HealthResponse(BaseModel):
    status: Literal["ok"]  # Always "ok" — HTTP 200 means the process is alive
    version: str           # Application version string
    environment: str       # From APP_ENV environment variable
    database: Literal["ok", "error"]  # Result of the DB connectivity probe
```

---

### 3.2 Create Research Project

**`POST /api/v1/projects`**

Creates a new research project and persists it to the database.

**Request Body**

```json
{
  "title": "Impact of Large Language Models on Scientific Research",
  "research_question": "How are LLMs changing the speed and quality of scientific literature review?",
  "description": "An investigation into the adoption of AI tools in academic research workflows.",
  "category": "Technology"
}
```

**Request Schema**

```python
class ProjectCreateRequest(BaseModel):
    title: str                       = Field(..., min_length=1, max_length=200)
    research_question: str           = Field(..., min_length=1, max_length=1000)
    description: str | None          = Field(None, max_length=2000)
    category: ProjectCategory | None = Field(None)

    @field_validator("title", "research_question", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v
```

**Validation Rules**

| Field | Rule | Error code |
|---|---|---|
| `title` | Required. 1–200 characters after whitespace strip. | 422 |
| `research_question` | Required. 1–1000 characters after whitespace strip. | 422 |
| `description` | Optional. Max 2000 characters if provided. | 422 |
| `category` | Optional. Must be a valid `ProjectCategory` enum value or `null`. | 422 |

**Response: 201 Created**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Impact of Large Language Models on Scientific Research",
  "research_question": "How are LLMs changing the speed and quality of scientific literature review?",
  "description": "An investigation into the adoption of AI tools in academic research workflows.",
  "category": "Technology",
  "status": "not_started",
  "created_at": "2025-01-15T14:30:00Z",
  "updated_at": "2025-01-15T14:30:00Z"
}
```

**Error Responses**

| Code | Condition | `detail` form |
|---|---|---|
| 422 | Missing required field | Pydantic array, `type: "missing"` |
| 422 | Title or question too long | Pydantic array, `type: "string_too_long"` |
| 422 | Title or question is blank whitespace | Pydantic array after strip, `type: "string_too_short"` |
| 422 | `category` is not a known enum value | Pydantic array, `type: "enum"`, lists valid values |

---

### 3.3 List All Research Projects

**`GET /api/v1/projects`**

Returns research projects ordered by creation date descending (newest first), with optional pagination and status filtering.

**Query Parameters**

| Parameter | Type | Default | Constraints | Description |
|---|---|---|---|---|
| `limit` | int | 100 | 1–500 | Maximum results to return |
| `offset` | int | 0 | ≥ 0 | Number of records to skip |
| `status` | ProjectStatus | none | valid enum value | Filter by status |

Invalid `status` values return HTTP 422. Invalid `limit`/`offset` values (negative, non-integer, over max) return HTTP 422 via Pydantic query parameter validation.

**Response: 200 OK**

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Impact of Large Language Models on Scientific Research",
      "research_question": "How are LLMs changing the speed and quality of scientific literature review?",
      "description": "An investigation into the adoption of AI tools in academic research workflows.",
      "category": "Technology",
      "status": "not_started",
      "created_at": "2025-01-15T14:30:00Z",
      "updated_at": "2025-01-15T14:30:00Z"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

`total` reflects the count of records matching the applied filter, not the page size.

**Response Schema**

```python
class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int   # Count matching the filter (pre-pagination)
    limit: int   # Applied limit
    offset: int  # Applied offset
```

**Error Responses**

| Code | Condition |
|---|---|
| 422 | `status` query parameter is not a valid `ProjectStatus` value |
| 422 | `limit` is not an integer, is less than 1, or exceeds 500 |
| 422 | `offset` is not an integer or is negative |

---

### 3.4 Get Research Project by ID

**`GET /api/v1/projects/{project_id}`**

Returns a single research project by its UUID.

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `project_id` | UUID string | The project's UUID |

**Response: 200 OK** — returns the full `ProjectResponse` object.

**Error Responses**

| Code | Condition | `detail` |
|---|---|---|
| 404 | Project UUID not found | `"Project not found."` |
| 422 | `project_id` is not a valid UUID format | Pydantic validation array |

---

### 3.5 Update Research Project

**`PATCH /api/v1/projects/{project_id}`**

Partially updates a research project. Only fields explicitly provided in the request body are updated. The service layer uses `model.model_dump(exclude_unset=True)` to obtain exactly the set of fields the client sent, then applies only those fields.

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `project_id` | UUID string | The project's UUID |

#### Omitted vs. Explicit Null

This distinction is critical for optional fields:

| Body sent | Field behaviour |
|---|---|
| Field is absent from the body entirely | Field is **unchanged** in the database |
| Field is present and set to a non-null value | Field is **updated** to the new value |
| Optional field is present and set to `null` | Field is **cleared** to `null` in the database |
| Required field (`title`, `research_question`) is present and set to `null` | Returns HTTP 422 — required fields cannot be nulled |

This is implemented by the service using `exclude_unset=True` on the Pydantic model, then iterating only the included keys:

```python
# Service layer pattern — not implementation code
update_data = payload.model_dump(exclude_unset=True)
for key, value in update_data.items():
    setattr(db_project, key, value)
db_project.updated_at = datetime.now(timezone.utc)
```

**Example: clear an optional field**

```json
{ "description": null }
```
→ `description` is set to `null` in the database.

**Example: omit a field**

```json
{ "status": "in_progress" }
```
→ Only `status` changes. All other fields, including `description`, are untouched.

**Request Schema**

```python
class ProjectUpdateRequest(BaseModel):
    title: str | None                = Field(default=None, min_length=1, max_length=200)
    research_question: str | None    = Field(default=None, min_length=1, max_length=1000)
    description: str | None          = Field(default=None, max_length=2000)
    category: ProjectCategory | None = Field(default=None)
    status: ProjectStatus | None     = Field(default=None)

    @field_validator("title", "research_question", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if isinstance(v, str) else v

    @model_validator(mode="after")
    def required_fields_cannot_be_null(self) -> "ProjectUpdateRequest":
        # If title or research_question were explicitly provided as null,
        # they will be None here — reject them.
        # Note: if they were simply absent, model_dump(exclude_unset=True)
        # will not include them, so this validator only fires when explicitly sent.
        for field_name in ("title", "research_question"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} is required and cannot be set to null.")
        return self
```

**Request Body Examples**

Status only:
```json
{ "status": "in_progress" }
```

Multiple fields:
```json
{
  "title": "Updated Title",
  "status": "in_progress",
  "description": "Updated description."
}
```

Clear optional field:
```json
{ "description": null }
```

No-op (empty body):
```json
{}
```
→ Returns HTTP 200 with the unmodified project. `updated_at` is **not** changed for empty-body PATCHes.

**Response: 200 OK**

Returns the complete updated `ProjectResponse` object.

**Error Responses**

| Code | Condition | `detail` |
|---|---|---|
| 404 | Project UUID not found | `"Project not found."` |
| 422 | Invalid `status` value | Pydantic array, `type: "enum"` |
| 422 | Invalid `category` value | Pydantic array, `type: "enum"` |
| 422 | `title` or `research_question` explicitly set to `null` | Pydantic array, `type: "value_error"` |
| 422 | `title` or `research_question` too long | Pydantic array, `type: "string_too_long"` |

---

### 3.6 Delete Research Project

**`DELETE /api/v1/projects/{project_id}`**

Permanently and irreversibly deletes a research project from the database.

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `project_id` | UUID string | The project's UUID |

**Request**: No body.

**Response: 204 No Content**

Empty body. The project no longer exists in the database.

**Error Responses**

| Code | Condition | `detail` |
|---|---|---|
| 404 | Project UUID not found | `"Project not found."` |
| 422 | `project_id` is not a valid UUID format | Pydantic validation array |

#### Frontend Confirmation Requirement

The frontend **must** present a confirmation dialog before calling this endpoint. The dialog must:

- State the project title explicitly: "Delete **{title}**?"
- Warn that the action is permanent: "This action cannot be undone."
- Provide a destructive-styled confirm button ("Delete") and a cancel button.
- Only call `DELETE /api/v1/projects/{id}` after the user explicitly confirms.
- On success (204): redirect to `/projects` and show a toast: "Project deleted."
- On 404 (already deleted or stale ID): show a toast: "Project not found." and redirect to `/projects`.

The confirmation dialog is implemented using shadcn/ui `AlertDialog`, not a basic `window.confirm`.

---

## 4. Dashboard Summary Endpoint

**`GET /api/v1/projects/summary`**

Returns aggregate statistics computed from live database records. This endpoint performs real database queries — no hardcoded or mocked values are ever returned.

**Important**: This route must be registered **before** `GET /api/v1/projects/{project_id}` to prevent the literal string `"summary"` being matched as a UUID.

**Request**: No body, no parameters.

**Database queries performed**:
1. `COUNT(*)` across all projects → `total`.
2. `COUNT(*) GROUP BY status` → `by_status` map. All `ProjectStatus` values are always present in the response; statuses with zero matching records are included as `0`.
3. `SELECT ... ORDER BY created_at DESC LIMIT 5` → `recent_projects`.

**Response: 200 OK**

```json
{
  "total": 12,
  "by_status": {
    "not_started": 1,
    "in_progress": 4,
    "completed": 7,
    "archived": 0
  },
  "recent_projects": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Impact of Large Language Models on Scientific Research",
      "category": "Technology",
      "status": "not_started",
      "created_at": "2025-01-15T14:30:00Z"
    }
  ]
}
```

When the database contains no projects:
```json
{
  "total": 0,
  "by_status": {
    "not_started": 0,
    "in_progress": 0,
    "completed": 0,
    "archived": 0
  },
  "recent_projects": []
}
```

**Response Schema**

```python
class ProjectBriefResponse(BaseModel):
    id: UUID
    title: str
    category: ProjectCategory | None
    status: ProjectStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ProjectSummaryResponse(BaseModel):
    total: int
    by_status: dict[ProjectStatus, int]   # All 4 statuses always present
    recent_projects: list[ProjectBriefResponse]  # Up to 5, newest first
```

---

## 5. Project Response Schema (Shared)

All endpoints that return a full project use the same `ProjectResponse`:

```python
class ProjectResponse(BaseModel):
    id: UUID
    title: str
    research_question: str
    description: str | None
    category: ProjectCategory | None
    status: ProjectStatus
    created_at: datetime   # UTC, serialized as ISO 8601 with Z suffix
    updated_at: datetime   # UTC, serialized as ISO 8601 with Z suffix

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda dt: dt.isoformat().replace("+00:00", "Z")}
    )
```

---

## 6. CORS Configuration

```python
allowed_origins = ["http://localhost:3000"]  # Overridable via ALLOWED_ORIGINS env var
allow_credentials = True
allow_methods = ["GET", "POST", "PATCH", "DELETE", "OPTIONS"]
allow_headers = ["Content-Type", "Authorization"]
```

---

## 7. API Route Registration Order

Routes within the projects router must be registered in this exact order to prevent path conflicts:

1. `GET /projects/summary` — static path; must precede dynamic `{project_id}` routes
2. `GET /projects` — list all
3. `POST /projects` — create
4. `GET /projects/{project_id}` — get by ID
5. `PATCH /projects/{project_id}` — update
6. `DELETE /projects/{project_id}` — delete

---

## 8. Complete Endpoint Reference

| Method | Path | Description |
|---|---|---|
| GET | `/health` | API health check + database probe |
| GET | `/api/v1/projects/summary` | Dashboard aggregate statistics (live DB queries) |
| GET | `/api/v1/projects` | List projects with pagination and status filter |
| POST | `/api/v1/projects` | Create a new project |
| GET | `/api/v1/projects/{id}` | Get a project by ID |
| PATCH | `/api/v1/projects/{id}` | Partially update (omit-vs-null aware) |
| DELETE | `/api/v1/projects/{id}` | Delete a project (requires frontend confirmation) |

---

## 9. Refinement Notes

This section records the rationale for decisions made during the API specification review.

### 9.1 Unified 422 for all validation failures

All field-level validation errors — including invalid `category` and `status` enum values — return HTTP 422. HTTP 400 is no longer used. This produces a uniform error-handling path on the frontend: any failed input produces a `detail` array that the frontend can parse consistently regardless of which field caused the error.

### 9.2 PATCH omit-vs-null semantics

`model_dump(exclude_unset=True)` is the mechanism. Fields absent from the request body are excluded from the dict and therefore never written to the database. Fields explicitly sent as `null` are included and applied. Required fields (`title`, `research_question`) are protected by a `model_validator` that raises if they appear in `model_fields_set` with a `None` value.

### 9.3 `ProjectCategory` as enum

The service-layer `VALID_CATEGORIES` list is replaced by a `ProjectCategory` enum. Pydantic validates enum membership automatically and produces a descriptive 422 error listing valid values. The frontend `categories.ts` constants file mirrors the enum values and is the designated sync point.

### 9.4 Database health probe in `/health`

The health endpoint executes `SELECT 1` in a try/except. If it succeeds, `database: "ok"`; if it raises, `database: "error"`. The HTTP status is always 200 so the process is reachable. The `database` field allows the frontend to surface a warning ("Backend is available but database is unreachable") distinct from "Backend is completely unreachable."

### 9.5 Summary endpoint uses live queries

The summary endpoint performs three real database queries on every call. It does not cache or mock. In Phase 1 at single-user scale this is negligible. Caching can be introduced in Phase 2 if needed.

### 9.6 UTC timestamps end-to-end

`datetime.now(timezone.utc)` is used everywhere — not `datetime.utcnow()`, which returns a naive datetime. SQLAlchemy stores the value; Pydantic serializes it with the `Z` suffix. The frontend can safely parse all timestamps as UTC without timezone conversion logic.

### 9.7 Delete requires frontend confirmation

The `DELETE` endpoint itself is unchanged — it accepts the request and returns 204. The confirmation requirement is a frontend constraint, enforced by using `AlertDialog` before the API call is made. This is documented here so the frontend implementation sub-task has the explicit requirement.
