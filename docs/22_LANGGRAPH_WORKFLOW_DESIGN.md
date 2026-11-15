# 22 — LangGraph Workflow Design

**Project**: Multi-Agent Autonomous Researcher (MAAR)
**Phase**: 3
**Status**: Draft — Awaiting Approval

---

## 1. StateGraph Architecture Overview

The Phase 3 research workflow is implemented as a LangGraph `StateGraph` using the 1.2.x API. The graph contains six nodes: three are LLM-driven agent nodes and three are deterministic Python functions.

```
                          ┌─────────────┐
                    START │ initialize  │
                          │    _run     │
                          └──────┬──────┘
                                 │
                          ┌──────▼──────┐
                     ┌───►│ supervisor  │◄──────────────────┐
                     │    │    _node    │                    │
                     │    └──────┬──────┘                    │
                     │           │ route_after_supervisor    │
                     │    ┌──────┴──────────────────────┐    │
                     │    │                             │    │
                     │  "request_plan"          "execute_next_task"
                     │  "revise_plan"           "continue_research"
                     │    │                             │    │
                     │  ┌─▼──────────┐        ┌────────▼──┐  │
                     │  │ planning   │        │ research  │  │
                     │  │   _node    │        │   _node   │──┘
                     │  └─────┬──────┘        └─────┬─────┘
                     │        │                     │ route_after_research
                     └────────┘                     │
                  "plan_complete"            ┌───────┴────────┐
                                             │                │
                                      "supervisor"    "fail_workflow"
                                             │                │
                                      ┌──────┘        ┌──────▼──────┐
                                      │               │    fail_    │
                               (loop back)            │  workflow   │
                                                      └──────┬──────┘
                                                             │
                                  "complete_research"        │
                            ┌──────────────────────┐         │
                            │  finalize_report     │◄────────┘ (Supervisor)
                            └──────────┬───────────┘
                                       │
                                      END
```

**Routing rules summary:**

| From Node | Supervisor Decision / Condition | → To Node |
|---|---|---|
| supervisor_node | `request_plan` or `revise_plan` | planning_node |
| supervisor_node | `execute_next_task` or `continue_research` | research_node |
| supervisor_node | `complete_research` | finalize_report |
| supervisor_node | `fail_workflow` | fail_workflow |
| supervisor_node | `iteration_count >= max_supervisor_cycles` | finalize_report (forced) |
| planning_node | always | supervisor_node |
| research_node | task succeeded | supervisor_node |
| research_node | unrecoverable tool failure | fail_workflow |
| initialize_run | always | supervisor_node |
| finalize_report | always | END |
| fail_workflow | always | END |

---

## 2. Typed Shared State

The shared state is a `TypedDict` compatible with LangGraph's checkpointing serialisation. Evidence content is NOT stored in state — only IDs and metadata.

```python
# app/graph/state.py  (design — not implementation code)

from __future__ import annotations
from typing import Annotated, Any
import operator
from typing_extensions import TypedDict

# Reducer: append-only list (used for IDs and task lists)
def append_reducer(existing: list, new: list) -> list:
    return existing + new

# Reducer: merge dict (used for task_results)
def merge_dict_reducer(existing: dict, new: dict) -> dict:
    return {**existing, **new}

class ResearchWorkflowState(TypedDict):
    # Immutable after initialization
    run_id: str
    project_id: str
    research_question: str
    workflow_mode: str
    max_supervisor_cycles: int          # default 3, from settings

    # Set by planning_node, read by supervisor and research nodes
    research_plan: dict | None          # serialised ResearchPlan

    # Task management — accumulated by planning_node
    research_tasks: list[dict]          # list of serialised ResearchTask
    pending_task_ids: list[str]         # task_ids not yet executed
    current_task_id: str | None         # task currently assigned

    # Accumulated by research_node (append-only reducers)
    completed_task_ids: Annotated[list[str], append_reducer]
    failed_task_ids: Annotated[list[str], append_reducer]
    collected_evidence_ids: Annotated[list[str], append_reducer]  # EvidenceRecord IDs

    # Task results — accumulated by research_node
    task_results: Annotated[dict[str, dict], merge_dict_reducer]  # task_id → TaskResult dict

    # Supervisor control
    supervisor_decision: str | None     # last decision string
    revision_notes: str | None          # supervisor note to planning agent
    iteration_count: int                # incremented each supervisor cycle

    # Workflow lifecycle
    workflow_status: str                # "initializing"|"planning"|"researching"|"finalizing"|"completed"|"failed"
    error_message: str | None

    # Result
    final_report_id: str | None         # ResearchReport.id after finalization
```

### Field ownership

| Field | Set by | Read by | Immutable after |
|---|---|---|---|
| run_id, project_id, research_question | executor.py | all nodes | initialization |
| max_supervisor_cycles | executor.py | supervisor_node | initialization |
| research_plan | planning_node | supervisor_node, finalize_report | — |
| research_tasks, pending_task_ids | planning_node | supervisor_node, research_node | re-planning replaces list |
| current_task_id | research_node | research_node | each task completion |
| completed_task_ids | research_node (reducer) | supervisor_node | — |
| collected_evidence_ids | research_node (reducer) | finalize_report | — |
| task_results | research_node (reducer) | supervisor_node | — |
| supervisor_decision | supervisor_node | routing functions | each supervisor call |
| revision_notes | supervisor_node | planning_node | each revision request |
| iteration_count | supervisor_node | supervisor_node, routing | — |
| workflow_status | all nodes | all nodes | — |
| error_message | any node on failure | fail_workflow | — |
| final_report_id | finalize_report | — | set once |

### What is NOT in state

- Raw evidence content (stored in `evidence_records` DB table; referenced by ID)
- Raw LLM prompt/response strings (logged as `AgentExecutionEvent` rows)
- Full document content (in `uploaded_documents` file system and DB)
- Large research question context (loaded fresh from DB when needed)

---

## 3. Graph Nodes

### 3.1 `initialize_run` (deterministic)

**Type**: Deterministic Python function

**Reads**: `run_id`, `research_question`

**Actions**:
1. Loads `ResearchRun` from DB and verifies `status="running"` and `workflow_mode="multi_agent"`
2. Writes `AgentExecutionEvent(agent="system", event_type="workflow_start")`
3. Updates `ResearchRun.current_stage = "Initializing"`

**Returns state update**: `{"workflow_status": "planning"}`

**Error**: If run not found or wrong status → returns `{"workflow_status": "failed", "error_message": "..."}`

---

### 3.2 `supervisor_node` (LLM-driven)

**Type**: LLM-driven agent

**Reads**: `research_question`, `research_plan`, `task_results`, `iteration_count`, `max_supervisor_cycles`, `pending_task_ids`, `completed_task_ids`, `failed_task_ids`

**LLM prompt strategy**: The system prompt defines the Supervisor's role and lists the exact allowed decision values. The user prompt contains: the research question, a structured summary of the research plan (if available), a compact summary of completed task results (task objective + findings headline + evidence count), list of pending tasks, and the iteration count. Raw evidence content is NOT passed to the Supervisor.

**Structured output**: `SupervisorDecision` with fields:
- `decision: str` — one of the 7 allowed values
- `reasoning: str` — why this decision was made (≤300 chars)
- `revision_notes: str | None` — populated when `decision="revise_plan"`
- `next_task_id: str | None` — populated when `decision="execute_next_task"`

**Forced termination**: Before calling the LLM, if `iteration_count >= max_supervisor_cycles`, the node skips the LLM call and returns `SupervisorDecision(decision="complete_research", reasoning="Maximum iterations reached")`.

**Returns state update**:
```python
{
    "supervisor_decision": decision.decision,
    "revision_notes": decision.revision_notes,
    "current_task_id": decision.next_task_id,
    "iteration_count": state["iteration_count"] + 1,
    "workflow_status": derived_from_decision,
}
```

**Error**: On LLM failure → `{"workflow_status": "failed", "error_message": "..."}`

---

### 3.3 `planning_node` (LLM-driven)

**Type**: LLM-driven agent

**Reads**: `research_question`, `research_plan` (existing plan for refinement), `revision_notes`

**LLM prompt strategy**: System prompt defines the planning role, the JSON output schema for `ResearchPlan`, and the constraint (2-8 tasks, no redundant tasks, each task must be independently searchable). User prompt contains: research question, existing plan (if refinement), revision notes.

**Structured output**: `ResearchPlan` with:
- `plan_id: str` (UUID)
- `objectives: list[str]` (3-6 high-level objectives)
- `tasks: list[ResearchTask]` (2-8 tasks)

Each `ResearchTask`:
- `task_id: str` (UUID, stable)
- `objective: str`
- `search_query: str` (optimised for web search)
- `expected_evidence_type: str`
- `priority: int` (1=highest, 3=lowest)

**DB persistence**: node calls `plan_service.save_plan()` which writes `ResearchPlan` and all `ResearchTask` rows. Updates `ResearchRun.current_stage = "Planning"`.

**Returns state update**:
```python
{
    "research_plan": plan.model_dump(),
    "research_tasks": [t.model_dump() for t in plan.tasks],
    "pending_task_ids": [t.task_id for t in sorted(plan.tasks, key=lambda x: x.priority)],
    "workflow_status": "researching",
}
```

**Error**: On JSON parse failure → retry once. If retry fails → `{"workflow_status": "failed", "error_message": "Planning agent failed to produce a valid plan"}`.

---

### 3.4 `research_node` (LLM-driven + tools)

**Type**: LLM-driven agent with constrained tool access

**Important**: The Research Agent in Phase 3 does NOT use LangGraph's `ToolNode` or LangChain tool-calling. Instead it calls Python tool functions directly (the existing Phase 2 providers are not LangChain `Tool` objects). The "LLM-driven" aspect is that the Research Agent calls the LLM to synthesise a brief `findings` summary after collecting evidence — it does NOT use the LLM for routing.

**Execution pattern**:
1. Pick the next task: reads `current_task_id` from state; if None, picks first from `pending_task_ids`
2. Updates task status to `running` in DB
3. Calls `tools.web_search(task.search_query)` → list of `NormalizedEvidence`
4. Optionally calls `tools.get_document_chunks(run_id)` if run has `use_documents=True`
5. Persists all evidence via `EvidenceRecord` inserts (with `task_id` column)
6. Calls LLM (brief synthesis): "Given these evidence excerpts for the task objective [X], write a 2-3 sentence finding summary." → `findings: str`
7. Builds `TaskResult`

**Tools available** (defined in `app/agents/tools.py`):
- `web_search(query: str, num_results: int) -> list[NormalizedEvidence]`
- `fetch_web_content(url: str) -> NormalizedEvidence | None`
- `get_document_chunks(run_id: str, db: AsyncSession) -> list[NormalizedEvidence]`

**Returns state update**:
```python
{
    "completed_task_ids": [task_id],          # reducer appends
    "task_results": {task_id: task_result},   # reducer merges
    "collected_evidence_ids": evidence_ids,   # reducer appends
    "pending_task_ids": updated_pending,      # task removed
    "current_task_id": None,
}
```

**Error**: On tool failure → still returns `TaskResult` with `status="failed"`, `error` field populated. Does NOT set `workflow_status="failed"` — Supervisor evaluates whether to continue.

---

### 3.5 `finalize_report` (deterministic)

**Type**: Deterministic Python function

**Reads**: `run_id`, `collected_evidence_ids`, `research_question`

**Actions**:
1. Loads all `EvidenceRecord` rows for `run_id` from DB (full content)
2. Calls `build_evidence_context(evidence_list, research_question, budget_chars)` — Phase 2 function, unchanged
3. Calls `build_prompt()` — Phase 2 function, unchanged
4. Calls `generate_report(llm, research_question, selected_evidence, user_prompt, SYSTEM_PROMPT)` — Phase 2 function, unchanged
5. Persists `ResearchReport` to DB
6. Updates `ResearchRun.status = "completed"`, `current_stage = "Complete"`
7. Writes `AgentExecutionEvent(agent="system", event_type="workflow_complete")`

**Returns state update**: `{"workflow_status": "completed", "final_report_id": report.id}`

---

### 3.6 `fail_workflow` (deterministic)

**Type**: Deterministic Python function

**Reads**: `run_id`, `error_message`, `workflow_status`

**Actions**:
1. Updates `ResearchRun.status = "failed"`, `error_message` from state
2. Writes `AgentExecutionEvent(agent="system", event_type="workflow_failed")`
3. Marks any `running` tasks in DB as `failed`

**Returns state update**: `{"workflow_status": "failed"}`

---

## 4. Conditional Routing Functions

### `route_after_supervisor(state: ResearchWorkflowState) -> str`

```
decision = state["supervisor_decision"]

if state["iteration_count"] >= state["max_supervisor_cycles"]:
    return "finalize_report"   # forced termination

if decision in ("request_plan", "revise_plan"):
    return "planning_node"

if decision in ("execute_next_task", "continue_research"):
    return "research_node"

if decision == "complete_research":
    return "finalize_report"

if decision == "fail_workflow":
    return "fail_workflow"

# Fallback — should not occur if Supervisor produces valid output
if state["workflow_status"] == "failed":
    return "fail_workflow"

return "finalize_report"   # safe default
```

### `route_after_research(state: ResearchWorkflowState) -> str`

```
# If the task failed AND the error is unrecoverable (e.g. DB unavailable)
latest_task_id = state["completed_task_ids"][-1]  # just appended
task_result = state["task_results"].get(latest_task_id, {})

if task_result.get("status") == "fatal_error":
    return "fail_workflow"

return "supervisor_node"
```

---

## 5. Loop Control and Safety

### Iteration counting

- `iteration_count` starts at 0
- `supervisor_node` increments it by 1 each time it runs
- Before calling the LLM, supervisor checks: if `iteration_count >= max_supervisor_cycles` → skip LLM, return `complete_research`
- `max_supervisor_cycles` is configurable via `MAX_SUPERVISOR_CYCLES` env var (default: 3)

### Task execution limits

- Maximum 8 tasks per plan (enforced in Planning Agent prompt)
- Each task is executed once; re-execution of completed tasks is blocked at the `research_node` level
- `failed_task_ids` accumulates permanently; tasks in this list cannot be re-queued

### Graph-level safety net

- `StateGraph.compile(recursion_limit=25)` — hard limit enforced by LangGraph
- 25 allows: up to 3 supervisor cycles × (1 supervisor + 1 planning/research) + buffer = safe for all normal paths
- Any graph execution reaching this limit is treated as an unhandled failure

### Plan refinement cap

- Planning Agent tracks refinement cycles in state via `iteration_count`
- A second `revise_plan` decision from Supervisor at `iteration_count >= 2` is ignored; the existing plan is used as-is

---

## 6. LangGraph Checkpointing

### Checkpointer

```python
# app/graph/checkpointer.py  (design)

from langgraph.checkpoint.sqlite import SqliteSaver

def get_checkpointer() -> SqliteSaver:
    """Returns a SqliteSaver backed by maar_checkpoints.db."""
    return SqliteSaver.from_conn_string("./maar_checkpoints.db")
```

### Checkpoint behaviour

- LangGraph 1.2.x automatically saves state after each node completes
- Thread ID = `run_id` (UUID string from `ResearchRun.id`)
- Each research run has its own isolated checkpoint thread
- Checkpoint state is JSON-serialisable (TypedDict fields only; no Python objects with non-serialisable types)

### Thread identification

```python
config = {
    "configurable": {
        "thread_id": run_id,    # isolates checkpoint per run
    },
    "recursion_limit": 25,
}
```

### Interrupted execution recovery

When the backend restarts mid-execution:
1. Startup recovery (`_recover_stuck_runs`) marks the `ResearchRun.status = "failed"` (as per FR-013 in doc 20)
2. The checkpoint in `maar_checkpoints.db` for that `thread_id` is **preserved**
3. In Phase 3, automatic graph resumption is NOT implemented (risk: stale state)
4. Future Phase 4 can add a resume path: call `graph.ainvoke(None, config={"configurable": {"thread_id": run_id}})` to continue from last checkpoint

### Human-in-the-loop preparation

The graph is compiled with `interrupt_before=[]` in Phase 3 (no interrupts). The infrastructure supports adding `interrupt_before=["planning_node"]` in a future phase to allow plan review before execution begins. This requires no architectural change — only the compile call changes.

---

## 7. Graph Compilation (Design)

```python
# app/graph/workflow.py  (design — not implementation)

from langgraph.graph import StateGraph, END
from app.graph.state import ResearchWorkflowState
from app.graph.checkpointer import get_checkpointer
from app.graph.nodes import initialize_run_node, finalize_report_node, fail_workflow_node
from app.agents.supervisor import supervisor_node
from app.agents.planner import planning_node
from app.agents.researcher import research_node
from app.graph.routing import route_after_supervisor, route_after_research

def build_research_graph():
    builder = StateGraph(ResearchWorkflowState)

    # Register nodes
    builder.add_node("initialize_run", initialize_run_node)
    builder.add_node("supervisor_node", supervisor_node)
    builder.add_node("planning_node", planning_node)
    builder.add_node("research_node", research_node)
    builder.add_node("finalize_report", finalize_report_node)
    builder.add_node("fail_workflow", fail_workflow_node)

    # Entry point
    builder.set_entry_point("initialize_run")

    # Fixed edges
    builder.add_edge("initialize_run", "supervisor_node")
    builder.add_edge("planning_node", "supervisor_node")
    builder.add_edge("finalize_report", END)
    builder.add_edge("fail_workflow", END)

    # Conditional edges
    builder.add_conditional_edges(
        "supervisor_node",
        route_after_supervisor,
        {
            "planning_node": "planning_node",
            "research_node": "research_node",
            "finalize_report": "finalize_report",
            "fail_workflow": "fail_workflow",
        }
    )
    builder.add_conditional_edges(
        "research_node",
        route_after_research,
        {
            "supervisor_node": "supervisor_node",
            "fail_workflow": "fail_workflow",
        }
    )

    checkpointer = get_checkpointer()
    graph = builder.compile(
        checkpointer=checkpointer,
        interrupt_before=[],   # no human-in-the-loop in Phase 3
    )
    return graph

# Module-level singleton — compiled once at import
research_graph = build_research_graph()
```

---

## 8. Error Propagation

### Node-level errors

Every node function wraps its body in try/except:

```python
try:
    # ... node logic ...
    return state_update
except Exception as exc:
    logger.error("Node %s failed: %s", node_name, exc)
    return {
        "workflow_status": "failed",
        "error_message": safe_error_message(exc),
    }
```

The routing function `route_after_supervisor` and `route_after_research` both check `workflow_status == "failed"` and route to `fail_workflow` when detected.

### Partial evidence failure

If `research_node` fails to collect evidence for a task (tool errors, SSRF blocks, empty results), it:
- Sets `TaskResult.status = "failed"` and `TaskResult.error = <message>`
- Does NOT set `workflow_status = "failed"`
- Returns normally; Supervisor evaluates whether sufficient evidence exists from other tasks

### Fatal errors

The following trigger immediate `fail_workflow`:
- DB connection failure during any node
- `initialize_run` cannot find the run record
- `finalize_report` LLM call fails after 2 retries
- Graph `recursion_limit` exceeded (LangGraph raises `GraphRecursionError`)

`GraphRecursionError` is caught at the executor level and triggers DB failure marking.

---

## 9. Execution Configuration

```python
# app/graph/executor.py  (design)

async def run_multi_agent_workflow(run_id: str) -> None:
    """
    Entrypoint called as a FastAPI background task.
    Mirrors the signature of run_research_workflow() for drop-in routing.
    """
    from app.graph.workflow import research_graph

    initial_state = ResearchWorkflowState(
        run_id=run_id,
        project_id=...,               # loaded from DB
        research_question=...,         # loaded from DB
        workflow_mode="multi_agent",
        max_supervisor_cycles=settings.MAX_SUPERVISOR_CYCLES,
        research_plan=None,
        research_tasks=[],
        pending_task_ids=[],
        current_task_id=None,
        completed_task_ids=[],
        failed_task_ids=[],
        collected_evidence_ids=[],
        task_results={},
        supervisor_decision=None,
        revision_notes=None,
        iteration_count=0,
        workflow_status="initializing",
        error_message=None,
        final_report_id=None,
    )

    config = {
        "configurable": {"thread_id": run_id},
        "recursion_limit": 25,
    }

    try:
        await research_graph.ainvoke(initial_state, config=config)
    except Exception as exc:
        # Top-level catch: mark run failed in DB
        await _mark_run_failed(run_id, safe_error_message(exc))
```

---

## 10. Migration Path

### Phase 3 (current design)
- Sequential task execution
- Single-thread SQLite checkpointer
- All agents share one LLM provider
- No human-in-the-loop

### Phase 4 options enabled by this design
- **Parallel task execution**: Use LangGraph's `Send()` API to fan out multiple `research_node` invocations. State reducers are already append-only, making this safe.
- **Human plan review**: Add `interrupt_before=["research_node"]` to graph compilation. No state or node changes required.
- **PostgreSQL checkpointer**: Replace `SqliteSaver` with `AsyncPostgresSaver` in `checkpointer.py`. Graph definition unchanged.
- **Per-agent model configuration**: Add `AgentConfig` to settings and pass into each agent node. Provider interface already supports this via constructor parameters.
- **LangSmith tracing**: Set `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` in `.env`. No code changes required — LangGraph auto-traces when LangSmith env vars are present.
