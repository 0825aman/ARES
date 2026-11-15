# MAAR Phase 3 — Master Implementation Plan

**Project**: Multi-Agent Autonomous Researcher (MAAR)
**Phase**: 3 — Multi-Agent Research Architecture
**Status**: ✅ Phase 3 Complete — 166/166 tests passing, `npm run build` passing

---

## Overview

Phase 3 introduces a genuine multi-agent architecture using LangGraph 1.2.20. Three specialized agents — Supervisor, Research Planning, and Research — coordinate through a typed shared state to decompose complex research questions, execute structured tasks, evaluate completeness, and generate consolidated reports.

Phase 2 is fully preserved. The sequential research workflow remains the default. Multi-agent is opt-in via `workflow_mode="multi_agent"` on the StartRunRequest.

All planning documents are in `maar/docs/` (docs 20-29).

**Two-command startup (unchanged from Phase 2):**

Windows PowerShell:
```powershell
# Terminal 1 — Backend
cd maar\backend; .venv\Scripts\Activate.ps1; uvicorn app.main:app --port 8000

# Terminal 2 — Frontend
cd maar\frontend; npm run dev
```

---

## Phase 2 Status (Prerequisite)

- [x] All Phase 2 milestones complete
- [x] 124/124 backend tests passing
- [x] `npm run build` passing
- [x] IBM watsonx.ai (Llama 3.3 70B) working with Tavily web search
- [x] Frontend client-side refactor complete (DashboardClient, ProjectsClient, WorkspaceClient)

---

## Phase 3 Milestones

---

### Milestone 1: Dependencies, Configuration, Database Migration

**Status**: [ ] pending

**Intent**
Install LangGraph 1.2.20, add Phase 3 env vars, extend existing ORM models with two new columns, create three new ORM models, and generate + apply the Alembic migration. This is the prerequisite for all other milestones.

**Relevant Documents**
- `docs/25_DATABASE_AND_PERSISTENCE_DESIGN.md` — full schema, ORM models, migration strategy
- `docs/26_BACKEND_IMPLEMENTATION_SPECIFICATION.md` — dependency list, config additions
- `docs/29_IMPLEMENTATION_ROADMAP_AND_DECISIONS.md` — ADR-201 (LangGraph pinning)

**Todo List**
1. Add `langgraph==1.2.20` and `langchain-core>=1.4.7,<2.0.0` to `requirements.txt`
2. Install in venv: `.venv\Scripts\pip install langgraph==1.2.20 "langchain-core>=1.4.7,<2.0.0"`
3. Verify: `python -c "import langgraph; print(langgraph.__version__)"`
4. Extract `_safe_error()` to `app/core/errors.py` as `safe_error_message(exc) -> str`
5. Add `MAX_SUPERVISOR_CYCLES: int = 3` and `CHECKPOINT_DB_URL: str = "./maar_checkpoints.db"` to `app/core/config.py`
6. Add both to `backend/.env.example`
7. Add `workflow_mode` column to `ResearchRun` ORM (`app/models/run.py`)
8. Add `task_id` nullable FK column to `EvidenceRecord` ORM (`app/models/evidence.py`)
9. Create `app/models/plan.py` — `ResearchPlan` ORM
10. Create `app/models/task.py` — `ResearchTask` ORM
11. Create `app/models/event.py` — `AgentExecutionEvent` ORM
12. Update `app/models/__init__.py` to import all new models
13. Update `app/main.py` `_recover_stuck_runs()` to also mark `research_tasks.status="running"` as `"failed"`
14. Generate migration: `alembic revision --autogenerate -m "phase3_multi_agent_schema"`
15. Apply migration: `alembic upgrade head`
16. Verify: `alembic downgrade -1` works cleanly
17. Run: `pytest tests/ -v` — all 124 tests must pass

**Expected Outcomes**
- LangGraph 1.2.20 importable
- `maar_dev.db` has 3 new tables and 2 new columns
- All 124 Phase 2 tests pass without modification

---

### Milestone 2: Shared State, Schemas, and Graph Skeleton

**Status**: [ ] pending

**Intent**
Define the typed shared state, all Pydantic schemas, routing functions, and a compilable graph skeleton with stub nodes. Establishes the architecture skeleton before any agent logic is written.

**Relevant Documents**
- `docs/22_LANGGRAPH_WORKFLOW_DESIGN.md` — full graph design, node list, routing
- `docs/23_SHARED_STATE_AND_COMMUNICATION.md` — state schema, reducers, field ownership
- `docs/24_AGENT_SPECIFICATIONS.md` — Pydantic schemas for SupervisorDecision, ResearchPlan, TaskResult

**Todo List**
1. Create `app/graph/__init__.py`
2. Create `app/graph/state.py` — `ResearchWorkflowState` TypedDict with all fields and `Annotated` reducers
3. Create `app/graph/checkpointer.py` — `get_checkpointer()` returning `SqliteSaver` from `CHECKPOINT_DB_URL`
4. Create `app/schemas/plan.py` — `ResearchTask`, `ResearchPlan`, `ResearchTaskResponse`, `ResearchPlanResponse`
5. Create `app/schemas/agent.py` — `SupervisorDecision`, `TaskResult`, `AgentEventResponse`, `AgentActivityResponse`
6. Create `app/graph/workflow.py` — stub nodes (pass-through lambda functions), full graph construction with all edges and routing functions, `get_research_graph()` singleton
7. Verify graph compiles: `python -c "from app.graph.workflow import get_research_graph; g = get_research_graph()"`
8. Run: `pytest tests/ -v` — all 124 tests pass

**Expected Outcomes**
- Graph compiles without error
- All Pydantic schemas validate with test data
- Routing functions are importable and callable

---

### Milestone 3: Phase 2 Tool Extraction and Service Modules

**Status**: [ ] pending

**Intent**
Create `app/agents/tools.py` with the three tool functions used by the Research Agent. Create `app/services/plan_service.py` and `app/services/event_service.py`. These wrap existing Phase 2 capabilities — no new research logic.

**Relevant Documents**
- `docs/24_AGENT_SPECIFICATIONS.md` — Section 3.2 (Research Agent tool permissions)
- `docs/25_DATABASE_AND_PERSISTENCE_DESIGN.md` — Section 5 (new service modules)
- `docs/26_BACKEND_IMPLEMENTATION_SPECIFICATION.md` — Section 3 (new service modules)

**Todo List**
1. Create `app/agents/__init__.py`
2. Create `app/agents/tools.py`:
   - `async web_search(query, search_provider, num_results) -> list[NormalizedEvidence]`
   - `async fetch_web_content(url, settings) -> NormalizedEvidence | None`
   - `async get_document_chunks(run_id, db) -> list[NormalizedEvidence]`
3. Create `app/services/plan_service.py`:
   - `save_plan(db, run_id, plan)` — creates ResearchPlan + ResearchTask rows
   - `get_latest_plan(db, run_id)` → ResearchPlan ORM | None
   - `get_tasks(db, run_id)` → list[ResearchTask ORM]
   - `update_task_status(db, task_id, status, **kwargs)` → None
4. Create `app/services/event_service.py`:
   - `log_event(db, run_id, agent_name, event_type, summary, ...)` → None
   - `get_events(db, run_id)` → list[AgentExecutionEvent ORM]
5. Write unit tests for tools.py (using MockWebSearchProvider, MockLLMProvider)
6. Write unit tests for plan_service.py and event_service.py (using test DB)
7. Run: `pytest tests/ -v` — all tests pass

**Expected Outcomes**
- `tools.web_search()` returns `list[NormalizedEvidence]` using MockWebSearchProvider
- SSRF guard (`is_safe_url`) blocks internal URLs
- `plan_service.save_plan()` creates correct DB rows
- `event_service.log_event()` creates AgentExecutionEvent rows

---

### Milestone 4: Research Planning Agent

**Status**: [ ] pending

**Intent**
Implement the `planning_node` with full LLM prompt, JSON parsing, validation, retry logic, deduplication, DB persistence, and event logging.

**Relevant Documents**
- `docs/24_AGENT_SPECIFICATIONS.md` — Section 2 (Research Planning Agent specification)
- `docs/22_LANGGRAPH_WORKFLOW_DESIGN.md` — Section 3.3 (planning_node behaviour)

**Todo List**
1. Create `app/agents/planner.py`
2. Implement `PLANNER_SYSTEM_PROMPT` (from doc 24 section 2.3)
3. Implement `planning_node(state, config)` async function:
   - First call vs. refinement call detection
   - Build user prompt
   - LLM call with one retry on invalid JSON
   - Validate `ResearchPlan` output (2-8 tasks)
   - Deduplicate tasks by objective
   - Call `plan_service.save_plan()`
   - Update `ResearchRun.current_stage = "Planning"`
   - Call `event_service.log_event()` for plan_created/plan_revised
   - Return state update
4. Register `planning_node` in `app/graph/workflow.py` (replace stub)
5. Add PA-001 through PA-008 tests to `tests/test_agents.py`
6. Run: `pytest tests/test_agents.py -v` — all planning tests pass
7. Run: `pytest tests/ -v` — all tests pass

**Expected Outcomes**
- planning_node produces valid ResearchPlan with 2-8 tasks
- Plan and tasks persisted to DB
- Retry logic handles invalid LLM JSON
- Task deduplication removes identical objectives

---

### Milestone 5: Research Agent

**Status**: [ ] pending

**Intent**
Implement the `research_node` with task execution, evidence collection, findings synthesis, evidence persistence, task status updates, and event logging.

**Relevant Documents**
- `docs/24_AGENT_SPECIFICATIONS.md` — Section 3 (Research Agent specification)
- `docs/22_LANGGRAPH_WORKFLOW_DESIGN.md` — Section 3.4 (research_node behaviour)

**Todo List**
1. Create `app/agents/researcher.py`
2. Implement `RESEARCHER_SYSTEM_PROMPT` (from doc 24 section 3.4)
3. Implement `research_node(state, config)` async function:
   - Identify current task from state
   - Mark task `running` via `task_service.update_task_status()`
   - Call `tools.web_search()`
   - Optionally call `tools.get_document_chunks()` if `use_documents=True`
   - Deduplicate evidence by URL / (document_id, chunk_index)
   - Persist `EvidenceRecord` rows with `task_id` FK
   - Call LLM for findings summary (2-3 sentences)
   - Build `TaskResult`
   - Mark task completed/partial/failed via `task_service.update_task_status()`
   - Call `event_service.log_event()`
   - Return state update (reducers append evidence_ids, task_results)
4. Register `research_node` in `app/graph/workflow.py` (replace stub)
5. Add RA-001 through RA-009 tests to `tests/test_agents.py`
6. Run: `pytest tests/test_agents.py -v` — all research tests pass
7. Run: `pytest tests/ -v` — all tests pass

**Expected Outcomes**
- research_node executes task and returns TaskResult
- EvidenceRecord rows have task_id FK set
- Failure modes return TaskResult without crashing the graph
- State reducers accumulate evidence_ids and task_results correctly

---

### Milestone 6: Supervisor Agent and Complete Graph

**Status**: [ ] pending

**Intent**
Implement the `supervisor_node`, deterministic nodes (`initialize_run`, `finalize_report`, `fail_workflow`), the `run_multi_agent_workflow()` executor, and the updated `runs.py` route. Complete the end-to-end graph.

**Relevant Documents**
- `docs/24_AGENT_SPECIFICATIONS.md` — Section 1 (Supervisor Agent specification)
- `docs/22_LANGGRAPH_WORKFLOW_DESIGN.md` — Sections 3.5, 3.6, 5 (deterministic nodes, loop control)
- `docs/26_BACKEND_IMPLEMENTATION_SPECIFICATION.md` — Sections 4, 5, 6 (routes, executor, error handling)

**Todo List**
1. Create `app/agents/supervisor.py` with `SUPERVISOR_SYSTEM_PROMPT` and `supervisor_node()`
2. Create `app/graph/nodes.py` with `initialize_run_node()`, `finalize_report_node()`, `fail_workflow_node()`
3. Create `app/graph/executor.py` with `run_multi_agent_workflow(run_id)` and `_mark_run_failed()`
4. Update `app/graph/workflow.py` — replace all stub nodes with real implementations
5. Add `workflow_mode: Literal["sequential", "multi_agent"] = "sequential"` to `StartRunRequest` in `app/schemas/run.py`
6. Update `app/api/v1/routes/runs.py` — add `workflow_mode` routing to background task selection
7. Add SA-001 through SA-009 tests to `tests/test_agents.py`
8. Create `tests/test_multi_agent_workflow.py` with GR-001 through GR-012 tests
9. Run: `pytest tests/test_agents.py tests/test_multi_agent_workflow.py -v` — all pass
10. Run: `pytest tests/ -v` — all 124 Phase 2 tests pass

**Expected Outcomes**
- Full graph executes end-to-end with mock agents
- GR-001 (happy path): run completes with report
- GR-004 (max iterations): workflow terminates correctly
- GR-012 (sequential workflow): Phase 2 path unaffected
- `POST /runs` with `workflow_mode="multi_agent"` triggers multi-agent graph

---

### Milestone 7: New API Endpoints

**Status**: [ ] pending

**Intent**
Implement and test the three new read-only API endpoints: `/plan`, `/tasks`, `/activity`.

**Relevant Documents**
- `docs/26_BACKEND_IMPLEMENTATION_SPECIFICATION.md` — Section 4 (new API endpoints)

**Todo List**
1. Add `GET /{project_id}/runs/{run_id}/plan` to `app/api/v1/routes/runs.py`
2. Add `GET /{project_id}/runs/{run_id}/tasks` to `app/api/v1/routes/runs.py`
3. Add `GET /{project_id}/runs/{run_id}/activity` to `app/api/v1/routes/runs.py`
4. Create `tests/test_phase3_api.py` with API-001 through API-009 tests
5. Run: `pytest tests/test_phase3_api.py -v` — all pass
6. Run: `pytest tests/ -v` — all tests pass
7. Verify: FastAPI `/docs` shows new endpoints with correct schemas

**Expected Outcomes**
- All three endpoints return correct response schemas
- 404 returned for sequential runs requesting `/plan` or `/tasks`
- All 124 Phase 2 API tests still pass

---

### Milestone 8: Frontend Phase 3 Components

**Status**: [ ] pending

**Intent**
Add workflow mode toggle to ResearchForm, implement three new components, update ResearchPanel routing, ensure backward compatibility for sequential runs.

**Relevant Documents**
- `docs/27_FRONTEND_MULTI_AGENT_EXPERIENCE.md` — complete frontend specification

**Todo List**
1. Add Phase 3 types to `src/lib/types/run.ts` (`ResearchTask`, `ResearchPlan`, `AgentEvent`, `AgentActivity`, `workflow_mode` to `ResearchRun`)
2. Add Phase 3 API functions to `src/lib/api/runs.ts` (`getPlan()`, `getTasks()`, `getActivity()`)
3. Add workflow mode toggle to `src/components/workspace/ResearchForm.tsx`
4. Create `src/components/workspace/MultiAgentStatusCard.tsx`
5. Create `src/components/workspace/ResearchPlanView.tsx`
6. Create `src/components/workspace/AgentActivityFeed.tsx`
7. Update `src/components/workspace/ResearchPanel.tsx` — route to Phase 3 components based on `workflow_mode`
8. Run: `npm run build` — must pass with zero TypeScript errors
9. Manual test: sequential run — verify no Phase 3 components visible
10. Manual test: multi-agent run — verify ResearchPlanView, AgentActivityFeed, MultiAgentStatusCard visible

**Expected Outcomes**
- `npm run build` passes with zero errors
- Phase 2 visual behaviour completely unchanged for sequential runs
- Phase 3 components render correctly for multi-agent runs

---

### Milestone 9: Integration Testing and E2E Validation

**Status**: [ ] pending

**Intent**
Run the full test suite, execute manual E2E scenarios with real API keys, verify the Phase 3 completion checklist.

**Relevant Documents**
- `docs/28_TESTING_EVALUATION_AND_OBSERVABILITY.md` — Sections 6 and 10

**Todo List**
1. Run: `pytest tests/ -v --tb=short` — all tests pass
2. Start backend and frontend with real API keys
3. Execute E2E scenario from doc 28 section 6 (mock providers first, then real)
4. Verify all items in doc 28 section 10 completion checklist
5. Check `maar_checkpoints.db` contains checkpoint entries for the run
6. Check `agent_execution_events` table has correct event sequence
7. Verify `GET /runs/{id}/activity` returns events in frontend AgentActivityFeed
8. Verify completed multi-agent run shows ResearchReport in frontend
9. Fix any issues found and re-run test suite
10. Update this plan file: mark all milestones `[x] done`
11. Update `maar-phase3-plan.md` status to `✅ Phase 3 Complete`

**Expected Outcomes**
- All automated tests pass (target: 170+ total)
- Full multi-agent E2E workflow completes successfully with real API keys
- Frontend displays plan, tasks, activity, and report correctly

---

## Phase 3 Completion Gate

Before Phase 3 is declared complete, all items in `docs/28_TESTING_EVALUATION_AND_OBSERVABILITY.md` Section 10 must be checked off, and all milestones above must be `[x] done`.

---

## Notes for Agent Mode Implementation

- Implement milestones sequentially: 1 → (2 and 3 in parallel) → 4 → 5 → 6 → 7 → 8 → 9
- After completing each milestone, update its **Status** to `[x] done` in this file
- After each milestone, run `pytest tests/ -v` to verify all Phase 2 tests still pass
- Do not modify `app/services/research_workflow.py` at any point
- Do not modify `app/providers/llm.py` or `app/providers/web_search.py`
- All new agent prompts must include the prompt injection defence statement
- Read the relevant planning docs before implementing each milestone
