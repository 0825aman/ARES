# 14 — Backend API Specification (Phase 2)

**Project**: Multi-Agent Autonomous Researcher (MAAR)
**Phase**: 2 — First End-to-End Research Workflow
**Status**: Planning

---

## 1. Phase 1 API Preservation

All Phase 1 endpoints remain unchanged:

| Method | Path | Status |
|---|---|---|
| GET | `/health` | ✅ Unchanged |
| GET | `/api/v1/projects/summary` | ✅ Unchanged |
| GET | `/api/v1/projects/` | ✅ Unchanged |
| POST | `/api/v1/projects/` | ✅ Unchanged |
| GET | `/api/v1/projects/{project_id}` | ✅ Unchanged |
| PATCH | `/api/v1/projects/{project_id}` | ✅ Unchanged |
| DELETE | `/api/v1/projects/{project_id}` | ✅ Unchanged |

---

## 2. New Phase 2 Endpoints

All new endpoints are nested under `/api/v1/projects/{project_id}/` to maintain project-scoped resource hierarchy.

---

### 2.1 Upload Document

**`POST /api/v1/projects/{project_id}/documents`**

Upload one or more documents to a project. Documents are uploaded before the run is created, then associated with a run at submission time.

**Content-Type**: `multipart/form-data`

**Request**: Form field `files` — one or more file uploads.

**Validation**:
- `project_id` must be a valid UUID and must exist.
- Each file: extension must be `.pdf`, `.docx`, or `.txt`.
- Each file: MIME type must match the extension.
- Each file: size must not exceed `MAX_UPLOAD_SIZE_MB`.
- Maximum 10 files per request.

**Response** `201 Created`:
```json
{
  "uploaded": [
    {
      "id": "uuid",
      "original_filename": "report.pdf",
      "file_size_bytes": 204800,
      "mime_type": "application/pdf",
      "uploaded_at": "2026-01-01T12:00:00Z"
    }
  ],
  "rejected": [
    {
      "filename": "image.png",
      "reason": "Unsupported file type. Accepted: pdf, docx, txt."
    }
  ]
}
```

**Error responses**:
- `404` — Project not found.
- `422` — No valid files in request.
- `413` — File exceeds size limit.
- `500` — Storage failure.

---

### 2.2 List Documents for Project

**`GET /api/v1/projects/{project_id}/documents`**

List all documents uploaded to a project (across all runs, ordered by upload date descending).

**Response** `200 OK`:
```json
{
  "items": [
    {
      "id": "uuid",
      "run_id": "uuid-or-null",
      "original_filename": "report.pdf",
      "file_size_bytes": 204800,
      "mime_type": "application/pdf",
      "extraction_status": "success",
      "uploaded_at": "2026-01-01T12:00:00Z"
    }
  ],
  "total": 1
}
```

---

### 2.3 Delete Document

**`DELETE /api/v1/projects/{project_id}/documents/{document_id}`**

Delete an uploaded document. Only allowed if the document is not associated with a `running` research run.

**Response**: `204 No Content`

**Error responses**:
- `404` — Document not found.
- `409 Conflict` — Document is part of a currently running research run.

---

### 2.4 Start Research Run

**`POST /api/v1/projects/{project_id}/runs`**

Create a new research run and start the workflow in the background.

**Content-Type**: `application/json`

**Request body**:
```json
{
  "research_question": "What are the environmental impacts of lithium mining?",
  "use_web": true,
  "use_documents": false,
  "document_ids": []
}
```

**Field rules**:
- `research_question`: string, 1–1000 chars, required, stripped of leading/trailing whitespace.
- `use_web`: boolean, required. Must be `true` if `use_documents` is `false`.
- `use_documents`: boolean, required. If `true`, `document_ids` must contain at least one valid document ID.
- `document_ids`: array of UUID strings, optional (default `[]`). All IDs must belong to this project.
- At least one of `use_web` or `use_documents` must be `true`.

**Validation errors** `422`:
- Both sources disabled.
- `use_documents: true` with empty `document_ids`.
- Invalid document IDs (not belonging to this project).
- Another run is already in `running` state for this project.

**Response** `201 Created`:
```json
{
  "id": "run-uuid",
  "project_id": "project-uuid",
  "research_question": "What are the environmental impacts...",
  "use_web": true,
  "use_documents": false,
  "status": "pending",
  "current_stage": null,
  "error_message": null,
  "started_at": null,
  "completed_at": null,
  "created_at": "2026-01-01T12:00:00Z"
}
```

**Error responses**:
- `404` — Project not found.
- `409 Conflict` — A run is already active for this project.
- `422` — Validation failure.

---

### 2.5 List Research Runs

**`GET /api/v1/projects/{project_id}/runs`**

List all research runs for a project, ordered by creation date descending.

**Query parameters**:
- `limit` (int, default 20, max 100)
- `offset` (int, default 0)

**Response** `200 OK`:
```json
{
  "items": [
    {
      "id": "run-uuid",
      "project_id": "project-uuid",
      "research_question": "...",
      "use_web": true,
      "use_documents": false,
      "status": "completed",
      "current_stage": "Complete",
      "error_message": null,
      "started_at": "2026-01-01T12:00:00Z",
      "completed_at": "2026-01-01T12:03:22Z",
      "created_at": "2026-01-01T12:00:00Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

---

### 2.6 Get Research Run Status

**`GET /api/v1/projects/{project_id}/runs/{run_id}`**

Retrieve a single run's status and metadata. Used by the frontend polling loop.

**Response** `200 OK`: Same shape as a single item in the list response above.

**Error responses**:
- `404` — Run not found or does not belong to this project.

---

### 2.7 Get Research Report

**`GET /api/v1/projects/{project_id}/runs/{run_id}/report`**

Retrieve the completed research report for a run.

**Response** `200 OK`:
```json
{
  "id": "report-uuid",
  "run_id": "run-uuid",
  "research_question": "What are the environmental impacts...",
  "executive_summary": "Lithium mining has significant...",
  "key_findings": [
    "Lithium extraction requires large volumes of water...",
    "Open-pit mining causes soil erosion..."
  ],
  "evidence_used": [
    {
      "source_label": "[SOURCE 1]",
      "source_type": "web",
      "url": "https://example.com/article",
      "title": "Environmental Impact of Lithium Mining",
      "excerpt": "Lithium extraction in the Atacama..."
    },
    {
      "source_label": "[SOURCE 2]",
      "source_type": "document",
      "filename": "report.pdf",
      "chunk_index": 0,
      "page_number": 3
    }
  ],
  "observations": "Multiple sources agree that...",
  "contradictions": null,
  "limitations": "Only 3 of 8 web sources were successfully retrieved...",
  "sources": [
    {
      "type": "web",
      "url": "https://example.com/article",
      "title": "Environmental Impact of Lithium Mining",
      "retrieved_at": "2026-01-01T12:01:04Z"
    },
    {
      "type": "document",
      "filename": "report.pdf",
      "mime_type": "application/pdf"
    }
  ],
  "generated_at": "2026-01-01T12:03:20Z"
}
```

**Error responses**:
- `404` — Run not found, report not yet generated (run still in progress), or run failed.

**Note**: `raw_llm_response` is intentionally excluded from the API response. It is stored in the DB for internal debugging only.

---

## 3. Router Structure

New routes are registered in `app/api/v1/router.py`:

```python
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(runs.router,     prefix="/projects", tags=["runs"])
api_router.include_router(documents.router, prefix="/projects", tags=["documents"])
```

The `runs` and `documents` routers use path parameters beginning with `/{project_id}/` so the project scoping is enforced at the route level.

---

## 4. HTTP Status Code Reference

| Code | Meaning in this API |
|---|---|
| 200 | Successful GET |
| 201 | Resource created (POST) |
| 204 | Successful DELETE (no body) |
| 404 | Resource not found |
| 409 | Conflict (duplicate active run, document in use) |
| 413 | Request entity too large (file size) |
| 422 | Validation failure (Pydantic) |
| 500 | Internal server error |

---

## 5. Error Response Format

All error responses follow the FastAPI/Pydantic convention:

**Validation errors (422)**:
```json
{
  "detail": [
    { "loc": ["body", "use_web"], "msg": "field required", "type": "missing" }
  ]
}
```

**Application errors (404, 409, 413, 500)**:
```json
{
  "detail": "Human-readable error message."
}
```

Error messages for 500 responses must never expose stack traces, file paths, or internal service details.
