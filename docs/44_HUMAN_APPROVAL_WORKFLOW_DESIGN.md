# 44 — Human Approval Workflow Design

## Phase 5 · Module M5.5

---

## 1. Purpose

This document specifies the design for the human-in-the-loop approval workflow in MAAR.

LangGraph supports pausing a running graph at designated nodes using `interrupt_before`. When the graph reaches one of these nodes, execution suspends. The backend notifies the frontend via SSE. The user sees an approval prompt in the workspace, makes a decision, and the backend resumes the graph with the user's input.

This mechanism is used in two places in Phase 5:

| Checkpoint | Graph Node | Trigger Condition | Decision Required |
|---|---|---|---|
| CP-1: Plan Approval | `planning_complete_node` | Research plan generated | Approve / Reject / Request revisions |
| CP-2: Critic Review | `critic_review_approval_node` | Critic flags `needs_attention` | Proceed / Revise / Abort |

---

## 2. LangGraph Interrupt Mechanism

### Current state (Phase 4)

```python
# backend/app/graph/workflow.py
compiled_graph = graph.compile(
    checkpointer=checkpointer,
    interrupt_before=[]   # ← no interrupts currently
)
```

### Phase 5 change

```python
compiled_graph = graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["planning_complete_node", "critic_review_approval_node"]
)
```

When the graph reaches either of these nodes, it suspends before executing the node body. The `AgentExecutor.run()` coroutine returns at this point. The executor must detect the suspension and persist an `ApprovalRequest` record.

### Resuming the graph

```python
# Resume with approval decision
await graph.ainvoke(
    {"approval_decision": "approved", "approval_notes": "Looks good"},
    config={"configurable": {"thread_id": run_id}}
)
```

The `thread_id` equals `run_id`. The checkpointer (`maar_checkpoints.db`) holds the suspended state. Calling `ainvoke` with `None` as input and the same thread_id resumes from the checkpoint.

### Detecting suspension

After each `ainvoke` or `astream` call, the executor inspects the graph's current state:

```python
state = await graph.aget_state({"configurable": {"thread_id": run_id}})
if state.next:  # non-empty means graph is suspended at a node
    suspended_node = state.next[0]
    # create ApprovalRequest in DB
```

---

## 3. ApprovalRequest Database Model

New table: `approval_requests`

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Primary key |
| `run_id` | UUID (FK → research_runs.id) | Associated run |
| `checkpoint_name` | VARCHAR(100) | `plan_approval` or `critic_review_approval` |
| `node_name` | VARCHAR(100) | LangGraph node name (e.g. `planning_complete_node`) |
| `context_snapshot` | TEXT (JSON) | Relevant state data serialised to JSON for display |
| `status` | VARCHAR(20) | `pending`, `approved`, `rejected`, `revision_requested`, `expired` |
| `decision` | VARCHAR(30) | Null until resolved: `approved`, `rejected`, `revision_requested` |
| `decision_notes` | TEXT | Optional free-text from user |
| `created_at` | DATETIME | When the interrupt fired |
| `decided_at` | DATETIME | When user submitted decision |
| `expires_at` | DATETIME | Auto-reject after N hours (configurable, default 24h) |

Constraints:
- `UNIQUE(run_id, checkpoint_name, status)` where `status = 'pending'` — only one pending approval per checkpoint per run at a time
- Index on `(run_id, status)`

`context_snapshot` contains enough information for the frontend to display a meaningful prompt without additional API calls:

For CP-1 (plan approval):
```json
{
  "research_question": "...",
  "plan_summary": "...",
  "planned_tasks": ["task1", "task2"],
  "estimated_sources": 12,
  "workflow_mode": "deep_research"
}
```

For CP-2 (critic review):
```json
{
  "review_status": "needs_attention",
  "overall_assessment": "...",
  "critical_issues": ["issue1", "issue2"],
  "recommendations": ["rec1", "rec2"],
  "report_quality_score": 0.62
}
```

---

## 4. New Graph Nodes

### 4.1 `planning_complete_node`

This node is added immediately after the existing planning node(s) in the graph. Its execution body is minimal — it is primarily a suspension point.

When the graph is interrupted **before** this node, execution pauses after planning is complete but before any research tasks begin. The user reviews the generated plan.

If the user **approves**: the graph resumes, `planning_complete_node` runs (a no-op or logging step), and the supervisor routes to the first research task.

If the user **rejects** or **requests revisions**: the graph state is updated with revision notes, execution resumes, and the planner node is re-invoked with the revision context.

### 4.2 `critic_review_approval_node`

This node is added after the existing `critic_node` in the graph. It only triggers the interrupt mechanism when `CriticReview.review_status == "needs_attention"`. 

If the critic's status is `approved`, this node is a pass-through and execution continues to report generation without interrupting.

If the critic flagged issues:
- Interrupt fires
- User reviews the critic's findings
- User can approve (proceed to report), request revision (loop back to researcher agents), or abort

---

## 5. API Endpoints

### 5.1 Get pending approval for a run

```
GET /api/v1/runs/{run_id}/approval
```

**Response — pending approval exists:**
```json
{
  "id": "uuid",
  "run_id": "uuid",
  "checkpoint_name": "plan_approval",
  "node_name": "planning_complete_node",
  "context_snapshot": { ... },
  "status": "pending",
  "created_at": "2026-11-12T10:00:00Z",
  "expires_at": "2026-11-13T10:00:00Z"
}
```

**Response — no pending approval:**
```json
null
```

**HTTP status:** 200 in both cases.

### 5.2 Submit approval decision

```
POST /api/v1/runs/{run_id}/approval/{approval_id}/decide
```

**Request body:**
```json
{
  "decision": "approved | rejected | revision_requested",
  "notes": "Optional notes to guide revision"
}
```

**Validation:**
- `decision` must be one of the three allowed values
- `notes` is optional, max 2000 chars
- The approval must be in `pending` status and not expired

**Response:**
```json
{
  "id": "uuid",
  "decision": "approved",
  "decided_at": "2026-11-12T10:05:00Z",
  "run_status": "running"
}
```

**After successful decision:**
1. Update `ApprovalRequest.status` to `approved/rejected` and set `decision`, `decided_at`
2. If `approved` or `revision_requested`: resume graph with decision context via `graph.ainvoke`
3. If `rejected`: update `ResearchRun.status` to `failed`, set `current_stage` to `aborted`
4. Emit SSE event `approval_resolved` to notify frontend
5. Return response

**HTTP status:**
- 200 — decision accepted and graph resumed
- 404 — approval_id not found for this run
- 409 — approval already decided or expired
- 422 — invalid decision value

### 5.3 Approval history for a run (optional, useful for debugging)

```
GET /api/v1/runs/{run_id}/approvals
```

Returns all approval records for a run in reverse chronological order.

---

## 6. SSE Events for Approval

The SSE stream (M5.1) emits two new event types related to approvals:

### `approval_required`

Emitted when the executor detects graph suspension:

```json
{
  "event_type": "approval_required",
  "run_id": "uuid",
  "data": {
    "approval_id": "uuid",
    "checkpoint_name": "plan_approval",
    "context_snapshot": { ... },
    "expires_at": "2026-11-13T10:00:00Z"
  }
}
```

### `approval_resolved`

Emitted after the user submits a decision and the graph resumes:

```json
{
  "event_type": "approval_resolved",
  "run_id": "uuid",
  "data": {
    "approval_id": "uuid",
    "decision": "approved",
    "run_continuing": true
  }
}
```

---

## 7. Frontend Approval UI

### 7.1 Approval Banner

When the workspace receives an `approval_required` SSE event (or polls and finds a pending approval), it displays a prominent banner at the top of the workspace, above all panels.

The banner replaces the run progress indicator during the approval wait period.

**Plan Approval Banner:**
```
┌─────────────────────────────────────────────────────────────┐
│ ⏸  Research Plan Ready for Review                           │
│                                                             │
│ The research agents have generated a plan. Review it before │
│ research begins. This request expires in 23h 55m.          │
│                                                             │
│ [View Plan & Decide]                                        │
└─────────────────────────────────────────────────────────────┘
```

**Critic Review Banner:**
```
┌─────────────────────────────────────────────────────────────┐
│ ⚠  Quality Review Requires Your Attention                   │
│                                                             │
│ The critic agent has flagged issues with the research       │
│ output. Your decision is required to continue.             │
│                                                             │
│ [Review Findings & Decide]                                  │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Approval Modal

Clicking "View Plan & Decide" or "Review Findings & Decide" opens a full-screen modal (shadcn/ui `Dialog` or `Sheet`) with:

**For Plan Approval:**
- Research question (display only)
- Plan summary paragraph
- Planned tasks list with agent assignments
- Estimated number of sources to retrieve
- Workflow mode badge

Decision buttons:
- **Approve Plan** (primary, green) — research begins immediately
- **Request Revisions** (secondary) — opens a text area for revision notes; re-runs planner
- **Reject & Abort** (destructive) — cancels the run permanently

**For Critic Review:**
- Overall assessment text
- Quality score (displayed as a score badge)
- Critical issues list (bulleted)
- Recommendations list (bulleted)

Decision buttons:
- **Proceed to Report** (primary) — generates report despite issues
- **Request Revision** (secondary) — opens text area; loops back to research agents
- **Abort Research** (destructive) — cancels the run

### 7.3 Expiry Countdown

The banner and modal display a live countdown to the expiry time. When expired:
- The approval transitions to `expired` status server-side (via a background check or when the run resumes)
- The banner updates to show "This approval request has expired"
- The run is marked `failed` with reason `approval_expired`

### 7.4 Workspace State During Approval Wait

While waiting for approval:
- Progress bar shows current percentage (frozen at the suspension point)
- Agent activity feed continues showing completed events
- Source Explorer, Evidence Viewer show whatever was collected before suspension
- Run status badge shows "Awaiting Approval" in amber
- No new SSE events for agent activity arrive (graph is paused)

---

## 8. State Machine: Run Status During Approvals

```
running
  └─→ awaiting_approval   (interrupt fired, ApprovalRequest created)
        ├─→ running        (approved or revision_requested → graph resumed)
        ├─→ failed         (rejected or expired)
        └─→ failed         (expiry background sweep)
```

The `ResearchRun.status` field gains a new valid value: `awaiting_approval`. The frontend must handle this status in `RunStatusCard`.

---

## 9. Expiry Management

A lightweight background mechanism handles expiry. Options in order of simplicity:

1. **Check-on-access**: When `GET /runs/{run_id}` or `GET /runs/{run_id}/approval` is called, the backend checks if the pending approval has passed `expires_at` and auto-transitions it to `expired` at that point.

2. **FastAPI startup task**: A background `asyncio.Task` started at app startup sweeps `approval_requests` every 30 minutes for expired pending rows.

Phase 5 uses option 1 (check-on-access) first, adding option 2 only if needed. This avoids background task complexity.

---

## 10. Security and Validation Rules

- Only one `pending` approval may exist per `(run_id, checkpoint_name)` at a time
- Attempting to decide on an expired approval returns HTTP 409
- Attempting to decide on an already-decided approval returns HTTP 409
- `revision_requested` without notes is allowed (notes are optional)
- No authentication in Phase 5 (local-only development); this is noted as a future hardening item

---

## 11. Non-Goals for Phase 5

- No email or push notifications for pending approvals
- No approval delegation or multi-user review
- No approval templates or pre-set responses
- No approval audit trail UI (records exist in DB; no dedicated UI page)
- No approval for intermediate research stages other than the two checkpoints defined above
