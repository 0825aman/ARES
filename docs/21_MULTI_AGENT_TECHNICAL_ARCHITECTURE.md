# 21 — Multi-Agent Technical Architecture

**Project**: Multi-Agent Autonomous Researcher (MAAR)
**Phase**: 3
**Status**: Draft — Awaiting Approval

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  Browser (Next.js)                                                   │
│  ResearchPanel → polling → GET /runs/{id}, /plans/{id}, /tasks      │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ HTTP
┌────────────────────────────────▼────────────────────────────────────┐
│  FastAPI                                                             │
│  POST /projects/{id}/runs  → creates ResearchRun record             │
│                            → launches background task               │
│                                                                      │
│  GET  /projects/{id}/runs/{run_id}         → run status             │
│  GET  /projects/{id}/runs/{run_id}/plan    → ResearchPlan           │
│  GET  /projects/{id}/runs/{run_id}/tasks   → ResearchTask list      │
│  GET  /projects/{id}/runs/{run_id}/report  → ResearchReport         │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ asyncio background task
┌────────────────────────────────▼────────────────────────────────────┐
│  Graph Execution Service  (app/graph/executor.py)                   │
│  - Selects workflow_mode: sequential → Phase2   multi_agent → Graph │
│  - Builds initial ResearchWorkflowState                             │
│  - Calls graph.ainvoke(state, config) with thread_id = run_id       │
│  - Handles top-level exceptions → marks run failed                  │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ LangGraph StateGraph
┌────────────────────────────────▼────────────────────────────────────┐
│  LangGraph Graph  (app/graph/workflow.py)                           │
│                                                                      │
│  Nodes (deterministic):                                              │
│    initialize_run  ──► supervisor_node ──► planning_node            │
│                             ▲                    │                  │
│                             │                    ▼                  │
│                        research_node ◄────  [conditional]           │
│                             │                                        │
│                             ▼                                        │
│                        supervisor_node ──► finalize_report          │
│                                      └──► fail_workflow             │
│                                                                      │
│  Nodes (LLM-driven):                                                 │
│    supervisor_node    app/agents/supervisor.py                       │
│    planning_node      app/agents/planner.py                         │
│    research_node      app/agents/researcher.py                      │
│                                                                      │
│  Checkpointer: SqliteSaver → maar_checkpoints.db                    │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ tool calls / service calls
┌────────────────────────────────▼────────────────────────────────────┐
│  Phase 2 Services (UNCHANGED)                                        │
│                                                                      │
│  web_search_provider.search()       TavilySearchProvider            │
│  web_fetcher.fetch_url()            trafilatura + httpx             │
│  web_fetcher.is_safe_url()          SSRF guard                      │
│  evidence_normalizer.*              NormalizedEvidence + helpers    │
│  context_builder.build_evidence_context()                           │
│  context_builder.build_prompt()                                     │
│  report_generator.generate_report()                                 │
│  run_service.*                      ResearchRun CRUD                │
│  document_service.*                 UploadedDocument CRUD           │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ SQLAlchemy async
┌────────────────────────────────▼────────────────────────────────────┐
│  Application Database  (maar_dev.db)                                │
│                                                                      │
│  Existing tables (unchanged):                                        │
│    research_projects, research_runs, evidence_records,              │
│    uploaded_documents, research_reports                              │
│                                                                      │
│  New Phase 3 tables:                                                 │
│    research_plans, research_tasks, agent_execution_events           │
└─────────────────────────────────────────────────────────────────────┘

  Checkpoint Database  (maar_checkpoints.db)
    LangGraph SqliteSaver — execution snapshots keyed by run_id
```

---

## 2. Component Map

| Component | Layer | Location | Status |
|---|---|---|---|
| Next.js frontend | Presentation | `maar/frontend/` | Existing — Phase 3 additions |
| FastAPI app | API | `app/main.py` | Existing — minor additions |
| runs.py router | API | `app/api/v1/routes/runs.py` | Existing — extend with new endpoints |
| Graph Execution Service | Orchestration | `app/graph/executor.py` | **New** |
| StateGraph definition | Orchestration | `app/graph/workflow.py` | **New** |
| ResearchWorkflowState | Orchestration | `app/graph/state.py` | **New** |
| Graph nodes (deterministic) | Orchestration | `app/graph/nodes.py` | **New** |
| LangGraph checkpointer | Orchestration | `app/graph/checkpointer.py` | **New** |
| Supervisor Agent | Agent | `app/agents/supervisor.py` | **New** |
| Research Planning Agent | Agent | `app/agents/planner.py` | **New** |
| Research Agent | Agent | `app/agents/researcher.py` | **New** |
| Agent tool definitions | Agent | `app/agents/tools.py` | **New** |
| research_workflow.py | Service | `app/services/research_workflow.py` | Existing — unchanged |
| evidence_normalizer.py | Service | `app/services/evidence_normalizer.py` | Existing — unchanged |
| context_builder.py | Service | `app/services/context_builder.py` | Existing — unchanged |
| report_generator.py | Service | `app/services/report_generator.py` | Existing — unchanged |
| run_service.py | Service | `app/services/run_service.py` | Existing — minor addition (workflow_mode) |
| document_service.py | Service | `app/services/document_service.py` | Existing — unchanged |
| project_service.py | Service | `app/services/project_service.py` | Existing — unchanged |
| plan_service.py | Service | `app/services/plan_service.py` | **New** |
| task_service.py | Service | `app/services/task_service.py` | **New** |
| event_service.py | Service | `app/services/event_service.py` | **New** |
| LLMProvider ABC | Provider | `app/providers/llm.py` | Existing — unchanged |
| WebSearchProvider ABC | Provider | `app/providers/web_search.py` | Existing — unchanged |
| web_fetcher.py | Provider | `app/providers/web_fetcher.py` | Existing — unchanged |
| ORM models (Phase 1-2) | Data | `app/models/` | Existing — EvidenceRecord gets `task_id` column |
| ResearchPlan ORM | Data | `app/models/plan.py` | **New** |
| ResearchTask ORM | Data | `app/models/task.py` | **New** |
| AgentExecutionEvent ORM | Data | `app/models/event.py` | **New** |
| Alembic migration (Phase 3) | Data | `alembic/versions/` | **New** |

---

## 3. Three-Agent Responsibilities

### Supervisor Agent

**Has access to**: state (read-only except `supervisor_decision`, `iteration_count`, `revision_notes`, `workflow_status`), structured log of completed task summaries.

**Does NOT have access to**: web search tools, document tools, LLM synthesis, database write operations.

**Produces**: one of 7 routing decisions (see FR-003 in doc 20) as a `SupervisorDecision` Pydantic model. Reasoning is captured in a `reasoning` string field persisted as an AgentExecutionEvent.

**Interaction with other agents**: reads `task_results` dict and `plan` from state. Writes `supervisor_decision`, `revision_notes` (when revising), `iteration_count`. Never calls the Planning or Research agents directly — LangGraph routing functions handle dispatch.

### Research Planning Agent

**Has access to**: `research_question`, `research_configuration`, `existing_plan` (optional, for refinements), `revision_notes` (optional).

**Does NOT have access to**: web search tools, document tools, evidence data, database.

**Produces**: `ResearchPlan` Pydantic model with 2-8 `ResearchTask` objects. Each task has a stable `task_id` (UUID generated at planning time), `objective`, `search_query`, `expected_evidence_type`, `priority`.

**Writes to state**: `research_plan`, `research_tasks` (full list), `pending_task_ids` (list of task_ids).

### Research Agent

**Has access to**: one `ResearchTask` at a time (objective + search_query), run_id for evidence persistence. Calls three tool functions defined in `app/agents/tools.py`.

**Does NOT have access to**: supervisor decisions, other tasks' details, LLM synthesis.

**Produces**: `TaskResult` Pydantic model with task_id, status, findings (string summary), evidence_ids (list of persisted EvidenceRecord IDs), unanswered_questions, limitations, error (optional).

**Writes to state**: appends task_id to `completed_task_ids`, adds `TaskResult` to `task_results`, appends evidence_ids to `collected_evidence_ids`.

---

## 4. LangGraph Integration Point

The existing `runs.py` route currently does:

```python
background_tasks.add_task(run_research_workflow, run.id)
```

Phase 3 changes this to:

```python
if body.workflow_mode == "multi_agent":
    background_tasks.add_task(run_multi_agent_workflow, run.id)
else:
    background_tasks.add_task(run_research_workflow, run.id)   # unchanged
```

The new `run_multi_agent_workflow(run_id)` function (in `app/graph/executor.py`) builds the initial state, invokes the compiled graph, and handles top-level error capture. **The Phase 2 `run_research_workflow` function is not modified**.

The `StartRunRequest` schema gains one optional field: `workflow_mode: Literal["sequential", "multi_agent"] = "sequential"`. The `ResearchRun` model gains one column: `workflow_mode VARCHAR(20) DEFAULT "sequential"`.

---

## 5. Phase 2 Service Reuse Map

| Phase 2 Service | Used By | How |
|---|---|---|
| `TavilySearchProvider.search()` | Research Agent | Called via `tools.web_search()` wrapper |
| `is_safe_url()` + `fetch_url()` | Research Agent | Called via `tools.fetch_web_content()` wrapper |
| `normalize_web_result()` | Research Agent | Called inside `tools.web_search()` |
| `normalize_document_chunk()` | Research Agent | Called inside `tools.get_document_chunks()` |
| `chunk_text()` | Research Agent | Called inside `tools.get_document_chunks()` |
| `build_evidence_context()` | `finalize_report` node | Builds cross-task evidence context |
| `build_prompt()` | `finalize_report` node | Builds synthesis prompt |
| `SYSTEM_PROMPT` | `finalize_report` node | Used as LLM system prompt |
| `generate_report()` | `finalize_report` node | Full report generation — unchanged |
| `run_service.get_run()` | executor.py, all nodes | Run record access |
| `run_service.update_status()` | graph nodes | Stage/status updates |
| `document_service.list_documents()` | Research Agent tools | Load doc metadata for chunk tool |
| `EvidenceRecord` ORM | Research Agent tools | Persist new evidence records |
| `ResearchReport` ORM | `finalize_report` node | Persist final report |

### What does NOT change in Phase 2 services

- `run_research_workflow()` — completely preserved, runs when `workflow_mode="sequential"`
- `LLMProvider` ABC and all implementations — unchanged interface
- `WebSearchProvider` ABC — unchanged interface
- All existing Pydantic schemas in `app/schemas/` — unchanged (new schemas added separately)

---

## 6. New Module Structure

```
maar/backend/app/
├── agents/
│   ├── __init__.py
│   ├── supervisor.py       # Supervisor agent: LLM call → SupervisorDecision
│   ├── planner.py          # Planning agent: LLM call → ResearchPlan
│   ├── researcher.py       # Research agent: tool calls → TaskResult
│   └── tools.py            # Tool functions exposed to Research Agent
├── graph/
│   ├── __init__.py
│   ├── state.py            # ResearchWorkflowState TypedDict + reducers
│   ├── nodes.py            # Deterministic nodes: initialize_run, finalize_report, fail_workflow
│   ├── workflow.py         # StateGraph construction and compilation
│   ├── executor.py         # run_multi_agent_workflow() entrypoint
│   └── checkpointer.py     # SqliteSaver factory function
├── schemas/
│   ├── ...                 # Existing schemas unchanged
│   ├── plan.py             # ResearchPlan, ResearchTask, ResearchObjective Pydantic schemas
│   └── agent.py            # SupervisorDecision, TaskResult, AgentEvent Pydantic schemas
├── models/
│   ├── ...                 # Existing models unchanged
│   ├── plan.py             # ResearchPlan ORM model
│   ├── task.py             # ResearchTask ORM model
│   └── event.py            # AgentExecutionEvent ORM model
└── services/
    ├── ...                 # Existing services unchanged
    ├── plan_service.py     # CRUD for ResearchPlan and ResearchTask
    └── event_service.py    # AgentExecutionEvent persistence
```

---

## 7. Complete Data Flow

1. **User submits research run** (`POST /api/v1/projects/{id}/runs` with `workflow_mode="multi_agent"`)
   - FastAPI creates `ResearchRun` record with `workflow_mode="multi_agent"`, `status="pending"`
   - Returns 201 immediately
   - Launches `run_multi_agent_workflow(run_id)` as background task

2. **Graph executor initialises**
   - Loads `ResearchRun` from DB
   - Builds `ResearchWorkflowState` with `run_id`, `research_question`, `workflow_status="initializing"`
   - Updates `ResearchRun.status = "running"`, `current_stage = "Initializing"`
   - Invokes `graph.ainvoke(initial_state, config={"configurable": {"thread_id": run_id}})`

3. **`initialize_run` node** (deterministic)
   - Validates run exists and is `running`
   - Writes initial `AgentExecutionEvent`: workflow started
   - Returns state with `workflow_status = "planning"`

4. **`supervisor_node`** (LLM-driven, iteration 0)
   - Reads: `research_question`, `iteration_count=0`, `workflow_status`
   - Produces: `SupervisorDecision(decision="request_plan", reasoning="...")`
   - Writes: `supervisor_decision = "request_plan"`, `iteration_count = 1`
   - Persists `AgentExecutionEvent`
   - Conditional edge routes to `planning_node`

5. **`planning_node`** (LLM-driven)
   - Reads: `research_question`, `revision_notes` (null on first call)
   - Produces: `ResearchPlan` with 3-6 `ResearchTask` objects
   - Persists `ResearchPlan` and `ResearchTask` rows to DB
   - Writes: `research_plan`, `research_tasks`, `pending_task_ids`
   - Updates `ResearchRun.current_stage = "Planning"`
   - Conditional edge routes back to `supervisor_node`

6. **`supervisor_node`** (LLM-driven, iteration 1)
   - Reads: `research_plan`, `task summaries`
   - Produces: `SupervisorDecision(decision="execute_next_task", reasoning="...")`
   - Conditional edge routes to `research_node`

7. **`research_node`** (LLM-driven + tool calls, repeats per task)
   - Picks first `pending_task_id`, marks task `running` in DB
   - Calls `tools.web_search(task.search_query)` → web evidence
   - Optionally calls `tools.get_document_chunks(run_id)` → document evidence
   - Persists `EvidenceRecord` rows with `task_id` reference
   - Produces `TaskResult`
   - Updates task status to `completed` or `failed` in DB
   - Writes: appends task to `completed_task_ids`, adds to `task_results`, appends `evidence_ids`
   - Routes back to `supervisor_node`

8. **`supervisor_node`** (LLM-driven, subsequent iterations)
   - Reviews all `task_results`
   - If more tasks pending: routes to `research_node`
   - If all tasks complete: routes to `finalize_report`
   - If coverage insufficient and within iteration limit: routes to `planning_node` with `revision_notes`
   - If iteration limit reached: forces `complete_research` → `finalize_report`

9. **`finalize_report` node** (deterministic)
   - Loads all `EvidenceRecord` rows for this `run_id` from DB
   - Calls `build_evidence_context()`, `build_prompt()`, `generate_report()`
   - Persists `ResearchReport` to DB
   - Updates `ResearchRun.status = "completed"`, `current_stage = "Complete"`
   - Writes `AgentExecutionEvent`: workflow complete

10. **Frontend polling** detects `status="completed"` → loads report + plan + tasks

---

## 8. Three Persistence Layers

### Layer A — LangGraph Working State (in-memory during execution)

- `ResearchWorkflowState` TypedDict held in memory during graph execution
- Contains: run_id, research_question, plan object, task list, task_results dict, evidence_ids list, routing decisions, iteration counts
- Does NOT contain raw evidence content (too large) — only IDs
- Checkpointed to Layer C at each node boundary

### Layer B — Application Database (`maar_dev.db`)

- Permanent business records
- `research_runs` — lifecycle status, current stage, timestamps
- `research_plans` — plan structure (JSON objectives)
- `research_tasks` — individual tasks with status
- `evidence_records` — all retrieved evidence with content
- `agent_execution_events` — immutable audit log of agent decisions
- `research_reports` — final synthesised output
- All records survive backend restarts

### Layer C — LangGraph Checkpoint Database (`maar_checkpoints.db`)

- `SqliteSaver` managed by LangGraph, separate file
- Stores full graph state snapshots after each node completes
- Used for: resuming interrupted executions, debugging state at any point
- Does NOT replace Layer B — Layer B is the authoritative business record
- Thread ID = `run_id` → one checkpoint thread per research run

### Consistency contract

- Before any DB write in a node, the checkpoint for the previous step already exists
- A backend restart can inspect Layer B (run status) and Layer C (last graph checkpoint)
- Recovery: mark run as `failed` in Layer B; Layer C checkpoint is preserved for inspection but not auto-resumed in Phase 3

---

## 9. Technology Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Graph framework | LangGraph 1.2.20 | Latest stable; Pydantic 2.x compatible; SQLite checkpointer available |
| LangGraph version pinned | `==1.2.20` | Breaking changes are common in LangGraph; pinning prevents surprises |
| Checkpoint backend | SqliteSaver | No additional infrastructure; SQLite-compatible with rest of stack |
| Task execution | Sequential | Safest for first multi-agent implementation; avoids DB transaction conflicts |
| Structured output | Pydantic JSON via prompts | Works with any LLM including watsonx; no tool-calling API required |
| Agent LLM | Shared provider from settings | `meta-llama/llama-3-3-70b-instruct` via watsonx; all agents share one provider |
| New modules location | `app/agents/`, `app/graph/` | Clear separation from existing `app/services/` and `app/providers/` |
| Phase 2 preservation | Sequential workflow unchanged | Default `workflow_mode="sequential"` preserves all existing behaviour |

---

## 10. Integration Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| LangGraph API changes between 1.2.x patches | High | Pin exact version `langgraph==1.2.20` in requirements.txt |
| LLM returns malformed JSON for structured decisions | High | All agent prompts include explicit JSON schema; retry logic with max 2 retries |
| Supervisor loops indefinitely | High | Hard `max_supervisor_cycles` limit; LangGraph `recursion_limit=25` |
| Evidence IDs in state become stale if DB rolls back | Medium | Evidence is appended (not updated); rollback leaves orphan records (acceptable) |
| SqliteSaver thread-safety with async FastAPI | Medium | Graph runs in background task (single thread per run); SqliteSaver is sync, called via executor |
| Research Agent calls too many web URLs | Medium | Bounded by `SEARCH_MAX_RESULTS` setting; existing SSRF guard preserved |
| Watsonx rate limits under parallel planning + research | Low | Sequential execution in Phase 3 means only one LLM call at a time |
