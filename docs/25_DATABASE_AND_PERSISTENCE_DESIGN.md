# 25 — Database and Persistence Design

**Project**: Multi-Agent Autonomous Researcher (MAAR)
**Phase**: 3
**Status**: Draft — Awaiting Approval

---

## 1. Existing Schema Assessment

The following tables exist from Phases 1 and 2 and MUST NOT be modified except where explicitly noted:

| Table | Rows | Phase 3 change |
|---|---|---|
| `research_projects` | id, title, research_question, description, category, status, created_at, updated_at | None |
| `research_runs` | id, project_id, research_question, use_web, use_documents, status, current_stage, error_message, started_at, completed_at, created_at | Add `workflow_mode` column |
| `evidence_records` | id, run_id, source_type, source_label, content, relevance_score, fetch_status, fetch_error, url, page_title, retrieved_at, document_id, chunk_index, page_number | Add `task_id` column (nullable FK) |
| `uploaded_documents` | id, project_id, run_id, original_filename, storage_path, file_size_bytes, mime_type, content_hash, extraction_status, extraction_error, uploaded_at | None |
| `research_reports` | id, run_id, research_question, executive_summary, key_findings, evidence_used, observations, contradictions, limitations, sources, raw_llm_response, generated_at | None |

### Modifications to existing tables

**`research_runs` — add `workflow_mode` column**
```sql
ALTER TABLE research_runs ADD COLUMN workflow_mode VARCHAR(20) NOT NULL DEFAULT 'sequential';
```
- Allows frontend and backend to distinguish Phase 2 and Phase 3 runs
- Default `'sequential'` ensures all existing runs continue to work unchanged
- Indexed for filtering

**`evidence_records` — add `task_id` column**
```sql
ALTER TABLE evidence_records ADD COLUMN task_id VARCHAR(36) REFERENCES research_tasks(id) ON DELETE SET NULL;
```
- Nullable FK — existing Phase 2 evidence records have no task_id (NULL is valid)
- Allows per-task evidence attribution in the frontend and reporting
- Indexed for efficient task-level evidence retrieval

---

## 2. New Tables

### 2.1 `research_plans`

Stores the structured research plan produced by the Planning Agent for each run. One plan per run (a refined plan replaces the previous one via upsert).

```sql
CREATE TABLE research_plans (
    id              VARCHAR(36)  PRIMARY KEY,
    run_id          VARCHAR(36)  NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    objectives      TEXT         NOT NULL,    -- JSON array of objective strings
    refinement_notes TEXT        NULL,        -- populated on re-planning
    plan_version    INTEGER      NOT NULL DEFAULT 1,
    created_at      DATETIME     NOT NULL,
    updated_at      DATETIME     NOT NULL,

    CONSTRAINT uq_research_plans_run_id UNIQUE (run_id, plan_version)
);
CREATE INDEX ix_research_plans_run_id ON research_plans(run_id);
```

**ORM model location**: `app/models/plan.py`

**Notes**:
- `objectives` stored as JSON TEXT (SQLite compatible — same pattern as `research_reports.key_findings`)
- `plan_version` increments on re-planning (Supervisor requested revision)
- Frontend queries `GET /api/v1/projects/{id}/runs/{run_id}/plan` which returns the latest version

---

### 2.2 `research_tasks`

Stores individual research tasks within a plan. Each task has its own lifecycle status.

```sql
CREATE TABLE research_tasks (
    id                    VARCHAR(36)  PRIMARY KEY,
    plan_id               VARCHAR(36)  NOT NULL REFERENCES research_plans(id) ON DELETE CASCADE,
    run_id                VARCHAR(36)  NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    task_order            INTEGER      NOT NULL DEFAULT 0,
    objective             TEXT         NOT NULL,
    search_query          TEXT         NOT NULL,
    expected_evidence_type VARCHAR(100) NULL,
    priority              INTEGER      NOT NULL DEFAULT 2,
    status                VARCHAR(20)  NOT NULL DEFAULT 'pending',
    findings              TEXT         NULL,   -- LLM-generated finding summary
    evidence_count        INTEGER      NOT NULL DEFAULT 0,
    unanswered_questions  TEXT         NULL,   -- JSON array
    limitations           TEXT         NULL,
    error_message         TEXT         NULL,
    started_at            DATETIME     NULL,
    completed_at          DATETIME     NULL,
    created_at            DATETIME     NOT NULL
);
CREATE INDEX ix_research_tasks_run_id  ON research_tasks(run_id);
CREATE INDEX ix_research_tasks_plan_id ON research_tasks(plan_id);
CREATE INDEX ix_research_tasks_status  ON research_tasks(status);
```

**ORM model location**: `app/models/task.py`

**Status lifecycle**:
```
pending → running → completed
                 → partial
                 → failed
```

**Notes**:
- `task_id` in `evidence_records` references this table's `id`
- `unanswered_questions` stored as JSON TEXT
- `task_order` tracks original priority-based ordering from the plan

---

### 2.3 `agent_execution_events`

Immutable audit log of significant agent actions. New rows are only ever inserted, never updated or deleted. This is the primary observability record for the multi-agent workflow.

```sql
CREATE TABLE agent_execution_events (
    id           VARCHAR(36)  PRIMARY KEY,
    run_id       VARCHAR(36)  NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    agent_name   VARCHAR(50)  NOT NULL,    -- "supervisor", "planner", "researcher", "system"
    event_type   VARCHAR(50)  NOT NULL,    -- see event type list below
    summary      TEXT         NOT NULL,    -- human-readable one-line description
    input_ref    VARCHAR(200) NULL,        -- e.g. "task_id:abc123"
    output_ref   VARCHAR(200) NULL,        -- e.g. "decision:execute_next_task"
    iteration    INTEGER      NOT NULL DEFAULT 0,
    created_at   DATETIME     NOT NULL
);
CREATE INDEX ix_agent_execution_events_run_id    ON agent_execution_events(run_id);
CREATE INDEX ix_agent_execution_events_created_at ON agent_execution_events(created_at);
```

**ORM model location**: `app/models/event.py`

**Event types**:

| Event type | agent_name | When |
|---|---|---|
| `workflow_start` | system | initialize_run node |
| `plan_requested` | supervisor | Supervisor decides `request_plan` |
| `plan_revision_requested` | supervisor | Supervisor decides `revise_plan` |
| `research_delegated` | supervisor | Supervisor decides `execute_next_task` |
| `completion_decided` | supervisor | Supervisor decides `complete_research` |
| `failure_decided` | supervisor | Supervisor decides `fail_workflow` |
| `plan_created` | planner | planning_node saves plan (version 1) |
| `plan_revised` | planner | planning_node saves revised plan (version > 1) |
| `task_started` | researcher | research_node begins a task |
| `task_completed` | researcher | task finishes with evidence collected |
| `task_failed` | researcher | task finishes with no usable evidence |
| `report_generating` | system | finalize_report node starts |
| `workflow_complete` | system | finalize_report node succeeds |
| `workflow_failed` | system | fail_workflow node |

---

## 3. Entity Relationship Diagram

```
research_projects
    │ 1
    │ ↓ CASCADE
research_runs ──── workflow_mode VARCHAR(20) DEFAULT 'sequential'
    │ 1
    ├──────────────────────────────────────────────────────┐
    │ ↓ CASCADE                                            │ ↓ CASCADE
research_plans                                      evidence_records ── task_id FK (nullable)
    │ 1                                                                     │
    │ ↓ CASCADE                                                             │
research_tasks ─────────────────────────────────────────────────────────── ┘
    (task_id → evidence_records.task_id)

research_runs 1──N agent_execution_events
research_runs 1──1 research_reports
research_runs 1──N uploaded_documents
```

---

## 4. New ORM Models

### `ResearchPlan` (app/models/plan.py)

```python
class ResearchPlan(Base):
    __tablename__ = "research_plans"
    __table_args__ = (UniqueConstraint("run_id", "plan_version"),)

    id: Mapped[str]              # UUID primary key
    run_id: Mapped[str]          # FK → research_runs.id CASCADE
    objectives: Mapped[str]      # JSON TEXT
    refinement_notes: Mapped[str | None]
    plan_version: Mapped[int]    # default 1
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    # Relationships
    run: Mapped["ResearchRun"]   # back_populates="plans"
    tasks: Mapped[list["ResearchTask"]]  # back_populates="plan"
```

### `ResearchTask` (app/models/task.py)

```python
class ResearchTask(Base):
    __tablename__ = "research_tasks"

    id: Mapped[str]
    plan_id: Mapped[str]         # FK → research_plans.id CASCADE
    run_id: Mapped[str]          # FK → research_runs.id CASCADE (denormalised for query convenience)
    task_order: Mapped[int]
    objective: Mapped[str]
    search_query: Mapped[str]
    expected_evidence_type: Mapped[str | None]
    priority: Mapped[int]
    status: Mapped[str]          # pending / running / completed / partial / failed
    findings: Mapped[str | None]
    evidence_count: Mapped[int]
    unanswered_questions: Mapped[str | None]  # JSON TEXT
    limitations: Mapped[str | None]
    error_message: Mapped[str | None]
    started_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]
    created_at: Mapped[datetime]

    # Relationships
    plan: Mapped["ResearchPlan"]
    run: Mapped["ResearchRun"]
    evidence_records: Mapped[list["EvidenceRecord"]]  # back_populates="task"
```

### `AgentExecutionEvent` (app/models/event.py)

```python
class AgentExecutionEvent(Base):
    __tablename__ = "agent_execution_events"

    id: Mapped[str]
    run_id: Mapped[str]          # FK → research_runs.id CASCADE
    agent_name: Mapped[str]
    event_type: Mapped[str]
    summary: Mapped[str]
    input_ref: Mapped[str | None]
    output_ref: Mapped[str | None]
    iteration: Mapped[int]
    created_at: Mapped[datetime]

    # Relationships
    run: Mapped["ResearchRun"]
```

### Modifications to existing ORM models

**`ResearchRun` (app/models/run.py)** — add:
```python
workflow_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="sequential")
plans: Mapped[list["ResearchPlan"]] = relationship("ResearchPlan", back_populates="run", cascade="all, delete-orphan")
tasks: Mapped[list["ResearchTask"]] = relationship("ResearchTask", back_populates="run", cascade="all, delete-orphan")
events: Mapped[list["AgentExecutionEvent"]] = relationship("AgentExecutionEvent", back_populates="run", cascade="all, delete-orphan")
```

**`EvidenceRecord` (app/models/evidence.py)** — add:
```python
task_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("research_tasks.id", ondelete="SET NULL"), nullable=True, index=True)
task: Mapped["ResearchTask | None"] = relationship("ResearchTask", back_populates="evidence_records")
```

---

## 5. New Service Modules

### `app/services/plan_service.py`

```
save_plan(db, run_id, plan: ResearchPlan) → ResearchPlan ORM
    Creates ResearchPlan row and all ResearchTask rows.
    Handles plan versioning (increments plan_version).

get_latest_plan(db, run_id) → ResearchPlan ORM | None
    Returns the most recent plan version for a run.

get_tasks(db, run_id) → list[ResearchTask ORM]
    Returns all tasks for a run, ordered by task_order.

update_task_status(db, task_id, status, **kwargs) → None
    Updates task status, findings, evidence_count, timestamps.
```

### `app/services/event_service.py`

```
log_event(db, run_id, agent_name, event_type, summary, **kwargs) → None
    Creates AgentExecutionEvent row.
    Fire-and-forget pattern — errors are logged but do not fail the workflow.

get_events(db, run_id) → list[AgentExecutionEvent ORM]
    Returns all events for a run, ordered by created_at.
```

---

## 6. Migration Strategy

### Alembic migration file

A single new Alembic migration file covers all Phase 3 schema changes:

```
alembic/versions/XXXXXXXX_phase3_multi_agent_schema.py
```

**Migration operations (up)**:
1. Add `workflow_mode` column to `research_runs`
2. Add `task_id` column to `evidence_records`
3. Create `research_plans` table
4. Create `research_tasks` table
5. Create `agent_execution_events` table

**Migration operations (down)**:
1. Drop `agent_execution_events`
2. Drop `research_tasks`
3. Drop `research_plans`
4. Drop `task_id` from `evidence_records`
5. Drop `workflow_mode` from `research_runs`

The migration uses `render_as_batch=True` (already configured in `alembic/env.py`) which is required for column additions in SQLite.

### Backward compatibility

- `workflow_mode DEFAULT 'sequential'` — all existing runs get the sequential mode automatically
- `task_id NULLABLE` — all existing evidence records get NULL task_id, which is valid
- All existing API endpoints continue to work without change
- The existing `run_research_workflow()` code path is completely unaffected

### Generating the migration

```powershell
# Windows PowerShell (from maar/backend with venv active)
alembic revision --autogenerate -m "phase3_multi_agent_schema"
alembic upgrade head
```

---

## 7. What Belongs Where

| Data | Application DB | LangGraph Checkpoints |
|---|---|---|
| ResearchRun lifecycle status | ✅ | ❌ |
| ResearchPlan and objectives | ✅ | Copy in state (small) |
| ResearchTask status and findings | ✅ | Reference by ID in state |
| EvidenceRecord content | ✅ | IDs only in state |
| AgentExecutionEvent audit trail | ✅ | ❌ |
| ResearchReport content | ✅ | ID only in state |
| Graph node execution state | ❌ | ✅ |
| Supervisor decision history | AgentExecutionEvent ✅ | Part of state snapshot ✅ |
| LLM prompt/response strings | AgentExecutionEvent (summary only) | Not stored |
| Task result dicts | ResearchTask row ✅ | Compact dict in state ✅ |

The application DB is the **authoritative record** for all business data. LangGraph checkpoints are a technical artifact for graph execution management and should not be queried by application code directly.
