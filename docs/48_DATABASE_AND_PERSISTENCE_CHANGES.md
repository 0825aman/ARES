# 48 — Database and Persistence Changes

## Phase 5

---

## 1. Overview

Phase 5 introduces three new database tables, modifies two existing tables, and adds one new column to a third. All changes are additive — no existing data is destroyed or restructured (except the relaxed uniqueness constraint on `research_reports`, which requires a migration-time data fix described below).

All changes are applied via Alembic migrations. The Phase 4 migration chain ends at head `g7b8c9d0e1f2`. Phase 5 adds three new migrations: H, I, and J.

---

## 2. Summary of All Changes

| Table | Change Type | Details |
|---|---|---|
| `agent_execution_events` | Column added | `sequence` — auto-increment integer for SSE ordering |
| `research_reports` | Column added | `version_number` INTEGER |
| `research_reports` | Column added | `is_current` BOOLEAN |
| `research_reports` | Constraint changed | `UNIQUE(run_id)` → `UNIQUE(run_id, version_number)` |
| `approval_requests` | New table | Human approval workflow state |
| `report_versions` | New table | Report version archive |
| `export_records` | New table | Export file tracking |
| `research_runs` | No changes | `status` enum gains `awaiting_approval` (string field, no constraint change) |

---

## 3. Migration H — Approval Requests and Event Sequencing

**Alembic revision ID:** `h8c9d0e1f2a3`
**Down revision:** `g7b8c9d0e1f2`

### 3.1 Add `sequence` to `agent_execution_events`

```sql
ALTER TABLE agent_execution_events
ADD COLUMN sequence INTEGER;

-- Back-fill existing rows with row-number ordering by created_at within each run
UPDATE agent_execution_events
SET sequence = (
    SELECT COUNT(*)
    FROM agent_execution_events b
    WHERE b.run_id = agent_execution_events.run_id
      AND b.created_at <= agent_execution_events.created_at
      AND b.id <= agent_execution_events.id
);

CREATE UNIQUE INDEX idx_agent_events_run_sequence
ON agent_execution_events(run_id, sequence);
```

**Note:** After back-fill, new rows get `sequence` values via a SQLAlchemy event listener or a service-layer increment — SQLite does not support sequences natively. The service layer uses `SELECT MAX(sequence) + 1 FROM agent_execution_events WHERE run_id = ?` within the same transaction as the insert.

### 3.2 Create `approval_requests` table

```sql
CREATE TABLE approval_requests (
    id          TEXT PRIMARY KEY,
    run_id      TEXT NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    checkpoint_name  VARCHAR(100) NOT NULL,
    node_name        VARCHAR(100) NOT NULL,
    context_snapshot TEXT NOT NULL,    -- JSON string
    status      VARCHAR(20)  NOT NULL DEFAULT 'pending',
    decision    VARCHAR(30),
    decision_notes   TEXT,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decided_at  DATETIME,
    expires_at  DATETIME NOT NULL
);

CREATE INDEX idx_approval_requests_run_id
ON approval_requests(run_id);

CREATE INDEX idx_approval_requests_run_status
ON approval_requests(run_id, status);
```

**No partial unique index on SQLite** (SQLite partial indexes via `WHERE` are supported since 3.8.9). Use application-level check before inserting: verify no `pending` approval exists for the same `(run_id, checkpoint_name)` before creating a new one.

---

## 4. Migration I — Report Versioning

**Alembic revision ID:** `i9d0e1f2a3b4`
**Down revision:** `h8c9d0e1f2a3`

### 4.1 Add columns to `research_reports`

```sql
ALTER TABLE research_reports
ADD COLUMN version_number INTEGER NOT NULL DEFAULT 1;

ALTER TABLE research_reports
ADD COLUMN is_current BOOLEAN NOT NULL DEFAULT TRUE;
```

**Back-fill:** All existing rows already have `version_number = 1` and `is_current = TRUE` due to the `DEFAULT` values.

### 4.2 Relax the UNIQUE constraint on `research_reports`

SQLite does not support `DROP CONSTRAINT`. The migration uses the standard SQLite constraint-change pattern:

```sql
-- 1. Create new table with updated constraint
CREATE TABLE research_reports_new (
    id                  TEXT PRIMARY KEY,
    run_id              TEXT NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    title               TEXT NOT NULL,
    executive_summary   TEXT,
    methodology         TEXT,
    findings            TEXT,
    conclusions         TEXT,
    sources_used        TEXT,
    confidence_score    REAL,
    word_count          INTEGER,
    version_number      INTEGER NOT NULL DEFAULT 1,
    is_current          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(run_id, version_number)
);

-- 2. Copy data
INSERT INTO research_reports_new SELECT *, 1, TRUE FROM research_reports;

-- 3. Drop old table
DROP TABLE research_reports;

-- 4. Rename new table
ALTER TABLE research_reports_new RENAME TO research_reports;

-- 5. Recreate index
CREATE INDEX idx_research_reports_run_current
ON research_reports(run_id, is_current);
```

### 4.3 Create `report_versions` table

```sql
CREATE TABLE report_versions (
    id               TEXT PRIMARY KEY,
    report_id        TEXT NOT NULL REFERENCES research_reports(id) ON DELETE CASCADE,
    run_id           TEXT NOT NULL,
    version_number   INTEGER NOT NULL,
    archived_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    content_snapshot TEXT NOT NULL    -- JSON string
);

CREATE INDEX idx_report_versions_run_id
ON report_versions(run_id);

CREATE INDEX idx_report_versions_report_id
ON report_versions(report_id);
```

---

## 5. Migration J — Export Records

**Alembic revision ID:** `j0e1f2a3b4c5`
**Down revision:** `i9d0e1f2a3b4`

### 5.1 Create `export_records` table

```sql
CREATE TABLE export_records (
    id               TEXT PRIMARY KEY,
    run_id           TEXT NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    report_id        TEXT NOT NULL REFERENCES research_reports(id) ON DELETE CASCADE,
    format           VARCHAR(10)  NOT NULL,
    status           VARCHAR(20)  NOT NULL DEFAULT 'pending',
    file_path        TEXT,
    file_size_bytes  INTEGER,
    error_message    TEXT,
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at     DATETIME
);

CREATE INDEX idx_export_records_run_id
ON export_records(run_id);
```

---

## 6. ORM Model Definitions

### 6.1 AgentExecutionEvent — updated

New column added to existing SQLAlchemy model:

```python
sequence = Column(Integer, nullable=True)
# Set to NOT NULL after back-fill migration completes
```

### 6.2 ApprovalRequest — new model

```python
class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    run_id = Column(String, ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False)
    checkpoint_name = Column(String(100), nullable=False)
    node_name = Column(String(100), nullable=False)
    context_snapshot = Column(Text, nullable=False)   # JSON
    status = Column(String(20), nullable=False, default="pending")
    decision = Column(String(30), nullable=True)
    decision_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    
    run = relationship("ResearchRun", back_populates="approval_requests")
```

### 6.3 ReportVersion — new model

```python
class ReportVersion(Base):
    __tablename__ = "report_versions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    report_id = Column(String, ForeignKey("research_reports.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(String, nullable=False)
    version_number = Column(Integer, nullable=False)
    archived_at = Column(DateTime, default=datetime.utcnow)
    content_snapshot = Column(Text, nullable=False)   # JSON
    
    report = relationship("ResearchReport", back_populates="versions")
```

### 6.4 ExportRecord — new model

```python
class ExportRecord(Base):
    __tablename__ = "export_records"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    run_id = Column(String, ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False)
    report_id = Column(String, ForeignKey("research_reports.id", ondelete="CASCADE"), nullable=False)
    format = Column(String(10), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    file_path = Column(Text, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    run = relationship("ResearchRun", back_populates="export_records")
    report = relationship("ResearchReport", back_populates="export_records")
```

---

## 7. Entity Relationship Diagram — Phase 5 Additions

```
research_runs
  ├── agent_execution_events  (existing, + sequence column)
  ├── approval_requests       (new)
  ├── export_records          (new)
  └── research_reports        (existing, + version_number, is_current)
        ├── report_versions   (new)
        └── export_records    (new)
```

---

## 8. Database Initialization Changes

`backend/app/core/database.py` — the `init_db()` function calls `Base.metadata.create_all()`. The three new models must be imported before this call so SQLAlchemy registers their tables. This is done by adding the new model imports to `backend/app/models/__init__.py`.

---

## 9. Migration Execution Order

```
Existing chain:
  a1b2c3d4e5f6  →  b2c3d4e5f6a1  →  ...  →  g7b8c9d0e1f2

Phase 5 additions:
  g7b8c9d0e1f2  →  h8c9d0e1f2a3  →  i9d0e1f2a3b4  →  j0e1f2a3b4c5
```

Run migrations with:
```bash
cd backend
alembic upgrade head
```

---

## 10. Export Directory Initialization

At application startup, `backend/app/core/config.py` gains:

```python
EXPORT_DIR: str = "./exports"
APPROVAL_EXPIRY_HOURS: int = 24
```

The main `app/main.py` startup event creates the export directory if it does not exist:

```python
@app.on_event("startup")
async def startup_event():
    Path(settings.EXPORT_DIR).mkdir(parents=True, exist_ok=True)
```

---

## 11. Data Volume Considerations

For typical Phase 5 usage (single user, local development):

| Table | Expected rows per run |
|---|---|
| `agent_execution_events` | 50–200 |
| `approval_requests` | 1–4 |
| `report_versions` | 1–3 |
| `export_records` | 1–10 |

No performance concerns for SQLite at this scale. Indexing strategy is sufficient.

---

## 12. Rollback Strategy

Each Alembic migration has a corresponding `downgrade()` function:
- Migration H downgrade: `DROP TABLE approval_requests`, `DROP COLUMN sequence` from events (SQLite: requires table rebuild)
- Migration I downgrade: Rebuild `research_reports` without version columns, `DROP TABLE report_versions`
- Migration J downgrade: `DROP TABLE export_records`

SQLite's lack of `ALTER TABLE DROP COLUMN` (before SQLite 3.35) means column drops require the rebuild-rename pattern in downgrade functions.
