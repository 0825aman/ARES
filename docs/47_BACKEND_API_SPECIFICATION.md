# 47 — Backend API Specification

## Phase 5 — Complete API Reference

---

## 1. Overview

This document lists every backend API endpoint relevant to Phase 5, including both existing endpoints (unchanged) and all new Phase 5 endpoints. It serves as the authoritative API contract for frontend-backend integration.

**Base URL (local development):** `http://localhost:8000/api/v1`

---

## 2. New Phase 5 Endpoints

### 2.1 SSE Stream

#### `GET /runs/{run_id}/stream`

Opens a Server-Sent Events stream for a research run. The client receives live events as the graph executes.

**Path params:**
- `run_id` — UUID of the research run

**Query params:**
- None (Last-Event-ID is provided via HTTP header)

**Request headers:**
- `Last-Event-ID: {sequence_number}` — optional; when provided, server replays all events with `sequence > last_event_id`

**Response:**
- `Content-Type: text/event-stream`
- Stream of SSE messages

**SSE message format:**
```
id: {sequence_number}
event: {event_type}
data: {json_payload}

```

**Event types emitted:**

| Event Type | Trigger | Data shape |
|---|---|---|
| `connected` | On stream open | `{"run_id": "uuid", "message": "Stream connected"}` |
| `activity_event` | New `AgentExecutionEvent` | Full event record |
| `run_status_changed` | `ResearchRun.status` changes | `{"run_id": "uuid", "status": "running", "current_stage": "..."}` |
| `agent_status_changed` | Agent starts/completes task | `{"agent_name": "...", "status": "running|idle|completed"}` |
| `source_added` | New `ResearchSource` created | Full source record |
| `evidence_added` | New `Evidence` created | Full evidence record |
| `approval_required` | Graph interrupt fires | Approval request record + context_snapshot |
| `approval_resolved` | User submits decision | `{"approval_id": "uuid", "decision": "approved"}` |
| `heartbeat` | Every 30 seconds | `{"timestamp": "..."}` |
| `run_completed` | Run status → completed | `{"run_id": "uuid", "report_id": "uuid"}` |
| `run_failed` | Run status → failed | `{"run_id": "uuid", "error": "..."}` |

**Behaviour:**
- Stream stays open until client disconnects or run reaches terminal state (completed/failed)
- After terminal state, server emits `run_completed` or `run_failed`, then closes the stream
- Heartbeat every 30s prevents proxy timeouts

**HTTP status:** 200 (stream opened) or 404 (run not found)

---

### 2.2 Approval Endpoints

#### `GET /runs/{run_id}/approval`

Returns the current pending approval for a run, or `null` if none exists.

**Response (pending):**
```json
{
  "id": "uuid",
  "run_id": "uuid",
  "checkpoint_name": "plan_approval",
  "node_name": "planning_complete_node",
  "context_snapshot": {
    "research_question": "...",
    "plan_summary": "...",
    "planned_tasks": ["task1", "task2"],
    "estimated_sources": 12,
    "workflow_mode": "deep_research"
  },
  "status": "pending",
  "created_at": "2026-11-12T10:00:00Z",
  "expires_at": "2026-11-13T10:00:00Z"
}
```

**Response (none):** HTTP 200, body `null`

---

#### `POST /runs/{run_id}/approval/{approval_id}/decide`

Submit an approval decision.

**Request body:**
```json
{
  "decision": "approved",
  "notes": "Optional revision instructions"
}
```

**Validation:**
- `decision`: required, enum `["approved", "rejected", "revision_requested"]`
- `notes`: optional string, max 2000 chars
- Approval must be `pending` and not expired

**Response:**
```json
{
  "id": "uuid",
  "decision": "approved",
  "decided_at": "2026-11-12T10:05:00Z",
  "run_status": "running"
}
```

**HTTP status:**
- 200 — decision accepted
- 404 — approval not found for this run
- 409 — approval already decided or expired
- 422 — validation error

---

#### `GET /runs/{run_id}/approvals`

Returns all approval records for a run (history).

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "checkpoint_name": "plan_approval",
      "status": "approved",
      "decision": "approved",
      "created_at": "...",
      "decided_at": "..."
    }
  ]
}
```

---

### 2.3 Export Endpoints

#### `POST /runs/{run_id}/export`

Trigger synchronous report export.

**Request body:**
```json
{
  "format": "pdf",
  "report_id": "optional-uuid"
}
```

**Validation:**
- `format`: required, enum `["pdf", "docx", "markdown"]`
- `report_id`: optional UUID; if omitted, uses current report for the run
- Run must have a completed report

**Response:**
```json
{
  "id": "uuid",
  "run_id": "uuid",
  "report_id": "uuid",
  "format": "pdf",
  "status": "ready",
  "file_size_bytes": 48320,
  "created_at": "...",
  "completed_at": "...",
  "download_url": "/api/v1/runs/{run_id}/export/{export_id}/download"
}
```

**HTTP status:**
- 200 — export generated and ready
- 404 — run or report not found
- 422 — validation error
- 500 — generation failed (body includes `error_message`)

---

#### `GET /runs/{run_id}/export/{export_id}/download`

Download the generated export file.

**Response:** Binary file stream with appropriate `Content-Type` and `Content-Disposition: attachment; filename="..."` headers.

**HTTP status:**
- 200 — file returned
- 404 — export record or file not found
- 409 — export not in `ready` status

---

#### `GET /runs/{run_id}/exports`

List all export records for a run.

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "format": "pdf",
      "status": "ready",
      "file_size_bytes": 48320,
      "created_at": "...",
      "completed_at": "...",
      "download_url": "/api/v1/runs/{run_id}/export/{id}/download"
    }
  ]
}
```

---

### 2.4 Report Versioning Endpoints

#### `GET /runs/{run_id}/reports`

Returns all report versions for a run.

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "version_number": 2,
      "is_current": true,
      "title": "...",
      "confidence_score": 0.84,
      "word_count": 1240,
      "created_at": "..."
    }
  ]
}
```

---

#### `GET /reports/{report_id}` (existing — no change)

Returns a full report by ID. Used when loading a specific version.

---

## 3. Existing Endpoints (No Changes in Phase 5)

These endpoints are already implemented and remain unchanged:

### Runs

| Method | Path | Description |
|---|---|---|
| GET | `/runs` | List all runs (optionally filtered by project_id) |
| GET | `/runs/{run_id}` | Get run details |
| POST | `/runs` | Create a new run |
| POST | `/runs/{run_id}/start` | Start a run |
| POST | `/runs/{run_id}/stop` | Stop a run |
| GET | `/runs/{run_id}/activity` | Get activity events (REST polling fallback) |

### Sources

| Method | Path | Description |
|---|---|---|
| GET | `/sources` | List sources (filter: `run_id`, paginated) |
| GET | `/sources/{id}` | Get source detail |

### Evidence

| Method | Path | Description |
|---|---|---|
| GET | `/evidence` | List evidence (filter: `run_id`, paginated) |
| GET | `/evidence/{id}` | Get evidence detail |

### Claims

| Method | Path | Description |
|---|---|---|
| GET | `/claims` | List claims (filter: `run_id`) |
| GET | `/claims/{id}` | Get claim detail |
| PATCH | `/claims/{id}` | Update claim status |

### Critic Reviews

| Method | Path | Description |
|---|---|---|
| GET | `/reviews` | List reviews (filter: `run_id`) |
| GET | `/reviews/{id}` | Get review detail |

### Reports

| Method | Path | Description |
|---|---|---|
| GET | `/reports` | List reports (filter: `run_id`) |
| GET | `/reports/{id}` | Get report detail |

### Projects

| Method | Path | Description |
|---|---|---|
| GET | `/projects` | List projects |
| POST | `/projects` | Create project |
| GET | `/projects/{id}` | Get project detail |
| PATCH | `/projects/{id}` | Update project |
| DELETE | `/projects/{id}` | Delete project |

### Health

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Backend health check |

---

## 4. Error Response Format

All error responses use the standard FastAPI error format:

```json
{
  "detail": "Human-readable error message"
}
```

For validation errors (422):
```json
{
  "detail": [
    {
      "loc": ["body", "format"],
      "msg": "value is not a valid enumeration member",
      "type": "type_error.enum"
    }
  ]
}
```

---

## 5. CORS Configuration

No changes to Phase 4 CORS settings:
- Allowed origins: `http://localhost:3000`
- Allowed methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
- Allowed headers: `*`
- `allow_credentials: True`

The SSE endpoint (`/runs/{run_id}/stream`) requires no additional CORS changes — it is a GET request and falls under the same policy.

---

## 6. Pydantic Schemas — New in Phase 5

### ApprovalRequest schemas

```python
class ApprovalContextSnapshot(BaseModel):
    # CP-1
    research_question: Optional[str]
    plan_summary: Optional[str]
    planned_tasks: Optional[List[str]]
    estimated_sources: Optional[int]
    workflow_mode: Optional[str]
    # CP-2
    review_status: Optional[str]
    overall_assessment: Optional[str]
    critical_issues: Optional[List[str]]
    recommendations: Optional[List[str]]
    report_quality_score: Optional[float]

class ApprovalRequestResponse(BaseModel):
    id: UUID
    run_id: UUID
    checkpoint_name: str
    node_name: str
    context_snapshot: ApprovalContextSnapshot
    status: str
    created_at: datetime
    expires_at: datetime

class ApprovalDecisionRequest(BaseModel):
    decision: Literal["approved", "rejected", "revision_requested"]
    notes: Optional[str] = Field(None, max_length=2000)

class ApprovalDecisionResponse(BaseModel):
    id: UUID
    decision: str
    decided_at: datetime
    run_status: str
```

### Export schemas

```python
class ExportRequest(BaseModel):
    format: Literal["pdf", "docx", "markdown"]
    report_id: Optional[UUID] = None

class ExportRecordResponse(BaseModel):
    id: UUID
    run_id: UUID
    report_id: UUID
    format: str
    status: str
    file_size_bytes: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]
    download_url: str
    error_message: Optional[str] = None
```

### Report version schemas

```python
class ReportVersionSummary(BaseModel):
    id: UUID
    version_number: int
    is_current: bool
    title: str
    confidence_score: Optional[float]
    word_count: Optional[int]
    created_at: datetime
    archived_at: Optional[datetime] = None
```
