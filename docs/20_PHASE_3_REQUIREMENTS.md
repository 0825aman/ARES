# 20 — Phase 3 Requirements

**Project**: Multi-Agent Autonomous Researcher (MAAR)
**Phase**: 3 — Multi-Agent Research Architecture
**Status**: Draft — Awaiting Approval

---

## 1. Overview and Objectives

Phase 3 replaces the monolithic sequential research pipeline introduced in Phase 2 with a genuine multi-agent architecture orchestrated by LangGraph. Three specialized agents — Supervisor, Research Planning, and Research — cooperate through a structured shared state to plan, execute, evaluate, and finalize research workflows.

**Primary objectives:**
- Introduce LangGraph as the orchestration layer for the research workflow.
- Create a Supervisor Agent that coordinates workflow decisions without performing research itself.
- Create a Research Planning Agent that decomposes complex research questions into structured, executable tasks.
- Create a Research Agent that executes individual tasks using existing Phase 2 tools.
- Preserve all Phase 1 and Phase 2 API contracts and frontend behaviour.
- Establish the foundation for parallel task execution and additional agents in Phase 4.

---

## 2. Scope — What Is In Phase 3

| Area | Included |
|---|---|
| LangGraph StateGraph orchestration | ✅ |
| Supervisor Agent with structured routing decisions | ✅ |
| Research Planning Agent with Pydantic plan schema | ✅ |
| Research Agent reusing Phase 2 tools | ✅ |
| Shared typed state with reducers | ✅ |
| Sequential task execution (one task at a time) | ✅ |
| SQLite LangGraph checkpointer | ✅ |
| New DB tables: ResearchPlan, ResearchTask, AgentExecutionEvent | ✅ |
| Alembic migration for new tables | ✅ |
| API: `workflow_mode` field on StartRunRequest | ✅ |
| API: new endpoints for plan and task status | ✅ |
| Frontend: agent activity display, task progress | ✅ |
| Bounded loop control (max iterations) | ✅ |
| Startup recovery for interrupted multi-agent runs | ✅ |
| Structured logging of agent decisions | ✅ |
| All existing Phase 2 tests continue to pass | ✅ |

---

## 3. User Stories

**US-001** — As a researcher, I can submit a complex research question and have the system automatically decompose it into structured sub-questions so that I receive more thorough, multi-dimensional findings than a single-query search provides.

**US-002** — As a researcher, I can see the generated research plan (objectives and tasks) in my workspace so that I understand what the system is investigating.

**US-003** — As a researcher, I can monitor which agent is currently active and what task it is executing, so I understand the workflow's progress.

**US-004** — As a researcher, I can see which research tasks have completed, are pending, or have failed, so I can evaluate the quality of the evidence collection.

**US-005** — As a researcher, I can view the final consolidated report even when some individual tasks returned partial evidence, so the workflow produces a result rather than total failure.

**US-006** — As a developer, I can inspect the Supervisor's routing decisions in structured logs so I can debug why a particular agent was chosen or why additional research was requested.

**US-007** — As a developer, I can run all Phase 3 tests without real API keys or external network access, so the test suite runs reliably in CI.

**US-008** — As a developer, I can recover an interrupted multi-agent run after a backend restart, so partially-completed workflows are not silently lost.

**US-009** — As a researcher, I can continue using the existing simple research workflow (Phase 2 mode) for straightforward questions, so Phase 3 does not force multi-agent overhead on every run.

**US-010** — As an operator, I can configure the maximum number of Supervisor evaluation cycles so the system does not loop indefinitely on difficult questions.

---

## 4. Functional Requirements

### FR-001 — LangGraph Integration
The system MUST use LangGraph 1.2.x (`StateGraph`) to orchestrate the multi-agent research workflow. No custom message-passing or agent coordination layer shall be implemented instead.

### FR-002 — Workflow Mode Selection
`POST /api/v1/projects/{id}/runs` MUST accept an optional `workflow_mode` field with values `"sequential"` (Phase 2 default) and `"multi_agent"`. When `"sequential"` is selected, the existing Phase 2 `run_research_workflow` executes unchanged.

### FR-003 — Supervisor Agent
The Supervisor Agent MUST produce one of the following structured routing decisions after each evaluation cycle:
- `request_plan` — initial delegation to Planning Agent
- `accept_plan` — plan is adequate; begin task execution
- `revise_plan` — plan is incomplete; return to Planning Agent with revision notes
- `execute_next_task` — assign the next pending task to Research Agent
- `request_additional_research` — submit a supplementary task to Research Agent
- `complete_research` — research is sufficiently complete; proceed to report generation
- `fail_workflow` — unrecoverable error; terminate with error state

The Supervisor MUST NOT call web search, document extraction, or LLM synthesis tools directly.

### FR-004 — Bounded Execution
The graph MUST enforce a `max_supervisor_cycles` limit (default: 3, configurable via `.env`). When `iteration_count >= max_supervisor_cycles`, the Supervisor MUST be forced to `complete_research` regardless of its assessment.

### FR-005 — Research Planning Agent
The Planning Agent MUST produce a `ResearchPlan` Pydantic model containing between 2 and 8 `ResearchTask` objects. Each task MUST have: `task_id` (stable UUID), `objective` (string), `search_query` (string), `expected_evidence_type` (string), `priority` (int 1-3).

### FR-006 — Plan Refinement
When the Supervisor returns `revise_plan`, the Planning Agent MUST receive the original plan plus the Supervisor's `revision_notes` string and produce a refined plan. Plan refinement MUST be capped at 2 cycles.

### FR-007 — Research Agent Tool Permissions
The Research Agent MUST have access to ONLY these Phase 2 tools:
- `web_search(query, num_results)` — wraps `TavilySearchProvider.search()`
- `fetch_web_content(url)` — wraps `is_safe_url()` + `fetch_url()`
- `get_document_chunks(run_id)` — retrieves pre-extracted document evidence from DB

The Research Agent MUST NOT call `generate_report()`, `LLMProvider.complete()` for synthesis, or any database write operations outside of evidence persistence.

### FR-008 — Evidence Persistence
For each task executed by the Research Agent, collected evidence MUST be persisted to `evidence_records` table with `task_id` as an additional foreign key reference (new column). Evidence IDs (not content) are stored in the LangGraph state.

### FR-009 — Task Persistence
All `ResearchTask` objects MUST be persisted to a new `research_tasks` table with status tracking (`pending`, `running`, `completed`, `failed`). The frontend can query task status independently.

### FR-010 — Plan Persistence
The `ResearchPlan` MUST be persisted to a new `research_plans` table linked to `research_runs.id`. The frontend can retrieve the plan to display research objectives.

### FR-011 — Agent Event Logging
Each significant agent action MUST be recorded as an `AgentExecutionEvent` row: agent name, event type, summary, input reference, output reference, timestamp. This table is the primary observability record.

### FR-012 — Report Generation
When the Supervisor decides `complete_research`, the existing `generate_report()` function from Phase 2 MUST be called with ALL evidence collected across all tasks. The existing `ResearchReport` table is unchanged.

### FR-013 — Startup Recovery
On backend startup, ResearchRuns with `status="running"` or `status="pending"` and `workflow_mode="multi_agent"` MUST be marked `failed` with message "Server restart during multi-agent workflow." LangGraph checkpoint data is preserved for potential future resume.

### FR-014 — Existing API Preservation
All Phase 2 API endpoints MUST continue to function without modification. No breaking changes to existing request/response schemas.

### FR-015 — Checkpointing
LangGraph checkpoint state MUST be persisted using `SqliteSaver` to `maar_checkpoints.db` (separate file from `maar_dev.db`). Thread ID = `run_id`.

---

## 5. Non-Functional Requirements

**NFR-001 — Testability**: All agent logic MUST be testable with mock LLM and search providers. No test shall require paid API keys.

**NFR-002 — Observability**: Every Supervisor routing decision MUST be logged at INFO level with a structured JSON payload containing: `run_id`, `decision`, `iteration_count`, `reason`.

**NFR-003 — Safety**: The graph `recursion_limit` MUST be set to 25. Any graph execution that exceeds this limit MUST be treated as a workflow failure.

**NFR-004 — Reliability**: A failure of any single ResearchTask MUST NOT terminate the entire workflow. The Supervisor MUST evaluate available evidence and decide whether to proceed or request remediation.

**NFR-005 — SQLite Compatibility**: All new ORM models MUST remain SQLite-compatible (no PostgreSQL-only features). Alembic `render_as_batch=True` already configured.

**NFR-006 — Backwards Compatibility**: Phase 2 `sequential` workflow mode MUST continue to work identically after Phase 3 is deployed.

**NFR-007 — Windows Dev Environment**: All setup instructions and commands MUST use PowerShell syntax compatible with Windows 10/11.

---

## 6. Explicit Exclusions

The following are explicitly NOT in Phase 3:

| Excluded Capability | Rationale |
|---|---|
| Parallel task execution | Increases complexity significantly; deferred to Phase 4 |
| Vector database (Qdrant) | Not required for task-based evidence search |
| WebSocket streaming | Polling is sufficient for Phase 3 |
| Human-in-the-loop approval | LangGraph `interrupt_before` will be wired but not exposed in UI |
| Multi-model agents (different LLM per agent) | All agents share one LLM provider; separate configs deferred |
| LangSmith cloud tracing | Optional; structured DB logging is the primary observability layer |
| Agent memory across runs | Each run starts with a fresh state |
| Retrieval-Augmented Generation (RAG) | Deferred to Phase 4 |
| User authentication | Out of scope for Phase 3 |
| Docker / containerisation | Development-only local setup |
| Replacement of Phase 2 sequential workflow | `sequential` mode remains the default |

---

## 7. Phase 2 Compatibility Requirements

- `run_research_workflow()` in `app/services/research_workflow.py` MUST NOT be modified.
- `TavilySearchProvider`, `WatsonxProvider`, `OpenAIProvider`, `MockLLMProvider`, `MockWebSearchProvider` MUST NOT be modified.
- `evidence_normalizer.py`, `context_builder.py`, `report_generator.py` MUST be callable from both Phase 2 and Phase 3 paths.
- All 124 existing tests MUST continue to pass after Phase 3 code is introduced.
- The `POST /api/v1/projects/{id}/runs` endpoint MUST default to `workflow_mode="sequential"` so existing behaviour is unchanged.

---

## 8. Assumptions and Constraints

1. LangGraph 1.2.20 is used. API behaviour may differ from earlier versions — implementation MUST be based on 1.2.x documentation.
2. IBM watsonx.ai `meta-llama/llama-3-3-70b-instruct` is the current LLM. All three agents share this provider.
3. Structured output from LLM agents is achieved via prompt-constrained JSON — not via LangChain tool-calling wrappers (which would require `langchain-openai` or similar). The existing `LLMProvider.complete(system_prompt, user_prompt)` interface is preserved.
4. SQLite is the only database for Phase 3. PostgreSQL migration is deferred.
5. The LangGraph `SqliteSaver` checkpointer is synchronous. It will be called from a sync wrapper within the async FastAPI background task.
6. Task count per plan is bounded to 8 to prevent runaway API costs.

---

## 9. Acceptance Gates

Phase 3 is complete when all of the following are true:

- [ ] All 124 Phase 2 tests pass without modification.
- [ ] New Phase 3 test suite passes with mock providers (target: ≥ 40 new tests).
- [ ] `POST /api/v1/projects/{id}/runs` with `workflow_mode="multi_agent"` creates a run, triggers the LangGraph graph, and returns 201 immediately.
- [ ] A research plan with at least 3 tasks is persisted to `research_plans` table.
- [ ] All tasks are persisted to `research_tasks` table with correct status transitions.
- [ ] Agent execution events are written to `agent_execution_events` table.
- [ ] The Supervisor's `complete_research` decision triggers `generate_report()` and produces a `ResearchReport`.
- [ ] When `iteration_count >= max_supervisor_cycles`, the workflow terminates without an infinite loop.
- [ ] `npm run build` passes with zero errors after frontend Phase 3 changes.
- [ ] The workspace UI displays the research plan, task list, and agent activity.
- [ ] The full E2E scenario in section 14 of the specification passes manually.
