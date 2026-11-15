# 29 — Implementation Roadmap and Decisions

**Project**: Multi-Agent Autonomous Researcher (MAAR)
**Phase**: 3
**Status**: Draft — Awaiting Approval

---

## 1. Implementation Sequence

Phase 3 is implemented in 8 milestones. Each milestone is independently testable and must pass its acceptance criteria before the next begins. Milestones 2 and 3 can be developed in parallel since they have no interdependency.

```
Milestone 1: Dependencies, Configuration, Database Migration
    │
Milestone 2: Shared State, Schemas, and Graph Skeleton
    │
Milestone 3: Phase 2 Tool Extraction (parallel with M2)
    │
Milestone 4: Research Planning Agent
    │
Milestone 5: Research Agent
    │
Milestone 6: Supervisor Agent and Complete Graph
    │
Milestone 7: Persistence Layer and New API Endpoints
    │
Milestone 8: Frontend Phase 3 Components
    │
Milestone 9: Integration Testing and E2E Validation
```

---

## 2. Milestone Specifications

---

### Milestone 1: Dependencies, Configuration, Database Migration

**Status**: [ ] pending

**Scope**: Install LangGraph, add new env vars, create Phase 3 Alembic migration, extend existing ORM models.

**Files affected**:
- `requirements.txt` — add `langgraph==1.2.20`, `langchain-core>=1.4.7,<2.0.0`
- `app/core/config.py` — add `MAX_SUPERVISOR_CYCLES`, `CHECKPOINT_DB_URL`
- `app/core/errors.py` — extract `safe_error_message()` from `research_workflow.py`
- `app/models/run.py` — add `workflow_mode` column, new relationships
- `app/models/evidence.py` — add `task_id` column, new relationship
- `app/models/plan.py` — new ResearchPlan ORM
- `app/models/task.py` — new ResearchTask ORM
- `app/models/event.py` — new AgentExecutionEvent ORM
- `app/models/__init__.py` — import new models
- `app/main.py` — extend recovery to mark stuck tasks as failed
- `alembic/versions/XXX_phase3_multi_agent_schema.py` — new migration
- `backend/.env.example` — document new env vars

**Dependencies**: None (this is the prerequisite for all other milestones)

**Deliverables**:
- LangGraph installed and importable in venv
- `alembic upgrade head` creates all 3 new tables and 2 new columns
- `alembic downgrade -1` works cleanly
- All 124 Phase 2 tests still pass

**Acceptance criteria**:
- [ ] `python -c "import langgraph; print(langgraph.__version__)"` prints `1.2.20`
- [ ] `alembic upgrade head` completes without error on fresh and existing databases
- [ ] `pytest tests/ -v` — all 124 tests pass

---

### Milestone 2: Shared State, Schemas, and Graph Skeleton

**Status**: [ ] pending

**Scope**: Create typed state, all Pydantic schemas, routing functions, and a compilable (but non-functional) graph skeleton.

**Files created**:
- `app/graph/__init__.py`
- `app/graph/state.py` — `ResearchWorkflowState` TypedDict + reducers
- `app/graph/workflow.py` — StateGraph skeleton (stub nodes)
- `app/graph/checkpointer.py` — `get_checkpointer()` factory
- `app/schemas/plan.py` — `ResearchPlan`, `ResearchTask`, `ResearchPlanResponse`, `ResearchTaskResponse`
- `app/schemas/agent.py` — `SupervisorDecision`, `TaskResult`, `AgentEventResponse`, `AgentActivityResponse`

**Dependencies**: Milestone 1

**Deliverables**:
- Graph compiles without error
- State TypedDict passes pyright/mypy type checking
- All Pydantic schemas validate correctly with test data

**Acceptance criteria**:
- [ ] `from app.graph.workflow import get_research_graph; g = get_research_graph()` executes without error
- [ ] `SupervisorDecision(decision="request_plan", reasoning="test")` validates
- [ ] `ResearchPlan` with 3 `ResearchTask` objects validates
- [ ] All 124 Phase 2 tests still pass

---

### Milestone 3: Phase 2 Tool Extraction (parallel with M2)

**Status**: [ ] pending

**Scope**: Extract Phase 2 research capabilities into reusable tool functions in `app/agents/tools.py`. No new logic — pure extraction and wrapping.

**Files created**:
- `app/agents/__init__.py`
- `app/agents/tools.py` — `web_search()`, `fetch_web_content()`, `get_document_chunks()`

**Files created**:
- `app/services/plan_service.py` — `save_plan()`, `get_latest_plan()`, `get_tasks()`, `update_task_status()`
- `app/services/event_service.py` — `log_event()`, `get_events()`

**IMPORTANT**: `app/services/research_workflow.py` is NOT modified. The internal functions `_web_research()` and `_extract_documents()` are NOT extracted from it. Instead, `tools.py` re-implements the same logic cleanly by calling the same underlying Phase 2 providers and normalizers.

**Dependencies**: Milestone 1

**Deliverables**:
- `tools.py` functions callable independently with mock providers
- `plan_service.py` creates correct DB records
- `event_service.py` creates correct DB records
- Unit tests for all tool functions

**Acceptance criteria**:
- [ ] `await tools.web_search("test query", MockWebSearchProvider())` returns `list[NormalizedEvidence]`
- [ ] `tools.web_search()` calls `is_safe_url()` and skips blocked URLs
- [ ] `plan_service.save_plan()` creates ResearchPlan + ResearchTask rows in test DB
- [ ] All 124 Phase 2 tests still pass

---

### Milestone 4: Research Planning Agent

**Status**: [ ] pending

**Scope**: Implement `planning_node` with full prompt, JSON parsing, validation, retry logic, and DB persistence.

**Files created**:
- `app/agents/planner.py`

**Files affected**:
- `tests/test_agents.py` — PA-001 through PA-008 test cases

**Dependencies**: Milestones 2, 3

**Deliverables**:
- `planning_node` returns a valid state update with a ResearchPlan
- Plan is persisted to `research_plans` and `research_tasks` tables
- Retry logic handles invalid LLM JSON output
- `AgentExecutionEvent` row created on plan creation

**Acceptance criteria**:
- [ ] All PA-001–PA-008 tests pass with MockLLMProvider
- [ ] `research_plans` and `research_tasks` rows created in test DB
- [ ] Refinement call (with existing plan + revision_notes) produces updated plan
- [ ] Task deduplication removes identical objectives
- [ ] Planning node failure sets `workflow_status="failed"`

---

### Milestone 5: Research Agent

**Status**: [ ] pending

**Scope**: Implement `research_node` with task execution, evidence collection, findings synthesis, and DB persistence.

**Files created**:
- `app/agents/researcher.py`

**Files affected**:
- `tests/test_agents.py` — RA-001 through RA-009 test cases

**Dependencies**: Milestones 2, 3

**Deliverables**:
- `research_node` executes a single task and returns `TaskResult`
- Evidence persisted to `evidence_records` with `task_id` FK
- Task status updated in `research_tasks`
- `AgentExecutionEvent` rows created for task start and completion
- All tool failure modes handled correctly

**Acceptance criteria**:
- [ ] All RA-001–RA-009 tests pass with MockWebSearchProvider
- [ ] `evidence_records.task_id` populated correctly
- [ ] `research_tasks.status` transitions correctly
- [ ] Zero evidence case returns `TaskResult(status="failed")` without crashing
- [ ] DB insert failure returns `TaskResult(status="fatal_error")`

---

### Milestone 6: Supervisor Agent and Complete Graph

**Status**: [ ] pending

**Scope**: Implement `supervisor_node`, connect all nodes in the graph, implement routing functions, implement deterministic nodes (`initialize_run`, `finalize_report`, `fail_workflow`), implement `run_multi_agent_workflow()` executor.

**Files created**:
- `app/agents/supervisor.py`
- `app/graph/nodes.py`
- `app/graph/executor.py`

**Files modified**:
- `app/graph/workflow.py` — replace stub nodes with real implementations
- `app/api/v1/routes/runs.py` — add `workflow_mode` routing
- `app/schemas/run.py` — add `workflow_mode` to `StartRunRequest`
- `app/models/run.py` — add `workflow_mode` column

**Files created**:
- `tests/test_multi_agent_workflow.py` — GR-001 through GR-012 test cases

**Dependencies**: Milestones 4, 5

**Deliverables**:
- Full graph executes end-to-end with mock agents
- Supervisor routing decisions correctly dispatch to planning and research nodes
- Max iterations enforcement works
- Graph recursion_limit respected
- `finalize_report` calls Phase 2 `generate_report()` and persists report

**Acceptance criteria**:
- [ ] GR-001 (happy path) passes with mock agents
- [ ] GR-004 (max iterations) terminates correctly
- [ ] GR-011 (startup recovery) correctly marks stuck runs failed
- [ ] GR-012 (sequential workflow unaffected) passes
- [ ] `POST /api/v1/projects/{id}/runs` with `workflow_mode="multi_agent"` returns 201
- [ ] All 124 Phase 2 tests still pass

---

### Milestone 7: New API Endpoints

**Status**: [ ] pending

**Scope**: Implement and test the three new API endpoints: `/plan`, `/tasks`, `/activity`.

**Files modified**:
- `app/api/v1/routes/runs.py` — add GET /plan, GET /tasks, GET /activity

**Files created**:
- `tests/test_phase3_api.py` — API-001 through API-009 test cases

**Dependencies**: Milestone 6

**Deliverables**:
- All three new endpoints return correct response schemas
- Error cases (run not found, plan not yet created) return correct 404 responses
- Sequential runs return 404 for `/plan` and `/tasks` endpoints

**Acceptance criteria**:
- [ ] All API-001–API-009 tests pass
- [ ] All 124 Phase 2 tests still pass
- [ ] FastAPI docs at `/docs` show new endpoints with correct schemas

---

### Milestone 8: Frontend Phase 3 Components

**Status**: [ ] pending

**Scope**: Implement all frontend changes: new types, API functions, and four new/modified components.

**Files modified**:
- `src/lib/types/run.ts` — new types
- `src/lib/api/runs.ts` — new API functions
- `src/components/workspace/ResearchForm.tsx` — workflow mode toggle
- `src/components/workspace/ResearchPanel.tsx` — routing for multi-agent runs

**Files created**:
- `src/components/workspace/MultiAgentStatusCard.tsx`
- `src/components/workspace/ResearchPlanView.tsx`
- `src/components/workspace/AgentActivityFeed.tsx`

**Dependencies**: Milestone 7

**Deliverables**:
- `npm run build` passes with zero errors
- Workflow mode toggle visible in ResearchForm
- MultiAgentStatusCard renders with correct active agent and task progress
- ResearchPlanView shows objectives and task list with status badges
- AgentActivityFeed renders events in expandable section

**Acceptance criteria**:
- [ ] `npm run build` passes with zero TypeScript errors
- [ ] Sequential run (`workflow_mode="sequential"`) shows no Phase 3 components
- [ ] Multi-agent run shows ResearchPlanView and AgentActivityFeed
- [ ] Task status updates visible during polling
- [ ] Completed run shows ResearchReportView (unchanged from Phase 2)

---

### Milestone 9: Integration Testing and E2E Validation

**Status**: [ ] pending

**Scope**: Run full test suite, execute manual E2E scenarios with real API keys, verify checklist from doc 28.

**Dependencies**: Milestone 8

**Deliverables**:
- All automated tests pass (target: 170+ total tests)
- E2E scenario from doc 28 section 6 verified manually
- All checklist items in doc 28 section 10 checked

**Acceptance criteria**:
- [ ] `pytest tests/ -v` — all tests pass (124 Phase 2 + Phase 3 new tests)
- [ ] Real watsonx.ai + Tavily run produces a multi-agent report
- [ ] All items in doc 28 completion checklist checked

---

## 3. Technical Decisions

### ADR-201: LangGraph 1.2.20 — Pinned Version

**Decision**: Pin `langgraph==1.2.20` exactly.

**Rationale**: LangGraph has frequent breaking changes across minor versions. Pinning prevents accidental upgrades during `pip install --upgrade`. The dry-run confirmed full compatibility with Python 3.14.5 and Pydantic 2.14.3.

**Trade-off**: Must explicitly update the pin when upgrading. Acceptable for a controlled development environment.

---

### ADR-202: Sequential Task Execution in Phase 3

**Decision**: Execute one research task at a time (sequential).

**Rationale**: Parallel execution using LangGraph's `Send()` API introduces DB transaction complexity (concurrent EvidenceRecord inserts), API rate limit risk (watsonx.ai and Tavily), and harder-to-debug state. Sequential execution is sufficient to validate the multi-agent architecture.

**Path forward**: Phase 4 can introduce `Send()` for task fan-out without changing the agent implementations — only `workflow.py` changes.

---

### ADR-203: Structured Output via Prompt JSON (not tool-calling API)

**Decision**: All agent structured outputs use LLM-generated JSON parsed with the existing `_parse_llm_response()` function, not LangChain's `with_structured_output()` or OpenAI function-calling.

**Rationale**: The existing `LLMProvider.complete(system_prompt, user_prompt)` interface works with watsonx.ai which does not support OpenAI's function-calling API. Using prompt-based JSON is provider-agnostic. The existing JSON parser already handles code fences and malformed responses.

**Trade-off**: Less strict than schema-enforced tool calling. Mitigated by: explicit JSON schema in prompts, Pydantic validation, retry logic.

---

### ADR-204: Single LLM Provider for All Agents

**Decision**: All three agents share the same `LLMProvider` instance.

**Rationale**: Using one provider for Supervisor, Planner, and Researcher simplifies configuration significantly. The hypothesis that different agents need different models is untested. Shared provider eliminates additional API key management.

**Path forward**: `app/core/config.py` will include `SUPERVISOR_MODEL`, `PLANNER_MODEL`, `RESEARCHER_MODEL` as empty strings (defaulting to `LLM_MODEL`) so Phase 4 can easily enable per-agent model configuration.

---

### ADR-205: SqliteSaver for LangGraph Checkpointing

**Decision**: Use `langgraph.checkpoint.sqlite.SqliteSaver` backed by `maar_checkpoints.db`.

**Rationale**: No additional infrastructure required. Consistent with SQLite-first development approach. The sync/async compatibility issue is handled by LangGraph's internal adapter in `graph.ainvoke()`.

**Path forward**: Can be swapped for `AsyncPostgresSaver` in Phase 4 when PostgreSQL is introduced. Only `checkpointer.py` changes.

---

### ADR-206: Phase 2 Workflow Preserved as Default

**Decision**: `workflow_mode` defaults to `"sequential"`. The `run_research_workflow()` function is completely unchanged.

**Rationale**: Phase 3 introduces new complexity. Keeping Phase 2 as the default protects against regressions and allows users to fall back to the proven path. The multi-agent workflow is an opt-in for Phase 3.

---

### ADR-207: No Direct Extraction of Phase 2 Internal Functions

**Decision**: The internal functions `_web_research()` and `_extract_documents()` in `research_workflow.py` are NOT extracted. `app/agents/tools.py` re-implements equivalent logic by calling the same underlying providers and normalizers.

**Rationale**: `research_workflow.py` is a tested, working module. Extracting its internals risks breaking Phase 2 tests. The tool functions call the same `TavilySearchProvider`, `fetch_url()`, `normalize_web_result()`, and `normalize_document_chunk()` primitives — they are functionally identical but structurally independent.

---

### ADR-208: Confirmed Configuration Defaults

**Decision**: The following defaults are confirmed after owner review (2026-11-11):

| Parameter | Default | Rationale |
|---|---|---|
| `workflow_mode` in ResearchForm | `"sequential"` | Preserves Phase 2 as the primary user path; multi-agent is opt-in |
| `MAX_SUPERVISOR_CYCLES` | `3` | Balances thoroughness vs. cost; sufficient for most research questions |
| Task count range (Planning Agent) | 2–8 | Broad enough to handle complex questions; bounded to control cost |
| Plan review gate (human-in-the-loop) | Deferred to Phase 4 | `interrupt_before=[]` in graph compilation; infrastructure ready, not exposed |

All defaults are configurable via environment variables or UI controls. No hardcoded values.

---

### ADR-209: LangSmith as a Zero-Code Optional Integration

**Decision**: LangSmith tracing is supported from Phase 3 but requires zero application code changes to enable or disable. It is activated exclusively through standard LangChain environment variables (`LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`).

**Mechanism**:
- `langsmith` is installed automatically as a transitive dependency of `langchain-core` (already required by LangGraph)
- LangGraph 1.2.x reads `LANGCHAIN_TRACING_V2` at runtime via the `langsmith` library's callback system
- When the env var is absent or `false`, the `langsmith` library is loaded but remains dormant — no network calls, no errors
- MAAR application code NEVER imports `langsmith` directly
- `LANGCHAIN_*` variables are NOT added to pydantic-settings `Settings` class — they are OS env vars only

**Requirements satisfied**:

| Requirement | How satisfied |
|---|---|
| Works completely without LangSmith account | ✅ — env vars absent = no tracing, no errors |
| Structured local logging always on | ✅ — `configure_logging()` + node entry/exit logs + `AgentExecutionEvent` DB table |
| Configurable through env vars | ✅ — standard `LANGCHAIN_*` vars in `.env` |
| Compatible LangGraph nodes traced when enabled | ✅ — LangGraph's internal callback hooks handle this |
| No hardcoded credentials | ✅ — keys only in `.env` (gitignored) |
| Privacy controls documented | ✅ — `LANGCHAIN_HIDE_INPUTS=true` documented in doc 28 |
| No code changes after initial integration | ✅ — toggle is purely `.env` file change + restart |
| Not a runtime dependency for research execution | ✅ — `langsmith` is passive when tracing is disabled |

**Trade-off**: LLM calls via `LLMProvider.complete()` are not auto-traced by LangSmith in Phase 3 (since they bypass LangChain's Runnable system). Local structured logging covers this gap. Full LLM tracing can be enabled in Phase 4 by wrapping `LLMProvider` in a LangChain `Runnable`.

**`.env.example` entry**:
```ini
# ─── LangSmith Observability (optional — remove or leave blank to disable) ────
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY=ls__your_key_here
# LANGCHAIN_PROJECT=maar-phase3
# LANGCHAIN_HIDE_INPUTS=true
```

Full setup instructions: `docs/28_TESTING_EVALUATION_AND_OBSERVABILITY.md` Section 7.

---

## 4. Deferred Capabilities

| Capability | Reason deferred | When to revisit |
|---|---|---|
| Parallel task execution (Send API) | Complexity risk in Phase 3 | Phase 4 after validating sequential multi-agent |
| Human-in-the-loop plan approval | Infrastructure ready; UI complexity | Phase 4: change `interrupt_before=[]` to `["research_node"]` |
| Per-agent LLM model configuration | Untested need | Phase 4: add SUPERVISOR_MODEL/PLANNER_MODEL/RESEARCHER_MODEL config vars |
| Full LLM call tracing in LangSmith | Requires LangChain Runnable wrapper | Phase 4: wrap LLMProvider in Runnable |
| Vector database (RAG) | Requires Qdrant + embeddings | Phase 4 |
| Automatic checkpoint resumption | Risk of stale state | Phase 4 after checkpointing is battle-tested |
| WebSocket streaming agent activity | Polling is sufficient | Phase 4 if latency becomes a UX issue |
| Agent memory across runs | Cross-run context | Phase 4 |

---

## 5. Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| LangGraph 1.2.x API is different from documentation | Medium | High | Read official 1.2.x docs; pin version; test compilation in Milestone 1 |
| watsonx.ai rate limits under multi-agent LLM calls | Medium | Medium | Sequential execution; existing retry logic; `LLM_TIMEOUT_SECONDS` setting |
| SqliteSaver incompatibility with Python 3.14 | Low | High | Verify in Milestone 1 via import test; have fallback plan (InMemorySaver) |
| LLM produces invalid JSON for structured decisions | High | Low | Pydantic validation + fallback defaults in all agents |
| Supervisor loops indefinitely | Low | High | `max_supervisor_cycles` hard limit + `recursion_limit=25` |
| Alembic migration fails on existing database | Low | Medium | Test migration on copy of `maar_dev.db` before applying to production |
| Frontend TypeScript errors after adding new types | Medium | Low | Run `npm run build` after each component; strict typing throughout |
| Research tasks duplicate Phase 2 evidence | Low | Low | Task-level deduplication; `append_unique` reducer in state |
