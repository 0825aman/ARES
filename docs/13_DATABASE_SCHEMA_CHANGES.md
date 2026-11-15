# 13 — Database Schema Changes

**Project**: Multi-Agent Autonomous Researcher (MAAR)
**Phase**: 2 — First End-to-End Research Workflow
**Status**: Planning

---

## 1. Existing Phase 1 Schema Assessment

The Phase 1 database contains a single table: `research_projects`.

**`research_projects` — current state:**

| Column | Type | Constraints |
|---|---|---|
| `id` | VARCHAR(36) | PK, UUID string |
| `title` | VARCHAR(200) | NOT NULL |
| `research_question` | TEXT | NOT NULL |
| `description` | TEXT | NULL |
| `category` | VARCHAR(100) | NULL, INDEX |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT `not_started`, INDEX |
| `created_at` | DATETIME | NOT NULL, INDEX |
| `updated_at` | DATETIME | NOT NULL |

**Assessment**: This table requires **no column changes** in Phase 2. A `runs` relationship will be added to the ORM model, but it is a Python-level relationship only — no SQL migration is needed for the projects table.

---

## 2. New Tables

### 2.1 `research_runs`

Tracks each execution of the research workflow against a project.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK, UUID string | `default=uuid4()` |
| `project_id` | VARCHAR(36) | FK → `research_projects.id`, NOT NULL, INDEX | CASCADE DELETE |
| `research_question` | TEXT | NOT NULL | May differ from project's RQ |
| `use_web` | BOOLEAN | NOT NULL, DEFAULT TRUE | Whether web search was requested |
| `use_documents` | BOOLEAN | NOT NULL, DEFAULT FALSE | Whether document search was requested |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT `pending`, INDEX | Enum: pending/running/completed/failed |
| `current_stage` | VARCHAR(100) | NULL | Human-readable stage label |
| `error_message` | TEXT | NULL | Safe error description on failure |
| `started_at` | DATETIME | NULL | Set when status→running |
| `completed_at` | DATETIME | NULL | Set when status→completed/failed |
| `created_at` | DATETIME | NOT NULL, INDEX | `default=utcnow()` |

**Indexes**: `project_id`, `status`, `created_at`
**Cascade**: Deleting a `ResearchProject` deletes all its `ResearchRun` rows.

---

### 2.2 `uploaded_documents`

Tracks files uploaded by the user for a specific research run.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK, UUID string | |
| `run_id` | VARCHAR(36) | FK → `research_runs.id`, NOT NULL, INDEX | CASCADE DELETE |
| `project_id` | VARCHAR(36) | FK → `research_projects.id`, NOT NULL, INDEX | Redundant FK for direct project-level queries |
| `original_filename` | VARCHAR(500) | NOT NULL | Original name from upload |
| `stored_filename` | VARCHAR(500) | NOT NULL | UUID-based safe filename on disk |
| `storage_path` | TEXT | NOT NULL | Full path relative to `UPLOAD_DIR` |
| `mime_type` | VARCHAR(100) | NOT NULL | Validated MIME type |
| `file_size_bytes` | INTEGER | NOT NULL | |
| `content_hash` | VARCHAR(64) | NOT NULL, INDEX | SHA-256 of file content (deduplication) |
| `extraction_status` | VARCHAR(20) | NOT NULL, DEFAULT `pending` | Enum: pending/success/failed |
| `extraction_error` | TEXT | NULL | Safe error if extraction failed |
| `uploaded_at` | DATETIME | NOT NULL | `default=utcnow()` |

**Indexes**: `run_id`, `project_id`, `content_hash`
**Cascade**: Deleting a `ResearchRun` deletes its `UploadedDocument` rows. Files on disk are deleted by the service layer before the DB delete (or via a cleanup job).

---

### 2.3 `evidence_records`

Normalized evidence from both web and document sources.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK, UUID string | |
| `run_id` | VARCHAR(36) | FK → `research_runs.id`, NOT NULL, INDEX | CASCADE DELETE |
| `source_type` | VARCHAR(20) | NOT NULL | `web` or `document` |
| `source_label` | VARCHAR(20) | NOT NULL | `[SOURCE 1]`, `[SOURCE 2]`, etc. |
| `content` | TEXT | NULL | Extracted/fetched text chunk |
| `relevance_score` | FLOAT | NOT NULL, DEFAULT 0.0 | Keyword overlap score |
| `fetch_status` | VARCHAR(20) | NOT NULL, DEFAULT `success` | `success` or `failed` |
| `fetch_error` | TEXT | NULL | Error reason if failed |
| `url` | TEXT | NULL | Web: source URL |
| `page_title` | VARCHAR(500) | NULL | Web: page title |
| `retrieved_at` | DATETIME | NULL | Web: fetch timestamp |
| `document_id` | VARCHAR(36) | NULL, FK → `uploaded_documents.id` | Document: source document |
| `chunk_index` | INTEGER | NULL | Document: position within document |
| `page_number` | INTEGER | NULL | Document: page number if available |

**Indexes**: `run_id`, `source_type`
**Cascade**: Deleting a `ResearchRun` deletes its `EvidenceRecord` rows.

---

### 2.4 `research_reports`

One report per research run (one-to-one relationship).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK, UUID string | |
| `run_id` | VARCHAR(36) | FK → `research_runs.id`, NOT NULL, UNIQUE | CASCADE DELETE |
| `research_question` | TEXT | NOT NULL | Denormalized for easy retrieval |
| `executive_summary` | TEXT | NOT NULL | |
| `key_findings` | TEXT | NOT NULL | JSON array of finding strings |
| `evidence_used` | TEXT | NOT NULL | JSON array of source references |
| `observations` | TEXT | NULL | Additional observations |
| `contradictions` | TEXT | NULL | JSON array or prose |
| `limitations` | TEXT | NOT NULL | |
| `sources` | TEXT | NOT NULL | JSON array of { type, url/filename, title } |
| `raw_llm_response` | TEXT | NULL | Stored for debugging; not exposed to API |
| `generated_at` | DATETIME | NOT NULL | `default=utcnow()` |

**Note on JSON fields**: SQLite does not have a native JSON type. JSON arrays are stored as TEXT. SQLAlchemy's `JSON` type handles serialization/deserialization automatically with SQLite.

**Indexes**: `run_id` (UNIQUE)
**Cascade**: Deleting a `ResearchRun` deletes its `ResearchReport`.

---

## 3. Entity Relationship Diagram

```
research_projects
    │ id (PK)
    │ title
    │ research_question
    │ ...
    │
    ├──< research_runs (project_id FK)
    │       │ id (PK)
    │       │ research_question
    │       │ use_web, use_documents
    │       │ status, current_stage
    │       │ started_at, completed_at
    │       │
    │       ├──< uploaded_documents (run_id FK)
    │       │       id (PK)
    │       │       original_filename, stored_filename
    │       │       mime_type, file_size_bytes
    │       │       content_hash
    │       │       extraction_status
    │       │
    │       ├──< evidence_records (run_id FK)
    │       │       id (PK)
    │       │       source_type (web | document)
    │       │       source_label
    │       │       content, relevance_score
    │       │       url / document_id
    │       │
    │       └──  research_reports (run_id FK, UNIQUE)
    │               id (PK)
    │               executive_summary
    │               key_findings (JSON)
    │               sources (JSON)
    │               ...
```

---

## 4. Cascade Deletion Behavior

When a `ResearchProject` is deleted (Phase 1 behavior preserved):
- All `ResearchRun` rows for that project are deleted (CASCADE).
- All `UploadedDocument` rows for those runs are deleted (CASCADE).
- All `EvidenceRecord` rows for those runs are deleted (CASCADE).
- All `ResearchReport` rows for those runs are deleted (CASCADE).
- The service layer is responsible for deleting uploaded files from disk before the DB transaction.

SQLAlchemy `relationship(..., cascade="all, delete-orphan")` enforces this in the ORM. The `ondelete="CASCADE"` foreign key constraint also enforces it at the SQLite level.

---

## 5. Migration Strategy

### Phase 2 Approach: Alembic

Alembic is not present in the Phase 1 codebase. It must be introduced in Phase 2 because:
- Phase 1 uses `create_all()` on startup — acceptable when there is only one table and no migration history.
- Phase 2 adds 4 new tables. Future phases will modify existing tables (e.g. add columns to `research_runs`).
- Without Alembic, schema changes require manual `DROP TABLE` and data loss.

**Migration plan**:

1. Install `alembic` in `requirements.txt`.
2. Run `alembic init alembic` in `maar/backend/` to generate `alembic/` directory and `alembic.ini`.
3. Configure `alembic/env.py` to use the async SQLAlchemy engine from `app/core/database.py` and import all models.
4. Generate initial migration: `alembic revision --autogenerate -m "phase1_initial"` — captures the existing `research_projects` table.
5. Generate Phase 2 migration: `alembic revision --autogenerate -m "phase2_research_workflow"` — captures the 4 new tables.
6. Remove the `create_all()` call from `app/main.py` lifespan. Replace with a startup check that runs `alembic upgrade head` programmatically.

**Why not keep `create_all()`?** `create_all()` only creates tables that don't exist — it never modifies existing ones. Any future column addition would require manual intervention. Alembic tracks the schema version in the `alembic_version` table and generates safe incremental migrations.

**SQLite + Alembic limitation**: SQLite has limited `ALTER TABLE` support (no `DROP COLUMN` in older versions). Alembic handles this with `batch_alter_table` mode, which rebuilds the table. This must be configured in `alembic/env.py` with `render_as_batch=True`.

**Developer workflow** (after Phase 2):
```powershell
# Apply all pending migrations
cd maar\backend; .venv\Scripts\Activate.ps1; alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "description_of_change"
```

---

## 6. Indexes Summary

| Table | Column(s) | Type | Reason |
|---|---|---|---|
| `research_runs` | `project_id` | B-tree | Run lookups by project |
| `research_runs` | `status` | B-tree | Filter runs by status |
| `research_runs` | `created_at` | B-tree | Ordering |
| `uploaded_documents` | `run_id` | B-tree | Document lookups by run |
| `uploaded_documents` | `content_hash` | B-tree | Deduplication checks |
| `evidence_records` | `run_id` | B-tree | Evidence lookups by run |
| `research_reports` | `run_id` | UNIQUE | One report per run |
