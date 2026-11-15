# 26 — Backend Implementation Specification

**Project**: Multi-Agent Autonomous Researcher (MAAR)
**Phase**: 3
**Status**: Draft — Awaiting Approval

---

## 1. Integration Points

Phase 3 integrates into the existing backend at exactly two points:

### Integration Point 1 — `runs.py` route handler

**File**: `app/api/v1/routes/runs.py`

**Current code** (line 77):
```python
background_tasks.add_task(run_research_workflow, run.id)
```

**Phase 3 change**:
```python
if body.workflow_mode == "multi_agent":
    background_tasks.add_task(run_multi_agent_workflow, run.id)
else:
    background_tasks.add_task(run_research_workflow, run.id)
```

Nothing else in `runs.py` changes for the existing four endpoints. New endpoints are added (section 4).

### Integration Point 2 — `main.py` startup recovery

**File**: `app/main.py`

**Current code** — `_recover_stuck_runs()` marks `running` and `pending` runs as failed.

**Phase 3 addition** — the recovery logic already covers multi-agent runs because it operates on `research_runs.status` which is the same column. No change required to the recovery logic.

**Phase 3 addition** — after recovery, also mark any `research_tasks` with `status="running"` as `failed`. This requires one additional query in `_recover_stuck_runs()`.

---

## 2. Schema Changes

### `StartRunRequest` (app/schemas/run.py)

Add one optional field:
```python
workflow_mode: Literal["sequential", "multi_agent"] = "sequential"
```

No other fields change. Existing clients that do not send `workflow_mode` continue to get the sequential workflow.

### New response schemas (app/schemas/plan.py)

```python
class ResearchTaskResponse(BaseModel):
    id: str
    objective: str
    search_query: str
    expected_evidence_type: str | None
    priority: int
    status: str
    findings: str | None
    evidence_count: int
    unanswered_questions: list[str]
    limitations: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

class ResearchPlanResponse(BaseModel):
    id: str
    run_id: str
    objectives: list[str]
    tasks: list[ResearchTaskResponse]
    plan_version: int
    created_at: datetime
    updated_at: datetime
```

### New response schemas (app/schemas/agent.py)

```python
class AgentEventResponse(BaseModel):
    id: str
    agent_name: str
    event_type: str
    summary: str
    input_ref: str | None
    output_ref: str | None
    iteration: int
    created_at: datetime

class AgentActivityResponse(BaseModel):
    run_id: str
    events: list[AgentEventResponse]
    total: int
```

---

## 3. New Service Modules

### `app/graph/executor.py`

Primary entrypoint called from `runs.py` background task.

```
run_multi_agent_workflow(run_id: str) -> None

  1. Load ResearchRun from DB
  2. Validate: status="pending", workflow_mode="multi_agent"
  3. Mark run status="running", current_stage="Initializing"
  4. Build ResearchWorkflowState from run data
  5. Build execution config: {thread_id: run_id, recursion_limit: 25}
  6. Call: await research_graph.ainvoke(initial_state, config=config)
  7. Top-level exception handler:
     - catch GraphRecursionError → mark run failed with "Graph recursion limit exceeded"
     - catch any other Exception → mark run failed with safe_error_message(exc)
```

The executor imports `research_graph` from `app/graph/workflow.py` (module-level singleton compiled once).

### `app/graph/workflow.py`

Builds and compiles the LangGraph StateGraph. Returns a compiled graph.

Module-level singleton pattern:
```python
_graph = None

def get_research_graph():
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph
```

This avoids re-compiling on every background task invocation.

### `app/graph/state.py`

`ResearchWorkflowState` TypedDict definition and all reducer functions. No dependencies on FastAPI or SQLAlchemy — pure Python types.

### `app/graph/nodes.py`

Deterministic (non-LLM) graph nodes:

```
initialize_run_node(state, config) -> dict
  - Reads run from DB
  - Logs workflow_start event
  - Returns {workflow_status: "planning"}

finalize_report_node(state, config) -> dict
  - Loads all EvidenceRecord rows for run_id
  - Calls build_evidence_context() [Phase 2]
  - Calls build_prompt() [Phase 2]
  - Calls generate_report() [Phase 2]
  - Persists ResearchReport
  - Updates ResearchRun status/stage
  - Logs workflow_complete event
  - Returns {workflow_status: "completed", final_report_id: report.id}

fail_workflow_node(state, config) -> dict
  - Updates ResearchRun status="failed"
  - Marks running tasks as failed
  - Logs workflow_failed event
  - Returns {workflow_status: "failed"}
```

### `app/graph/checkpointer.py`

```python
from langgraph.checkpoint.sqlite import SqliteSaver

_checkpointer = None

def get_checkpointer() -> SqliteSaver:
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = SqliteSaver.from_conn_string("./maar_checkpoints.db")
    return _checkpointer
```

Module-level singleton — checkpointer is created once per process.

### `app/agents/supervisor.py`

```
async def supervisor_node(state: ResearchWorkflowState, config: dict) -> dict:

  1. Check forced termination: if iteration_count >= max_supervisor_cycles
     → return {supervisor_decision: "complete_research", iteration_count: +1, ...}

  2. Build user prompt from state (task summaries only, no raw evidence)

  3. Call LLM: await llm.complete(SUPERVISOR_SYSTEM_PROMPT, user_prompt)

  4. Parse response as SupervisorDecision (with fallback)

  5. Log AgentExecutionEvent

  6. Return state update dict
```

### `app/agents/planner.py`

```
async def planning_node(state: ResearchWorkflowState, config: dict) -> dict:

  1. Build user prompt (first plan vs. refinement)

  2. Call LLM: await llm.complete(PLANNER_SYSTEM_PROMPT, user_prompt)

  3. Parse response as ResearchPlan (with one retry)

  4. Validate task count (2-8), deduplicate objectives

  5. Persist via plan_service.save_plan(db, run_id, plan)

  6. Update ResearchRun.current_stage = "Planning"

  7. Log AgentExecutionEvent

  8. Return state update dict
```

### `app/agents/researcher.py`

```
async def research_node(state: ResearchWorkflowState, config: dict) -> dict:

  1. Determine current task from state

  2. task_service.update_task_status(task_id, "running")

  3. Collect web evidence: tools.web_search(task.search_query)

  4. Optionally collect document evidence: tools.get_document_chunks(run_id)

  5. Deduplicate evidence

  6. Persist EvidenceRecord rows (with task_id FK)

  7. Call LLM for findings summary (2-3 sentences)

  8. Build TaskResult

  9. task_service.update_task_status(task_id, status, findings=..., evidence_count=...)

  10. Log AgentExecutionEvent

  11. Return state update dict
```

### `app/agents/tools.py`

Pure async tool functions — no LangChain tool wrappers:

```
async def web_search(query, search_provider, num_results) -> list[NormalizedEvidence]
  Calls search_provider.search(query, num_results)
  Returns normalize_web_result() for each result that has content
  For results without content: calls fetch_web_content()

async def fetch_web_content(url, settings) -> NormalizedEvidence | None
  Calls is_safe_url(url) — returns None if blocked
  Calls fetch_url(url, timeout, max_content_kb)
  Returns normalize_web_result() or None

async def get_document_chunks(run_id, db) -> list[NormalizedEvidence]
  Queries UploadedDocument records for run_id
  Extracts text (same logic as Phase 2 _extract_documents)
  Returns normalize_document_chunk() for each chunk
```

---

## 4. New API Endpoints

All new endpoints are added to `app/api/v1/routes/runs.py` (or a new `plans.py` file registered in the router).

### GET `/api/v1/projects/{project_id}/runs/{run_id}/plan`

Returns the latest research plan for a run.

```
Response 200:  ResearchPlanResponse
Response 404:  Run not found, or no plan exists yet
Response 422:  Invalid UUID
```

Used by frontend to display research objectives and task list.

### GET `/api/v1/projects/{project_id}/runs/{run_id}/tasks`

Returns all research tasks for a run.

```
Query params:  status (optional filter)
Response 200:  { items: list[ResearchTaskResponse], total: int }
Response 404:  Run not found
```

Used by frontend to display task progress.

### GET `/api/v1/projects/{project_id}/runs/{run_id}/activity`

Returns agent execution events for a run (the execution timeline).

```
Query params:  limit (default 50), offset (default 0)
Response 200:  AgentActivityResponse
Response 404:  Run not found
```

Used by frontend execution timeline component.

### Modified: `POST /api/v1/projects/{project_id}/runs`

Add `workflow_mode` to request body (optional, default `"sequential"`). Response schema unchanged — existing `RunResponse` is returned.

---

## 5. Background Execution Model

Phase 3 uses the same `FastAPI BackgroundTasks` mechanism as Phase 2. The multi-agent workflow runs as a single background task per run:

```
POST /runs → creates DB record → returns 201 → background task starts
  Background task: run_multi_agent_workflow(run_id)
    │
    └── graph.ainvoke() → blocks until complete
         │
         └── Each node is async; awaits DB operations and LLM calls
```

**Why not use asyncio tasks or thread pools?**

- `BackgroundTasks` is the simplest mechanism in FastAPI and requires no additional infrastructure
- The graph itself is async (`ainvoke`) so it does not block the event loop
- One background task per run — no concurrency concerns between runs
- SqliteSaver (synchronous) is called within async nodes using `asyncio.get_event_loop().run_in_executor()` to avoid blocking

**SqliteSaver async compatibility**:

LangGraph 1.2.x's `SqliteSaver` is synchronous. Since nodes are async, the checkpointer calls are made through LangGraph's internal async adapter. The compiled graph's `ainvoke()` handles this transparently. No manual thread pool management is required.

---

## 6. Error Handling

### Node-level

Every node wraps its body in try/except. On exception:
```python
return {
    "workflow_status": "failed",
    "error_message": safe_error_message(exc),
}
```

The routing functions detect `workflow_status == "failed"` and route to `fail_workflow_node`.

### Executor-level

`run_multi_agent_workflow()` wraps the entire `graph.ainvoke()` in try/except:
```python
try:
    await research_graph.ainvoke(initial_state, config=config)
except GraphRecursionError:
    await _mark_run_failed(run_id, "Graph recursion limit exceeded (25 nodes).")
except Exception as exc:
    await _mark_run_failed(run_id, safe_error_message(exc))
```

### DB failure handling

If a DB write fails inside a node, the node sets `workflow_status="failed"`. The executor's outer catch marks the run failed at the DB level. This may result in the run being marked failed twice — the second write is idempotent and safe.

### `safe_error_message(exc)` function

The existing `_safe_error()` in `research_workflow.py` strips file paths and truncates to 500 chars. Phase 3 moves this to `app/core/errors.py` and imports it from both the old and new workflow. The function itself is unchanged.

---

## 7. Dependencies to Add

The following packages must be added to `requirements.txt`:

```
langgraph==1.2.20
langchain-core>=1.4.7,<2.0.0
```

LangGraph 1.2.20 requires:
- `langchain-core>=1.4.7` (will install `langchain-core 1.7.7`)
- `langsmith>=0.14.9` (installed as transitive dep)
- `jsonpatch>=1.33.0` (new)
- `tenacity>=8.1.0` (new)
- `uuid-utils>=0.12.0` (new)
- `distro>=1.7.0` (new)
- `requests-toolbelt>=1.0.0` (new)

All are compatible with Python 3.14.5 and existing stack. Verified via `pip install --dry-run`.

---

## 8. New Environment Variables

Add to `backend/.env.example` and `app/core/config.py`:

```python
# Phase 3 multi-agent settings
MAX_SUPERVISOR_CYCLES: int = 3
CHECKPOINT_DB_URL: str = "./maar_checkpoints.db"

# Structured logging format — "text" (default) or "json"
LOG_FORMAT: str = "text"

# LangSmith observability — all optional, all disabled by default
# These are standard LangChain/LangSmith env vars — NOT pydantic-settings fields.
# They are read directly by the langsmith library at runtime; do NOT add them to Settings.
# Add to .env to enable: LANGCHAIN_TRACING_V2=true, LANGCHAIN_API_KEY=..., LANGCHAIN_PROJECT=maar-phase3
# Optional input suppression: LANGCHAIN_HIDE_INPUTS=true, LANGCHAIN_HIDE_OUTPUTS=true
```

**Important**: `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`, `LANGCHAIN_ENDPOINT`, `LANGCHAIN_HIDE_INPUTS` are **NOT** added to the `Settings` pydantic model. They are standard LangSmith environment variables read directly by the `langsmith` library. Adding them to `Settings` would validate them at startup and create a dependency that contradicts the requirement that MAAR works without any LangSmith configuration.

The `LOG_FORMAT` setting IS added to `Settings` because it controls MAAR's own logging infrastructure (not LangSmith).

**`.env.example` additions**:
```ini
# ─── Phase 3 Multi-Agent ──────────────────────────────────────────────────────
MAX_SUPERVISOR_CYCLES=3
CHECKPOINT_DB_URL=./maar_checkpoints.db
LOG_FORMAT=text

# ─── LangSmith Observability (optional — remove or leave blank to disable) ────
# Uncomment and fill in to enable LangSmith tracing:
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY=ls__your_key_here
# LANGCHAIN_PROJECT=maar-phase3
# LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
# LANGCHAIN_HIDE_INPUTS=true    # uncomment to suppress sensitive input data
```

---

## 9. Structured Logging Infrastructure

`LOG_FORMAT=json` enables machine-readable log output. A logging configuration module (`app/core/logging_config.py`) is added in Phase 3:

```python
# app/core/logging_config.py  (design)

import logging
import json
from datetime import datetime, timezone

class JsonFormatter(logging.Formatter):
    """Emits each log record as a single JSON line."""
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Merge any extra= fields passed by the caller
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and key != "message":
                base[key] = value
        return json.dumps(base)

def configure_logging(log_format: str = "text") -> None:
    """Call once at application startup from app/main.py."""
    handler = logging.StreamHandler()
    if log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-8s %(name)s — %(message)s"
        ))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
```

`configure_logging(settings.LOG_FORMAT)` is called in `app/main.py`'s lifespan function before any other startup steps.

All agent modules use the standard `logger = logging.getLogger(__name__)` pattern. The JSON formatter automatically picks up any `extra={}` fields passed to log calls.

---

## 10. File Change Summary

| File | Change type | Description |
|---|---|---|
| `app/api/v1/routes/runs.py` | Modify | Add workflow_mode routing; add 3 new endpoints |
| `app/schemas/run.py` | Modify | Add workflow_mode field to StartRunRequest |
| `app/schemas/plan.py` | Create | ResearchTaskResponse, ResearchPlanResponse |
| `app/schemas/agent.py` | Create | AgentEventResponse, AgentActivityResponse |
| `app/models/run.py` | Modify | Add workflow_mode column, new relationships |
| `app/models/evidence.py` | Modify | Add task_id column, new relationship |
| `app/models/plan.py` | Create | ResearchPlan ORM |
| `app/models/task.py` | Create | ResearchTask ORM |
| `app/models/event.py` | Create | AgentExecutionEvent ORM |
| `app/models/__init__.py` | Modify | Import new models |
| `app/services/plan_service.py` | Create | Plan and task CRUD |
| `app/services/event_service.py` | Create | AgentExecutionEvent logging |
| `app/services/research_workflow.py` | No change | Phase 2 preserved exactly |
| `app/agents/__init__.py` | Create | — |
| `app/agents/supervisor.py` | Create | Supervisor agent node |
| `app/agents/planner.py` | Create | Planning agent node |
| `app/agents/researcher.py` | Create | Research agent node |
| `app/agents/tools.py` | Create | Tool functions |
| `app/graph/__init__.py` | Create | — |
| `app/graph/state.py` | Create | ResearchWorkflowState TypedDict |
| `app/graph/nodes.py` | Create | Deterministic nodes |
| `app/graph/workflow.py` | Create | StateGraph construction |
| `app/graph/executor.py` | Create | run_multi_agent_workflow() |
| `app/graph/checkpointer.py` | Create | SqliteSaver factory |
| `app/core/config.py` | Modify | New env vars (MAX_SUPERVISOR_CYCLES, CHECKPOINT_DB_URL, LOG_FORMAT) |
| `app/core/errors.py` | Create | safe_error_message() extracted from research_workflow.py |
| `app/core/logging_config.py` | Create | JsonFormatter + configure_logging() |
| `app/main.py` | Modify | Recovery: mark stuck tasks failed; call configure_logging() |
| `alembic/versions/XXX_phase3.py` | Create | Phase 3 schema migration |
| `requirements.txt` | Modify | Add langgraph==1.2.20, langchain-core |
| `backend/.env.example` | Modify | Document new env vars and LangSmith optional block |
| `tests/test_multi_agent_workflow.py` | Create | Phase 3 graph tests |
| `tests/test_agents.py` | Create | Individual agent tests |
