# 23 — Shared State and Communication

**Project**: Multi-Agent Autonomous Researcher (MAAR)
**Phase**: 3
**Status**: Draft — Awaiting Approval

---

## 1. State Schema

The `ResearchWorkflowState` TypedDict is the single communication medium between all graph nodes. Agents do not message each other directly — they read from and write to state, with LangGraph applying reducers and persisting checkpoints.

### Full schema with annotations

```python
# app/graph/state.py  (design specification)

from __future__ import annotations
from typing import Annotated
from typing_extensions import TypedDict
import operator


# ── Reducer functions ────────────────────────────────────────────────

def append_unique(existing: list[str], new: list[str]) -> list[str]:
    """Append new items that are not already in the list."""
    seen = set(existing)
    return existing + [x for x in new if x not in seen]

def merge_task_results(
    existing: dict[str, dict],
    new: dict[str, dict],
) -> dict[str, dict]:
    """Merge task result dicts; existing results are never overwritten."""
    return {**new, **existing}   # existing wins on conflict


# ── State definition ─────────────────────────────────────────────────

class ResearchWorkflowState(TypedDict):
    # ── Immutable context (set once by executor.py) ──────────────────
    run_id: str
    project_id: str
    research_question: str
    workflow_mode: str
    max_supervisor_cycles: int

    # ── Research plan (set/replaced by planning_node) ─────────────────
    research_plan: dict | None           # serialised ResearchPlan
    research_tasks: list[dict]           # serialised ResearchTask list (ordered by priority)
    pending_task_ids: list[str]          # task_ids not yet executed (mutable)
    current_task_id: str | None          # task currently being executed

    # ── Accumulated results (append-only reducers) ────────────────────
    completed_task_ids: Annotated[list[str], append_unique]
    failed_task_ids: Annotated[list[str], append_unique]
    collected_evidence_ids: Annotated[list[str], append_unique]  # EvidenceRecord IDs

    # ── Task results (merge reducer — existing results protected) ──────
    task_results: Annotated[dict[str, dict], merge_task_results]

    # ── Supervisor control ────────────────────────────────────────────
    supervisor_decision: str | None      # latest routing decision
    revision_notes: str | None           # notes to Planning Agent (if revising)
    iteration_count: int                 # supervisor cycle count

    # ── Workflow lifecycle ────────────────────────────────────────────
    workflow_status: str                 # see status values below
    error_message: str | None

    # ── Final output ──────────────────────────────────────────────────
    final_report_id: str | None          # ResearchReport.id after finalization
```

### Workflow status values

| Value | Set by | Meaning |
|---|---|---|
| `"initializing"` | executor.py (initial) | Graph just started |
| `"planning"` | initialize_run node | Supervisor will request a plan |
| `"researching"` | planning_node | Tasks are being executed |
| `"finalizing"` | supervisor_node on `complete_research` | Report generation starting |
| `"completed"` | finalize_report node | Research and report complete |
| `"failed"` | any node on error | Terminal failure state |

---

## 2. Reducers

### Why reducers matter

LangGraph nodes return **partial state updates** (a dict of only the fields they change). The StateGraph applies reducer functions to merge the update into the existing state. Without reducers, a node returning `{"completed_task_ids": ["task-abc"]}` would **replace** the list. With the `append_unique` reducer, it appends instead.

### Reducer definitions

**`append_unique(existing, new) → list`**
- Used for: `completed_task_ids`, `failed_task_ids`, `collected_evidence_ids`
- Behaviour: appends new items that do not already exist in the list
- Safety: prevents duplicate IDs from being added if a node is retried
- LangGraph annotation: `Annotated[list[str], append_unique]`

**`merge_task_results(existing, new) → dict`**
- Used for: `task_results`
- Behaviour: merges two dicts; existing entries are protected (existing wins on key conflict)
- Safety: a task result written once cannot be silently overwritten by a retry
- LangGraph annotation: `Annotated[dict[str, dict], merge_task_results]`

### Fields without reducers

Fields without a reducer annotation are **replaced** by the new value when a node writes them. This is correct for:
- `supervisor_decision` — replaced each supervisor cycle
- `revision_notes` — replaced each supervisor cycle (null if not revising)
- `current_task_id` — set and then cleared
- `pending_task_ids` — replaced by planning_node (new plan replaces old list); reduced manually by research_node
- `research_plan`, `research_tasks` — replaced on re-planning
- `workflow_status`, `error_message` — replaced on transitions
- `iteration_count` — replaced with incremented value each cycle

---

## 3. State Ownership Rules

Every field has exactly one **owner** — the node responsible for setting it — and zero or more **readers**.

| Field | Owner | Readers | Mutability |
|---|---|---|---|
| `run_id` | executor.py | all | Immutable |
| `project_id` | executor.py | all | Immutable |
| `research_question` | executor.py | supervisor, planning, finalize | Immutable |
| `workflow_mode` | executor.py | — | Immutable |
| `max_supervisor_cycles` | executor.py | supervisor | Immutable |
| `research_plan` | planning_node | supervisor, finalize | Replaced on re-plan |
| `research_tasks` | planning_node | supervisor, research | Replaced on re-plan |
| `pending_task_ids` | planning_node (set) / research_node (removes processed ID) | supervisor | Mutable list |
| `current_task_id` | research_node | research_node | Cleared after each task |
| `completed_task_ids` | research_node (reducer) | supervisor | Append-only |
| `failed_task_ids` | research_node (reducer) | supervisor | Append-only |
| `collected_evidence_ids` | research_node (reducer) | finalize_report | Append-only |
| `task_results` | research_node (reducer) | supervisor | Merge — existing protected |
| `supervisor_decision` | supervisor_node | routing functions | Replaced each cycle |
| `revision_notes` | supervisor_node | planning_node | Replaced each cycle |
| `iteration_count` | supervisor_node | supervisor_node | Incremented |
| `workflow_status` | all nodes (transitions) | routing functions | Replaced |
| `error_message` | any node on failure | fail_workflow | Replaced |
| `final_report_id` | finalize_report | — | Set once |

---

## 4. Agent Input/Output Contracts

### 4.1 Supervisor Agent

**Input (reads from state)**:
```
research_question           string
research_plan               dict | None  (serialised ResearchPlan)
task_results                dict         (task_id → TaskResult dict)
completed_task_ids          list[str]
failed_task_ids             list[str]
pending_task_ids            list[str]
iteration_count             int
max_supervisor_cycles       int
workflow_status             str
```

**Context passed to LLM** (constructed by supervisor.py, NOT the full state):
```
research_question           verbatim
plan_summary                list of task objectives only (not full task dicts)
completed_task_summaries    list of {task_id, objective, findings_headline, evidence_count}
failed_tasks                list of {task_id, objective, error}
pending_task_objectives     list of strings
iteration_info              "Cycle N of max M"
```

**Output (SupervisorDecision Pydantic model)**:
```python
class SupervisorDecision(BaseModel):
    decision: Literal[
        "request_plan",
        "revise_plan",
        "execute_next_task",
        "continue_research",
        "complete_research",
        "fail_workflow",
    ]
    reasoning: str              # max 300 chars
    revision_notes: str | None  # required when decision == "revise_plan"
    next_task_id: str | None    # required when decision == "execute_next_task"
```

**State update written**:
```python
{
    "supervisor_decision": decision.decision,
    "revision_notes": decision.revision_notes,
    "current_task_id": decision.next_task_id,
    "iteration_count": state["iteration_count"] + 1,
    "workflow_status": map_decision_to_status(decision.decision),
}
```

---

### 4.2 Research Planning Agent

**Input (reads from state)**:
```
research_question           string
research_plan               dict | None   (None on first call; existing plan on refinement)
revision_notes              str | None    (populated on refinement requests)
```

**Context passed to LLM**:
```
research_question           verbatim
existing_plan_json          serialised plan (only when refining)
revision_notes              verbatim (only when refining)
task_count_constraint       "Produce between 2 and 8 tasks"
```

**Output (ResearchPlan Pydantic model)**:
```python
class ResearchTask(BaseModel):
    task_id: str               # UUID, generated at planning time
    objective: str             # what to investigate
    search_query: str          # optimised search string for web search
    expected_evidence_type: str # e.g. "academic papers", "news articles", "statistics"
    priority: int              # 1 (highest) to 3 (lowest)

class ResearchPlan(BaseModel):
    plan_id: str               # UUID
    objectives: list[str]      # 3-6 high-level research objectives
    tasks: list[ResearchTask]  # 2-8 tasks, sorted by priority
    refinement_notes: str | None  # populated when this is a refined plan
```

**State update written**:
```python
{
    "research_plan": plan.model_dump(),
    "research_tasks": [t.model_dump() for t in plan.tasks],
    "pending_task_ids": [t.task_id for t in sorted(plan.tasks, key=lambda x: x.priority)],
    "workflow_status": "researching",
}
```

---

### 4.3 Research Agent

**Input (reads from state)**:
```
current_task_id             str
research_tasks              list[dict]   (finds current task by task_id)
run_id                      str          (for document evidence retrieval)
```

**Context passed to LLM** (only for findings synthesis step):
```
task_objective              verbatim from ResearchTask
evidence_excerpts           list of {source, excerpt} — max 5 items, 300 chars each
```

**Tools called** (direct Python calls, not LangChain tools):
```python
# app/agents/tools.py

async def web_search(
    query: str,
    search_provider: WebSearchProvider,
    num_results: int = 8,
) -> list[NormalizedEvidence]:
    """Calls TavilySearchProvider.search(). Returns NormalizedEvidence list."""

async def fetch_web_content(
    url: str,
    settings: Settings,
) -> NormalizedEvidence | None:
    """Calls is_safe_url() + fetch_url(). Returns None if blocked or failed."""

async def get_document_chunks(
    run_id: str,
    db: AsyncSession,
) -> list[NormalizedEvidence]:
    """Loads UploadedDocument records for run, extracts text, returns NormalizedEvidence."""
    # Reuses the same extraction logic as Phase 2 _extract_documents()
    # but without the run.use_documents check (Research Agent checks this itself)
```

**Output (TaskResult Pydantic model)**:
```python
class TaskResult(BaseModel):
    task_id: str
    status: Literal["completed", "partial", "failed", "fatal_error"]
    findings: str                    # 2-3 sentence LLM-generated summary
    evidence_ids: list[str]          # EvidenceRecord.id values persisted to DB
    evidence_count: int
    unanswered_questions: list[str]  # what this task could not determine
    limitations: str | None
    error: str | None                # populated on failure
```

**State update written**:
```python
{
    "completed_task_ids": [task_id],                        # reducer appends
    "task_results": {task_id: task_result.model_dump()},    # reducer merges
    "collected_evidence_ids": task_result.evidence_ids,     # reducer appends
    "pending_task_ids": [t for t in state["pending_task_ids"] if t != task_id],
    "current_task_id": None,
}
```

---

## 5. Communication Protocol

### No direct agent-to-agent messaging

Agents do not call each other. The only communication path is:
1. Node A writes a partial state update
2. LangGraph applies reducers and saves the new state
3. LangGraph checkpoints the state
4. The routing function reads the relevant state field(s) and returns the next node name
5. Node B receives the full state and reads only the fields it needs

This means:
- There is no risk of circular calls
- Every state transition is logged by LangGraph's checkpointer
- Any node can be unit-tested in isolation by constructing a state dict directly

### Supervisor evaluation without raw evidence

The Supervisor never receives raw evidence content. It receives structured summaries in the LLM prompt:
- Task objectives (from `research_tasks`)
- Per-task finding headlines and evidence counts (from `task_results`)
- Lists of completed, failed, and pending task IDs

This keeps the Supervisor's context small and prevents it from attempting its own synthesis.

### Planning Agent receives only what it needs for planning

The Planning Agent receives the research question and, when refining, the existing plan and the Supervisor's revision notes. It does not receive evidence data, task results, or routing history.

### Research Agent receives one task at a time

The Research Agent is given a single `ResearchTask` (identified by `current_task_id`). It does not see other tasks' results or the research plan objectives. This intentional isolation prevents the agent from duplicating evidence already collected by other tasks.

### Agent execution records

Every significant agent action is persisted as an `AgentExecutionEvent` row (see doc 25 for schema). This provides a durable audit log independent of the LangGraph checkpoint state.

```python
class AgentExecutionEventSchema(BaseModel):
    run_id: str
    agent_name: str          # "supervisor", "planner", "researcher", "system"
    event_type: str          # "decision", "plan_created", "task_started",
                             # "task_completed", "task_failed", "workflow_start",
                             # "workflow_complete", "workflow_failed"
    summary: str             # human-readable one-line description
    input_ref: str | None    # e.g. "task_id:abc123" or "plan_id:xyz"
    output_ref: str | None   # e.g. "decision:execute_next_task" or "evidence_ids:3"
    iteration: int           # supervisor iteration count at time of event
    created_at: datetime
```

---

## 6. State Size Considerations

### What keeps state small

- Evidence **content** is stored in `evidence_records` (DB); only IDs are in state
- Document **content** is stored on disk; chunks are loaded fresh when needed
- LLM **prompts and responses** are stored in `agent_execution_events` (DB); not in state
- Task results contain only a brief `findings` string (2-3 sentences), not full synthesis

### Estimated state size

With 6 tasks and 8 evidence items per task:
- `research_plan`: ~2KB (6 tasks × ~300 chars each)
- `task_results`: ~1.2KB (6 × ~200 chars findings + metadata)
- `collected_evidence_ids`: ~240 bytes (48 UUID strings)
- Total state: ~5-10KB

This is well within LangGraph's SQLite checkpoint storage limits.

---

## 7. Three Persistence Layers — Interaction Contract

```
                LangGraph State                Application DB          LangGraph Checkpoints
                (in-memory)                    (maar_dev.db)           (maar_checkpoints.db)
                ───────────────                ──────────────          ────────────────────────
initialize_run  workflow_status="planning"  ─► ResearchRun.status     ─► checkpoint saved
                                               ="running"

planning_node   research_plan={...}         ─► ResearchPlan row        ─► checkpoint saved
                research_tasks=[...]           ResearchTask rows
                pending_task_ids=[...]

research_node   completed_task_ids+=[id]    ─► EvidenceRecord rows     ─► checkpoint saved
                task_results+={id:result}      ResearchTask.status
                collected_evidence_ids+=[...]  AgentExecutionEvent rows

finalize_report final_report_id=report.id  ─► ResearchReport row      ─► checkpoint saved
                workflow_status="completed"    ResearchRun.status
                                               ="completed"

Backend restart: state lost from memory;    DB state preserved        Checkpoint preserved
                                            (authoritative)           (resumable in Phase 4)
```

**Consistency rule**: The application DB is the **source of truth** for business state. The LangGraph checkpoint is a technical artifact for graph resumption. If they are inconsistent (e.g., checkpoint says "researching" but DB says "failed"), the DB wins and the checkpoint is considered stale.
