# 42 — Live Activity and Progress Design

**Project:** Multi-Agent Autonomous Researcher (MAAR)
**Phase:** 5 — M5.1 and M5.2
**Status:** Planning

---

## 1. Overview

M5.1 and M5.2 replace the current polling architecture with a Server-Sent Events (SSE) stream for live activity delivery, and introduce a structured workflow progress model derived from actual task and event data.

### Current State (Phase 4)

- `AgentActivityFeed.tsx` polls `GET /runs/{id}/activity` every 3 seconds
- `RunStatusCard.tsx` and `MultiAgentStatusCard.tsx` poll `GET /runs/{id}` every 3-4 seconds
- `AgentExecutionEvent` records are written during graph execution and persisted in SQLite
- The activity endpoint returns paginated events ordered by `created_at`
- **No SSE, no WebSocket, no streaming of any kind**

### Phase 5 Goal

- One persistent SSE connection per active run delivers events in real time
- Polling remains as a fallback (when SSE connection is unavailable or dropped)
- Progress is calculated deterministically from actual task and stage data
- Reconnect after browser refresh replays all events from the DB

---

## 2. SSE Event Stream

### 2.1 Endpoint

```
GET /api/v1/projects/{project_id}/runs/{run_id}/stream
```

**Response headers:**
```
Content-Type: text/event-stream
Cache-Control: no-cache
X-Accel-Buffering: no
```

**Implementation**: `sse-starlette` `EventSourceResponse` with an `async generator` that yields events from the in-memory queue and from DB replay on reconnect.

**Query parameters:**
- `last_event_id` (optional): Resume replay from this sequence number. Also sent automatically via `Last-Event-ID` request header.

### 2.2 SSE Event Format

Each event is a standard SSE envelope:

```
id: {run_id}:{sequence_number}
event: {event_type}
data: {JSON payload}

```

**Event types and payloads:**

#### `activity`
```json
{
  "id": "uuid",
  "run_id": "uuid",
  "agent_name": "supervisor | planner | researcher | system | critic",
  "event_type": "decision | task_started | task_completed | plan_created | ...",
  "summary": "Human-readable event description",
  "iteration": 3,
  "output_ref": "task:abc123",
  "created_at": "2026-11-12T10:00:00Z",
  "sequence": 12
}
```

#### `status_change`
```json
{
  "run_id": "uuid",
  "status": "running | completed | failed | needs_attention | rejected",
  "current_stage": "Researching task 3/5",
  "changed_at": "2026-11-12T10:05:00Z"
}
```

#### `approval_required`
```json
{
  "approval_id": "uuid",
  "run_id": "uuid",
  "checkpoint_type": "plan_approval | critic_needs_attention",
  "title": "Research Plan Ready for Review",
  "description": "The Planner has generated a 5-task research plan.",
  "created_at": "2026-11-12T10:02:00Z"
}
```

#### `run_completed`
```json
{
  "run_id": "uuid",
  "status": "completed",
  "report_id": "uuid",
  "completed_at": "2026-11-12T10:15:00Z"
}
```

#### `run_failed`
```json
{
  "run_id": "uuid",
  "status": "failed",
  "error_message": "LLM synthesis failed after 2 attempts.",
  "failed_at": "2026-11-12T10:05:00Z"
}
```

#### `heartbeat`
```json
{
  "timestamp": "2026-11-12T10:00:15Z"
}
```
Sent every 15 seconds to prevent proxy timeouts.

### 2.3 Sequence Numbers

Each `AgentExecutionEvent` row needs a `sequence` column (auto-incrementing integer, per-run) to support `Last-Event-ID` replay. This is added in **Migration H** (shared with approval requests) or as a standalone column addition.

Alternative: use the event's `rowid` from SQLite as sequence number. SQLite guarantees `rowid` monotonically increases. This avoids a new column at the cost of being a DB internal. **Decision**: Add explicit `sequence` column on `AgentExecutionEvent` for clarity and portability.

### 2.4 Replay on Reconnect

When the client connects with `Last-Event-ID: {run_id}:{last_seq}`:

1. Query DB: `SELECT * FROM agent_execution_events WHERE run_id=? AND sequence > ? ORDER BY sequence`
2. Stream all replayed events as `activity` type SSE events
3. Then switch to live queue subscription

When `Last-Event-ID` is absent (fresh connection):
1. Stream all existing events for the run from the start
2. Then subscribe to live queue

This ensures the activity timeline is fully accurate after any browser refresh.

---

## 3. Event Broadcasting

### 3.1 In-Memory Event Bus

```python
# app/services/event_broadcaster.py

import asyncio
from typing import Optional

# run_id → list of subscriber queues
_subscribers: dict[str, list[asyncio.Queue]] = {}

async def publish(run_id: str, event_type: str, data: dict) -> None:
    """Publish an event to all active SSE subscribers for a run."""
    payload = {"type": event_type, "data": data}
    for q in list(_subscribers.get(run_id, [])):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            # Subscriber is too slow — drop event (they will replay from DB on reconnect)
            pass

async def subscribe(run_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    _subscribers.setdefault(run_id, []).append(q)
    return q

async def unsubscribe(run_id: str, q: asyncio.Queue) -> None:
    subs = _subscribers.get(run_id, [])
    if q in subs:
        subs.remove(q)
    if not subs:
        _subscribers.pop(run_id, None)
```

### 3.2 Publishing Events

The `event_service.log_event()` function is called throughout the graph execution. Phase 5 adds a `broadcast_event()` call immediately after DB commit:

```python
# event_service.py — extended
async def log_event(db, run_id, agent_name, event_type, summary, ...):
    event = AgentExecutionEvent(...)
    db.add(event)
    # Broadcast happens AFTER commit (caller's responsibility or helper)
    return event

async def log_and_broadcast(db, run_id, ...):
    event = await log_event(db, run_id, ...)
    await db.commit()
    from app.services.event_broadcaster import publish
    await publish(run_id, "activity", event.to_sse_dict())
```

### 3.3 Status Change Publishing

Run status changes are also broadcast:

```python
# In executor.py, nodes.py, and approval_service.py
# When run.status or run.current_stage changes:
await broadcast_status_change(run_id, status, current_stage)
```

---

## 4. Frontend SSE Client

### 4.1 Custom Hook: `useLiveActivity`

```typescript
// src/hooks/useLiveActivity.ts
export function useLiveActivity(projectId: string, runId: string, isActive: boolean) {
  const [events, setEvents] = useState<LiveActivityEvent[]>([]);
  const [status, setStatus] = useState<RunStatus | null>(null);
  const [approvalRequired, setApprovalRequired] = useState<ApprovalRequest | null>(null);
  const lastEventIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!isActive || !runId) return;

    const url = `/api/v1/projects/${projectId}/runs/${runId}/stream`
      + (lastEventIdRef.current ? `?last_event_id=${lastEventIdRef.current}` : '');

    const es = new EventSource(url);

    es.addEventListener('activity', (e: MessageEvent) => {
      const event = JSON.parse(e.data) as LiveActivityEvent;
      lastEventIdRef.current = e.lastEventId;
      setEvents(prev => deduplicate([...prev, event]));
    });

    es.addEventListener('status_change', (e: MessageEvent) => {
      const change = JSON.parse(e.data);
      setStatus(change);
    });

    es.addEventListener('approval_required', (e: MessageEvent) => {
      setApprovalRequired(JSON.parse(e.data));
    });

    es.addEventListener('run_completed', () => {
      // Signal parent to load report
    });

    es.onerror = () => {
      // EventSource auto-reconnects using Last-Event-ID header
      // No manual retry logic needed
    };

    return () => es.close();
  }, [projectId, runId, isActive]);

  return { events, status, approvalRequired };
}

function deduplicate(events: LiveActivityEvent[]): LiveActivityEvent[] {
  const seen = new Set<string>();
  return events.filter(e => {
    if (seen.has(e.id)) return false;
    seen.add(e.id);
    return true;
  });
}
```

### 4.2 Polling Fallback

The existing `AgentActivityFeed` polling remains available. The `LiveActivityStream` component uses SSE by default. If `EventSource` is not supported or the connection fails repeatedly, the component falls back to polling at 5-second intervals (slower than the current 3s to reduce load).

```typescript
// Detect SSE support
const sseSupported = typeof EventSource !== 'undefined';
// Use SSE if supported, polling otherwise
```

---

## 5. Workflow Progress Tracking

### 5.1 Progress Model

Progress is calculated from a combination of:
1. **`ResearchRun.status`** — overall lifecycle
2. **`ResearchRun.current_stage`** — current human-readable stage label
3. **`ResearchTask` completion counts** — task-level granularity
4. **`AgentExecutionEvent` types** — node-level completions

### 5.2 Multi-Agent Progress Stages

| Stage | ID | Completion Signal | Weight |
|-------|-----|-------------------|--------|
| Planning | `planning` | `plan_created` event | 1 |
| Source Collection | `source_collection` | All tasks `completed` | tasks_count |
| Report Generation | `report_generation` | `report_draft` event | 1 |
| Claim Verification | `claim_verification` | `claims_verified` event | 1 |
| Critic Review | `critic_review` | `critic_review_complete` event | 1 |
| Citation Validation | `citation_validation` | `citations_validated` event | 1 |
| Complete | `complete` | `run.status == "completed"` | — |

**Progress percentage** = completed stages / total stages. Each source collection task counts as 1/n_tasks of the source_collection stage.

### 5.3 Sequential Progress Stages

| Stage | ID | Completion Signal |
|-------|-----|-------------------|
| Initializing | `init` | `workflow_start` event |
| Web Search | `web_search` | Evidence collected > 0 |
| Document Processing | `doc_processing` | Skipped if no docs |
| Report Generation | `report_generation` | `report_draft` event |
| Claim Verification | `claim_verification` | `claims_verified` event |
| Complete | `complete` | `run.status == "completed"` |

### 5.4 Progress API

New endpoint added to `runs.py`:

```
GET /api/v1/projects/{project_id}/runs/{run_id}/progress
```

**Response:**
```json
{
  "run_id": "uuid",
  "workflow_mode": "multi_agent",
  "overall_status": "running",
  "percent_complete": 42,
  "stages": [
    {
      "id": "planning",
      "label": "Planning",
      "status": "completed",
      "completed_at": "2026-11-12T10:01:00Z"
    },
    {
      "id": "source_collection",
      "label": "Source Collection",
      "status": "running",
      "tasks_total": 5,
      "tasks_completed": 2,
      "tasks_failed": 0,
      "current_task_label": "Task 3: Analyzing evidence from academic sources"
    },
    {
      "id": "report_generation",
      "label": "Report Generation",
      "status": "pending"
    },
    ...
  ],
  "started_at": "2026-11-12T10:00:00Z",
  "elapsed_seconds": 125,
  "current_stage_label": "Source Collection — task 3 of 5"
}
```

### 5.5 WorkflowProgressTracker Component

The `WorkflowProgressTracker` component renders the stages as a vertical stepper:

```
✅ Planning            completed 10:01:00
⟳ Source Collection   running — task 3/5  [2m 05s]
○ Report Generation   pending
○ Claim Verification  pending
○ Critic Review       pending
○ Citation Validation pending
○ Complete            —
```

States: `completed` (green check), `running` (animated spinner), `pending` (grey circle), `failed` (red X), `waiting_for_approval` (amber clock).

**Visual treatment:**
- Completed stages: muted grey text, green check icon
- Running stage: bold text, animated ring icon, elapsed time badge
- Failed stage: red text, red X icon, error tooltip
- Approval-waiting stage: amber text, clock icon, "Action required" badge

---

## 6. LiveActivityStream Component

### 6.1 Design

The `LiveActivityStream` replaces `AgentActivityFeed` for active runs. It uses the `useLiveActivity` hook.

**Layout:**
- Fixed-height scrollable panel (max-h-80)
- Auto-scrolls to newest event when running
- Pauses auto-scroll when user manually scrolls up
- "Jump to latest" button appears when not auto-scrolling

**Each event row:**
```
[agent badge] [summary text]         [timestamp] [iter badge]
```

**Agent badge colors (existing):**
- `supervisor` → violet
- `planner` → blue
- `researcher` → emerald
- `system` → slate
- `critic` → amber

**Event type icons:**
- `decision` → arrow-right
- `task_started` → play
- `task_completed` → check
- `task_failed` → x-circle
- `plan_created` → clipboard-list
- `workflow_complete` → flag

### 6.2 Connection Status Indicator

Small status badge in the activity feed header:
- Green dot: `Live` (SSE connected)
- Yellow dot: `Reconnecting…` (SSE disconnected, attempting reconnect)
- Grey dot: `Polling` (fallback mode)
- Grey dot: `History` (run complete, showing historical events)

---

## 7. Integration with Existing Components

### 7.1 ResearchWorkspace Integration

`MultiAgentStatusCard.tsx` is replaced by the new `ResearchWorkspace` layout (M5.7). The progress tracker and activity feed become top-level workspace elements.

### 7.2 Backward Compatibility

The existing `GET /runs/{id}/activity` endpoint is NOT removed. It remains the source for:
- Historical view of completed runs
- SSE replay queries
- Tests

The new SSE stream endpoint is additive only.

---

## 8. Database Changes for M5.1/M5.2

### 8.1 `agent_execution_events` Table Addition

Add `sequence` column (integer, auto-increment per run, for SSE Last-Event-ID support):

```sql
ALTER TABLE agent_execution_events ADD COLUMN sequence INTEGER;
```

**Migration H** (shared with approval table) applies this.

Backfill existing rows: `UPDATE agent_execution_events SET sequence = rowid WHERE sequence IS NULL`.

After backfill, add NOT NULL constraint in the next migration if desired (SQLite limitation: cannot add NOT NULL without table recreation — leave nullable with application-level enforcement).

### 8.2 Event Ordering Guarantee

Events are ordered by `(run_id, sequence)`. Since sequence is derived from `rowid` or auto-incremented, and SQLite is single-writer with WAL mode, ordering is guaranteed within a single process.

---

## 9. Error Handling and Edge Cases

| Scenario | Handling |
|----------|----------|
| SSE client disconnects (browser tab closed) | Server detects write error on next event, unsubscribes queue |
| No active SSE subscriber when event fires | Event only written to DB; no broadcast loss |
| Browser refresh during active run | EventSource reconnects, Last-Event-ID replays missing events from DB |
| Run completes before SSE connect | Full history replayed from DB on connect |
| Queue full (slow client) | QueueFull exception drops event; client replays from DB on reconnect |
| Backend restart during active run | Run is marked `failed` (existing startup cleanup). No SSE reconnect possible (run dead). UI shows failed state. |
| Multiple browser tabs for same run | Each tab gets its own SSE queue subscription — all receive events independently |
| Events arriving out of order | Deduplicated by `id` field in frontend; sorted by `sequence` for display |
