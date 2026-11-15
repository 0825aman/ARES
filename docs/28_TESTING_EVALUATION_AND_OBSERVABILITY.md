# 28 — Testing, Evaluation and Observability

**Project**: Multi-Agent Autonomous Researcher (MAAR)
**Phase**: 3
**Status**: Draft — Awaiting Approval

---

## 1. Test Architecture

All Phase 3 tests use the same infrastructure as Phase 2:
- `pytest` + `pytest-asyncio` (function-scoped fixtures)
- In-memory SQLite test database (`sqlite+aiosqlite:///:memory:`)
- FastAPI `AsyncClient` for HTTP tests
- Mock providers via dependency override (existing `MockLLMProvider`, `MockWebSearchProvider`)
- No real API keys required for any automated test

New test files:
- `tests/test_agents.py` — individual agent node tests
- `tests/test_multi_agent_workflow.py` — full graph tests
- `tests/test_phase3_api.py` — new API endpoint tests

All 124 Phase 2 tests must continue to pass unchanged.

---

## 2. Mock Agents for Graph Testing

Phase 3 introduces mock agent functions for graph-level testing that do not call the LLM:

```python
# tests/mocks.py (additions)

class MockSupervisorAgent:
    """Deterministic supervisor for graph testing."""
    def __init__(self, decisions: list[str]):
        self._decisions = iter(decisions)

    async def __call__(self, state, config):
        decision = next(self._decisions, "complete_research")
        return {
            "supervisor_decision": decision,
            "iteration_count": state["iteration_count"] + 1,
            "revision_notes": "Add more tasks" if decision == "revise_plan" else None,
        }

class MockPlannerAgent:
    """Returns a deterministic research plan."""
    async def __call__(self, state, config):
        plan = ResearchPlan(
            plan_id=str(uuid.uuid4()),
            objectives=["Understand topic A", "Investigate aspect B"],
            tasks=[
                ResearchTask(task_id=str(uuid.uuid4()), objective="Task 1",
                             search_query="query one", priority=1, ...),
                ResearchTask(task_id=str(uuid.uuid4()), objective="Task 2",
                             search_query="query two", priority=2, ...),
            ],
        )
        return {
            "research_plan": plan.model_dump(),
            "research_tasks": [t.model_dump() for t in plan.tasks],
            "pending_task_ids": [t.task_id for t in plan.tasks],
        }

class MockResearcherAgent:
    """Returns deterministic task results without web access."""
    async def __call__(self, state, config):
        task_id = state["current_task_id"] or state["pending_task_ids"][0]
        return {
            "completed_task_ids": [task_id],
            "task_results": {task_id: TaskResult(
                task_id=task_id, status="completed",
                findings="Mock finding for test.",
                evidence_ids=["ev-001"], evidence_count=1, ...
            ).model_dump()},
            "collected_evidence_ids": ["ev-001"],
            "pending_task_ids": [t for t in state["pending_task_ids"] if t != task_id],
        }
```

A `build_test_graph(supervisor, planner, researcher)` factory function builds a graph with injected mock agents, allowing full graph execution without any LLM or network calls.

---

## 3. Agent-Level Test Cases

### Supervisor Agent Tests (`tests/test_agents.py`)

| Test ID | Description | Expected |
|---|---|---|
| SA-001 | Valid decision output on first call (no plan exists) | Returns `request_plan` |
| SA-002 | Valid decision with completed tasks | Returns `complete_research` or `execute_next_task` |
| SA-003 | Forces `complete_research` when `iteration_count >= max_supervisor_cycles` | Returns `complete_research` without LLM call |
| SA-004 | Invalid JSON response from MockLLMProvider | Falls back to `complete_research` |
| SA-005 | Invalid decision value in JSON | Falls back to `complete_research` |
| SA-006 | LLM failure (MockLLMProvider raises) | Returns `fail_workflow` after retry |
| SA-007 | `revise_plan` decision includes `revision_notes` | revision_notes field is populated |
| SA-008 | `execute_next_task` with valid task_id | next_task_id matches a pending task |
| SA-009 | All tasks failed — should trigger fail | Returns `fail_workflow` |

### Planning Agent Tests

| Test ID | Description | Expected |
|---|---|---|
| PA-001 | Valid plan output for a simple research question | 2-8 tasks, all fields present |
| PA-002 | Task count capped at 8 | Plan validated with max 8 tasks |
| PA-003 | Task count below 2 | Retry triggered |
| PA-004 | Invalid JSON from LLM | Retry triggered; second valid response succeeds |
| PA-005 | Both retries fail | Node sets `workflow_status="failed"` |
| PA-006 | Refinement call with existing plan and notes | Produces updated plan preserving relevant tasks |
| PA-007 | Duplicate task objectives in LLM output | Duplicates removed, keeping first occurrence |
| PA-008 | Plan persisted to DB | `research_plans` and `research_tasks` rows created |

### Research Agent Tests

| Test ID | Description | Expected |
|---|---|---|
| RA-001 | Successful web search — evidence collected | TaskResult status="completed", evidence_ids populated |
| RA-002 | All URLs SSRF-blocked | TaskResult status="failed", no evidence_ids |
| RA-003 | Search provider raises exception | TaskResult status="failed", error message captured |
| RA-004 | Document chunks retrieved | Document evidence in TaskResult |
| RA-005 | Empty search results | TaskResult status="failed" |
| RA-006 | Evidence persisted to DB with task_id | EvidenceRecord rows have task_id FK set |
| RA-007 | Findings LLM call fails | TaskResult status="partial", findings="Evidence collected but synthesis failed" |
| RA-008 | Duplicate URL in results | Deduplicated — one EvidenceRecord per URL |
| RA-009 | DB insert failure | TaskResult status="fatal_error" → routes to fail_workflow |

---

## 4. Graph-Level Test Cases

### Full Graph Tests (`tests/test_multi_agent_workflow.py`)

| Test ID | Description | Expected |
|---|---|---|
| GR-001 | Happy path — 2 tasks, all succeed | Run status="completed", ResearchReport exists |
| GR-002 | Plan refinement loop — Supervisor requests revision once | planning_node called twice; second plan used |
| GR-003 | Additional research loop — Supervisor requests extra task | research_node called 3 times for 2+1 tasks |
| GR-004 | Max iterations reached | `iteration_count == max_supervisor_cycles` → forced `complete_research` |
| GR-005 | All tasks fail — Supervisor decides fail_workflow | Run status="failed", no report |
| GR-006 | One task fails, rest succeed | Report generated from partial evidence |
| GR-007 | Planning agent fails entirely | Run status="failed" |
| GR-008 | finalize_report node fails | Run status="failed" |
| GR-009 | Graph recursion_limit exceeded | Run status="failed" with "recursion limit exceeded" message |
| GR-010 | Checkpoint saved after each node | maar_checkpoints.db has entries for thread_id |
| GR-011 | Interrupted run recovery on startup | startup recovery marks pending+running runs as failed |
| GR-012 | Sequential workflow unaffected | `workflow_mode="sequential"` still uses run_research_workflow() |

---

## 5. API Endpoint Tests (`tests/test_phase3_api.py`)

| Test ID | Description | Expected |
|---|---|---|
| API-001 | POST /runs with workflow_mode="multi_agent" | 201, workflow_mode in response |
| API-002 | POST /runs without workflow_mode | 201, defaults to "sequential" |
| API-003 | GET /runs/{id}/plan — plan exists | 200, ResearchPlanResponse |
| API-004 | GET /runs/{id}/plan — no plan yet | 404 |
| API-005 | GET /runs/{id}/tasks — tasks exist | 200, list of ResearchTaskResponse |
| API-006 | GET /runs/{id}/activity — events exist | 200, AgentActivityResponse |
| API-007 | GET /runs/{id}/activity — no events | 200, empty list |
| API-008 | GET /runs/{id}/plan for sequential run | 404 |
| API-009 | All existing Phase 2 API tests | All 124 still pass |

---

## 6. End-to-End Scenario

**Scenario: Complex research question with plan revision**

Steps (using mock providers, no real API keys):

1. Create a ResearchProject via `POST /api/v1/projects`
2. Submit a run with `workflow_mode="multi_agent"` via `POST /api/v1/projects/{id}/runs`
3. Verify 201 response with `status="pending"`, `workflow_mode="multi_agent"`
4. Configure MockSupervisor with decisions: `["request_plan", "revise_plan", "execute_next_task", "execute_next_task", "complete_research"]`
5. Configure MockPlanner to return a 2-task plan on first call, 3-task plan on refinement
6. Configure MockResearcher to return `TaskResult(status="completed")` for all tasks
7. Run graph to completion
8. Assert: `research_runs.status = "completed"`
9. Assert: `research_plans` has 2 rows (plan_version 1 and 2)
10. Assert: `research_tasks` has 3 rows (from final plan)
11. Assert: `agent_execution_events` has correct sequence of events
12. Assert: `research_reports` has 1 row
13. Assert: `GET /runs/{id}/plan` returns the final plan
14. Assert: `GET /runs/{id}/tasks` returns 3 tasks, all "completed"
15. Assert: `GET /runs/{id}/activity` returns events in chronological order
16. Assert: `GET /runs/{id}/report` returns the report

**Backend interruption recovery test:**

1. Start a multi-agent run
2. After `planning_node` completes (tasks created), simulate backend restart
3. Verify: startup recovery marks run as "failed" with appropriate message
4. Verify: `research_tasks` stuck-running tasks marked as "failed"
5. Verify: `maar_checkpoints.db` still has the checkpoint (not deleted)

---

## 7. Observability Strategy

### Structured logging

All agent nodes log at INFO level using Python's `logging` module with structured fields. No external tracing service is required in Phase 3.

**Log format** (every routing decision):
```json
{
  "level": "INFO",
  "logger": "app.agents.supervisor",
  "message": "Supervisor decision",
  "run_id": "abc-123",
  "decision": "execute_next_task",
  "iteration": 2,
  "max_iterations": 3,
  "reasoning": "Task 1 complete; 2 tasks remain",
  "pending_count": 2,
  "completed_count": 1
}
```

**Log format** (task execution):
```json
{
  "level": "INFO",
  "logger": "app.agents.researcher",
  "message": "Task completed",
  "run_id": "abc-123",
  "task_id": "def-456",
  "objective": "Investigate clinical decision-making",
  "evidence_count": 3,
  "status": "completed",
  "duration_seconds": 4.2
}
```

### Application database observability

`AgentExecutionEvent` rows provide a durable audit trail that:
- Survives backend restarts
- Is queryable via the `/activity` API endpoint
- Is displayed in the frontend `AgentActivityFeed` component
- Does not require any external service

A developer can inspect why the Supervisor chose a particular path by querying:
```sql
SELECT agent_name, event_type, summary, iteration, created_at
FROM agent_execution_events
WHERE run_id = 'abc-123'
ORDER BY created_at;
```

### LangSmith — Optional Observability Integration

MAAR supports LangSmith tracing without requiring it. The integration is entirely environment-variable-driven. No application code conditionally imports or calls the LangSmith SDK — LangGraph activates tracing automatically when specific environment variables are present and ignores them when they are absent.

#### How LangGraph integrates with LangSmith

LangGraph 1.2.x uses the `langsmith` package (already installed as a transitive dependency of `langchain-core`) to detect tracing configuration at runtime. When `LANGCHAIN_TRACING_V2=true` is set, every graph node invocation, LLM call routed through `langchain-core`, and tool execution is automatically sent as a run tree to the LangSmith API. When the variable is absent or `false`, no network calls to LangSmith are made.

**Important**: The existing `LLMProvider.complete()` interface calls the LLM directly (not via LangChain's `ChatModel` abstraction). This means **LLM calls are not automatically traced by LangSmith** in Phase 3. What IS traced automatically:
- Graph node entries and exits (name, inputs, outputs, latency, errors)
- Graph-level runs (complete workflow execution)
- Any `langchain-core` `Runnable` objects if introduced in future phases

To enable LLM call tracing in Phase 3 without changing `LLMProvider`, the agent nodes emit structured log entries that mirror LangSmith's trace data locally. This ensures complete observability whether LangSmith is enabled or not.

#### Environment variables

```
# LangSmith tracing — all optional, all default to disabled/empty
LANGCHAIN_TRACING_V2=false           # set to "true" to enable LangSmith
LANGCHAIN_API_KEY=                    # your LangSmith API key (from smith.langchain.com)
LANGCHAIN_PROJECT=maar-phase3        # LangSmith project name to group runs under
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com  # default endpoint; leave empty unless using self-hosted
```

When `LANGCHAIN_TRACING_V2` is absent or `false`, `LANGCHAIN_API_KEY` is never read or validated. The application starts and runs normally.

#### Local structured logging — always on

Regardless of LangSmith status, every agent node emits structured JSON log entries via Python's `logging` module. These entries provide equivalent observability to LangSmith traces locally.

Every agent node logs at both entry and exit:

```python
# Entry log (emitted at start of every node)
logger.info("agent_node_start", extra={
    "event": "node_start",
    "node": "supervisor_node",            # node name
    "run_id": state["run_id"],
    "iteration": state["iteration_count"],
    "workflow_status": state["workflow_status"],
    "ts": datetime.now(timezone.utc).isoformat(),
})

# Exit log (emitted on successful completion)
logger.info("agent_node_complete", extra={
    "event": "node_complete",
    "node": "supervisor_node",
    "run_id": state["run_id"],
    "duration_ms": int((time.monotonic() - t_start) * 1000),
    "output_summary": "decision=execute_next_task iteration=2",
})

# Error log (emitted on exception)
logger.error("agent_node_error", extra={
    "event": "node_error",
    "node": "supervisor_node",
    "run_id": state["run_id"],
    "error": safe_error_message(exc),
    "duration_ms": int((time.monotonic() - t_start) * 1000),
})
```

Per-agent additional log fields:

| Agent | Additional logged fields |
|---|---|
| supervisor_node | decision, reasoning (truncated to 150 chars), iteration, pending_count, completed_count |
| planning_node | task_count, plan_version, is_refinement |
| research_node | task_id, task_objective (truncated), evidence_count, tool_calls_made |
| finalize_report | evidence_count_total, report_id |

#### Data sent to LangSmith when enabled

When `LANGCHAIN_TRACING_V2=true`, LangSmith receives:

| Data category | Sent? | Contains PII risk? |
|---|---|---|
| Graph node names and execution times | ✅ | No |
| Graph node input state (full dict) | ✅ | Contains research_question (user-supplied text) |
| Graph node output state (partial dict) | ✅ | Contains supervisor decisions, task lists |
| LLM prompts and responses | ❌ (not via LangChain) | N/A — not auto-traced |
| Evidence content | ❌ | N/A — not in state |
| Database IDs (UUIDs) | ✅ | No — UUIDs only |
| API keys or credentials | ❌ | N/A — never in state |

**Privacy note**: The `research_question` field in graph state is sent to LangSmith when tracing is enabled, because LangSmith captures full node inputs. This is user-supplied text. If research questions may contain sensitive information, either keep `LANGCHAIN_TRACING_V2=false` or use a self-hosted LangSmith instance (`LANGCHAIN_ENDPOINT`).

To exclude sensitive fields from LangSmith traces, set `LANGCHAIN_HIDE_INPUTS=true` in the environment. This is a native LangSmith environment variable that suppresses input serialisation.

#### Setup instructions (Milestone 1)

**Step 1** — Create a free LangSmith account at [smith.langchain.com](https://smith.langchain.com) (optional).

**Step 2** — Add to `maar/backend/.env` (do not commit this file):

```ini
# LangSmith tracing — remove or set to false to disable
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__your_key_here
LANGCHAIN_PROJECT=maar-phase3
```

**Step 3** — Restart the backend. No code changes are required.

**Step 4** — Submit a multi-agent research run. Visit [smith.langchain.com](https://smith.langchain.com) → Projects → `maar-phase3` to view the execution trace.

**Disabling**: Remove `LANGCHAIN_TRACING_V2` from `.env` or set it to `false`. Restart backend. Tracing stops immediately.

#### What developers can inspect

**Without LangSmith** (always available):
- Python log output in the backend terminal (structured JSON when `LOG_FORMAT=json`)
- `agent_execution_events` DB table via `GET /runs/{id}/activity`
- Frontend `AgentActivityFeed` component

**With LangSmith** (when enabled):
- Full graph execution tree with per-node latency
- Node input/output state at each step
- Error tracebacks with context
- Workflow-level latency breakdown
- Side-by-side run comparisons

#### LangSmith as a non-runtime dependency

`langsmith` is installed automatically as a transitive dependency of `langchain-core`. It is never imported directly in MAAR application code. LangGraph reads the `LANGCHAIN_*` environment variables internally. If `langsmith` were somehow uninstalled while `LANGCHAIN_TRACING_V2=true`, LangGraph would log a warning but continue executing without tracing. The core research workflow would not be affected.

---

## 8. Evaluation Metrics

These metrics can be computed from the application DB without external tooling:

| Metric | Definition | Query target |
|---|---|---|
| Task completion rate | completed_tasks / total_tasks per run | `research_tasks.status` |
| Evidence coverage | avg evidence_count per task | `research_tasks.evidence_count` |
| Plan revision rate | runs where plan_version > 1 / total multi-agent runs | `research_plans.plan_version` |
| Workflow termination correctness | runs ending with report / runs ending as completed | `research_runs`, `research_reports` |
| Task failure rate | failed tasks / total tasks | `research_tasks.status = "failed"` |
| Supervisor loop count | avg iteration_count at workflow end | `agent_execution_events` where event_type="workflow_complete" |
| Average workflow duration | completed_at - started_at per run | `research_runs` |
| Evidence per run | sum of evidence_count across tasks | `research_tasks` |

**Citation traceability**: verifiable by checking that `research_reports.evidence_used` references only `source_label` values that exist in `evidence_records` for the same `run_id`.

**Unsupported claim rate**: requires manual review — flag any `ResearchReport.key_findings` item that cites a `[SOURCE N]` not in `evidence_used`. The `_build_evidence_used()` function in `report_generator.py` already enforces citation resolution.

---

## 9. Evaluation Dataset

A small reproducible dataset for testing the three-agent architecture:

### Test question 1 — broad, well-resourced
`"How is machine learning being used in drug discovery?"`
- Expected tasks: 3-5 (mechanisms, clinical trials, regulatory, commercial)
- Expected evidence: 5+ web sources per task
- Used to test: happy path, evidence coverage, plan quality

### Test question 2 — narrow, limited sources
`"What is the adoption rate of quantum-resistant cryptography in financial services in 2025?"`
- Expected: partial evidence, some tasks returning empty results
- Used to test: task failure handling, partial evidence report generation

### Test question 3 — deliberately vague
`"Tell me about AI"`
- Expected: Planning Agent creates broad tasks; Supervisor likely requests revision
- Used to test: plan revision loop, max iterations

### Test question 4 — structured for max-iteration trigger
Use with `MAX_SUPERVISOR_CYCLES=1`
`"Explain the geopolitical implications of rare earth element supply chains"`
- Expected: one supervisor cycle → forced `complete_research`
- Used to test: bounded loop termination

All four test questions can be exercised with mock providers in automated tests by injecting canned plan/finding responses.

---

## 10. Phase 3 Completion Checklist

- [ ] All 124 Phase 2 tests pass after Phase 3 code is added
- [ ] `tests/test_agents.py` — all agent-level tests pass (target: 30+ tests)
- [ ] `tests/test_multi_agent_workflow.py` — all graph tests pass (target: 15+ tests)
- [ ] `tests/test_phase3_api.py` — all API tests pass (target: 10+ tests)
- [ ] E2E scenario (section 6) executes successfully with mock providers
- [ ] E2E scenario executes successfully with real watsonx.ai + Tavily APIs
- [ ] `npm run build` passes with zero TypeScript errors after frontend changes
- [ ] `AgentActivityFeed` renders correctly in browser for a completed multi-agent run
- [ ] `ResearchPlanView` shows task status updates during an active run
- [ ] `MultiAgentStatusCard` shows correct active agent name during execution
- [ ] Backend interruption recovery test passes (section 6)
- [ ] Supervisor routing decision logged in `agent_execution_events` for every cycle
- [ ] `maar_checkpoints.db` created and contains entries after a multi-agent run
- [ ] Sequential workflow (`workflow_mode="sequential"`) unchanged — verified manually
