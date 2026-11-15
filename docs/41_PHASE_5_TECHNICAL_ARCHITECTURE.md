# 41 — Phase 5 Technical Architecture

**Project:** Multi-Agent Autonomous Researcher (MAAR)
**Phase:** 5 — Complete Research Experience
**Status:** Planning

---

## 1. Architecture Overview

Phase 5 adds an experience layer on top of the Phase 4 pipeline. The core backend execution engine is unchanged. Phase 5 changes are additive.

```
┌──────────────────────────────────────────────────────────┐
│                   MAAR Frontend (Next.js)                │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │  Research   │  │  Evidence /  │  │ Report Viewer  │  │
│  │  Workspace  │  │  Claims      │  │ + Export       │  │
│  │  (M5.7)     │  │  Viewer      │  │ (M5.6)         │  │
│  └──────┬──────┘  │  (M5.4)      │  └───────┬────────┘  │
│         │         └──────────────┘          │           │
│  ┌──────▼──────────────────────────────────▼──────────┐  │
│  │            SSE Client (EventSource)                │  │
│  │   + REST API client (apiFetch)                     │  │
│  └────────────────────┬───────────────────────────────┘  │
└───────────────────────┼──────────────────────────────────┘
                        │ HTTP / SSE
┌───────────────────────▼──────────────────────────────────┐
│                  MAAR Backend (FastAPI)                   │
│                                                          │
│  ┌─────────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │  SSE Event      │  │  Approval    │  │  Export     │ │
│  │  Stream API     │  │  API (NEW)   │  │  API (NEW)  │ │
│  │  (NEW M5.1)     │  │  (M5.5)      │  │  (M5.6)     │ │
│  └────────┬────────┘  └──────┬───────┘  └──────┬──────┘ │
│           │                  │                  │        │
│  ┌────────▼──────────────────▼──────────────────▼──────┐ │
│  │              Existing REST APIs (Phase 1-4)         │ │
│  │  projects / runs / sources / evidence / claims /    │ │
│  │  citations / reviews / activity                     │ │
│  └────────────────────────┬────────────────────────────┘ │
│                           │                              │
│  ┌────────────────────────▼────────────────────────────┐ │
│  │              LangGraph Workflow Engine               │ │
│  │  (interrupt_before added for approval checkpoints)  │ │
│  │  AsyncSqliteSaver checkpointer                      │ │
│  └────────────────────────┬────────────────────────────┘ │
└───────────────────────────┼──────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
 maar_dev.db         maar_checkpoints.db   exports/ dir
 (main tables)       (LangGraph state)     (PDF/DOCX/MD)
```

---

## 2. Technology Stack (Unchanged + Additions)

### 2.1 Frontend (No new dependencies required for M5.1–M5.5)

| Technology | Version | Role |
|-----------|---------|------|
| Next.js | 14.2.3 | App Router, RSC + client components |
| React | 18.3.1 | Component framework |
| TypeScript | latest | Type safety |
| Tailwind CSS | latest | Utility styling |
| shadcn/ui | installed | Component library (17 components) |
| Lucide React | installed | Icons |
| Sonner | installed | Toast notifications |

**Native `EventSource` API** (browser built-in) — no additional package needed for SSE.

**M5.6 only**: No frontend export library needed. Download is triggered via an `<a href>` link to a backend-generated file endpoint.

### 2.2 Backend Additions

| Addition | Purpose | Phase |
|----------|---------|-------|
| `reportlab` or `weasyprint` | PDF generation | M5.6 |
| `sse-starlette` | SSE streaming via FastAPI | M5.1 |

**`sse-starlette`** is the standard Starlette/FastAPI SSE library. It provides `EventSourceResponse` and handles keep-alive, Last-Event-ID, and reconnect semantics correctly with async generators.

**PDF Library Decision**: `reportlab` for pure-Python programmatic PDF generation (no system dependencies, no Chromium). `weasyprint` requires a full HTML-to-PDF rendering stack with system libraries — unsuitable for a local-first portable application. `reportlab` is recommended. See `50_PHASE_5_IMPLEMENTATION_ROADMAP_AND_DECISIONS.md` for full ADR.

---

## 3. Phase 5 Backend Architecture

### 3.1 New API Modules

```
app/api/v1/routes/
├── runs.py          ← ADD: SSE stream endpoint, progress endpoint
├── approvals.py     ← NEW: approval CRUD, resume workflow
├── exports.py       ← NEW: PDF/DOCX/MD generation + download
```

### 3.2 New Services

```
app/services/
├── event_broadcaster.py   ← NEW: in-memory event bus for SSE fan-out
├── approval_service.py    ← NEW: approval request CRUD + LangGraph resume
├── export_service.py      ← NEW: PDF/DOCX/MD generation
├── progress_service.py    ← NEW: progress calculation from task + event data
```

### 3.3 New Models

```
app/models/
├── approval_request.py    ← NEW: approval requests and decisions
├── report_version.py      ← NEW: report version history
├── export_record.py       ← NEW: export file tracking
```

### 3.4 New Alembic Migrations

- **Migration H**: `approval_requests` table
- **Migration I**: `report_versions` table + `version_number` column on `research_reports`
- **Migration J**: `export_records` table

### 3.5 Modified Files

```
app/graph/workflow.py   ← ADD interrupt_before for approval checkpoints
app/graph/nodes.py      ← ADD approval request creation before interrupts
app/graph/executor.py   ← ADD approval resume logic
app/core/config.py      ← ADD export directory config, approval expiry config
```

---

## 4. Phase 5 Frontend Architecture

### 4.1 New Pages

```
src/app/
└── projects/[id]/
    └── runs/[runId]/       ← Page already exists; ENHANCE workspace
```

No new top-level pages. All Phase 5 UI lives in the existing workspace.

### 4.2 New Components

```
src/components/workspace/
├── LiveActivityStream.tsx       ← NEW: SSE-powered event timeline
├── WorkflowProgressTracker.tsx  ← NEW: stage-based progress visualization
├── SourceExplorer.tsx           ← NEW: full-featured source browser
├── EvidenceViewer.tsx           ← NEW: claim + evidence drill-down
├── ApprovalPanel.tsx            ← NEW: approval prompt + decision UI
├── ReportExportPanel.tsx        ← NEW: format selector + download
├── ResearchWorkspace.tsx        ← NEW: unified layout container (M5.7)
```

### 4.3 Updated Components

```
src/components/workspace/
├── ResearchPanel.tsx        ← REPLACE with ResearchWorkspace.tsx (M5.7)
├── AgentActivityFeed.tsx    ← ENHANCE to SSE mode (keep polling fallback)
├── RunStatusCard.tsx        ← ENHANCE with WorkflowProgressTracker
├── MultiAgentStatusCard.tsx ← ENHANCE with LiveActivityStream + WorkflowProgressTracker
```

### 4.4 New API Client Functions

```
src/lib/api/
├── runs.ts      ← ADD: getProgress, createSSEConnection
├── approvals.ts ← NEW: getApprovals, submitApproval, getApprovalStatus
├── exports.ts   ← NEW: requestExport, getExportStatus, downloadExport
```

### 4.5 New TypeScript Types

```
src/lib/types/
├── run.ts        ← ADD: WorkflowProgress, ProgressStage types
├── approval.ts   ← NEW: ApprovalRequest, ApprovalDecision types
├── export.ts     ← NEW: ExportRecord, ExportFormat types
├── event.ts      ← NEW: SSEEvent, LiveActivityEvent types (already have AgentEvent)
```

---

## 5. SSE Architecture

### 5.1 SSE vs WebSocket Decision

**Decision: SSE**

See full ADR in `50_PHASE_5_IMPLEMENTATION_ROADMAP_AND_DECISIONS.md`. Summary:

- All Phase 5 live updates are backend→frontend only (agent activities, status changes, approval triggers).
- User actions (approve, reject) go via normal REST POST endpoints.
- SSE is simpler, HTTP/1.1 compatible, auto-reconnects natively, and works behind standard proxies.
- WebSocket adds bidirectional complexity with no benefit for this use case.

### 5.2 SSE Event Stream Design

**Endpoint:** `GET /api/v1/projects/{project_id}/runs/{run_id}/stream`

**Event types:**

| Event Type | Payload | Trigger |
|-----------|---------|---------|
| `activity` | AgentExecutionEvent fields | New event logged to DB |
| `status_change` | run_id, status, current_stage | Run status changes |
| `approval_required` | ApprovalRequest fields | Workflow interrupted for approval |
| `run_completed` | run_id, status, report_id | Workflow finishes |
| `run_failed` | run_id, error_message | Workflow fails |
| `heartbeat` | timestamp | Every 15s to keep connection alive |

**Event ID:** `{run_id}:{event_sequence_number}` — used for Last-Event-ID reconnect.

### 5.3 Fan-out Architecture

LangGraph runs in a background `asyncio.Task`. SSE clients are long-lived HTTP connections. The bridge between them is an in-memory `asyncio.Queue` per run:

```python
# event_broadcaster.py
_queues: dict[str, list[asyncio.Queue]] = {}  # run_id → list of subscriber queues

async def publish(run_id: str, event: SSEEvent):
    for q in _queues.get(run_id, []):
        await q.put(event)

async def subscribe(run_id: str) -> asyncio.Queue:
    q = asyncio.Queue(maxsize=100)
    _queues.setdefault(run_id, []).append(q)
    return q

async def unsubscribe(run_id: str, q: asyncio.Queue):
    if run_id in _queues:
        _queues[run_id].discard(q)
```

**Replay on reconnect**: When a client reconnects with `Last-Event-ID`, the SSE endpoint queries the DB for events newer than the last seen sequence and sends them before subscribing to the live queue. This handles all refresh/reconnect scenarios correctly.

### 5.4 SQLite Concurrency Caution

SQLite has writer-locks. The graph runs in one async task; the SSE endpoint reads in another. Since all graph writes are in separate `async with AsyncSessionLocal()` blocks (short transactions), and SSE reads are read-only queries, this works correctly with WAL journal mode (already enabled via aiosqlite defaults). No additional locking is needed.

---

## 6. LangGraph Approval Integration

### 6.1 interrupt_before Additions

Phase 5 adds `interrupt_before` to the compiled graph for approval-gated nodes:

```python
_graph = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=["planning_complete_node", "critic_review_approval_node"],
)
```

These are **new lightweight pass-through nodes** inserted into the graph specifically as interrupt targets. The existing nodes (`planning_node`, `critic_node`) are not modified.

### 6.2 Approval Checkpoints

| Checkpoint Node | Trigger | Default |
|----------------|---------|---------|
| `planning_complete_node` | After planner generates research plan | OFF (configurable per run) |
| `critic_review_approval_node` | After Critic returns `needs_attention` | ON |

### 6.3 Resume Flow

```
[Run paused at interrupt]
   ↓
User submits approval via POST /api/v1/approvals/{id}/decide
   ↓
approval_service.py: record decision, call resume_workflow()
   ↓
executor.py: graph.ainvoke(None, config={"configurable": {"thread_id": run_id}})
   ↓ (LangGraph resumes from checkpoint)
Workflow continues
```

---

## 7. Export Architecture

### 7.1 Export Pipeline

```
User clicks Export → POST /api/v1/exports (format, run_id)
   ↓
export_service.py: load report from DB (no new LLM calls)
   ↓
Format handler:
  - PDF:  reportlab → write to exports/{run_id}/{filename}.pdf
  - DOCX: python-docx → write to exports/{run_id}/{filename}.docx
  - MD:   string template → write to exports/{run_id}/{filename}.md
   ↓
ExportRecord saved to DB (status, file_path, format, created_at)
   ↓
Return export_id + download URL
   ↓
GET /api/v1/exports/{export_id}/download → FileResponse
```

### 7.2 File Storage

- Location: `{EXPORT_DIR}/{run_id}/{timestamp}_{format}.{ext}`
- Default `EXPORT_DIR`: `./exports` (relative to backend working directory)
- Configurable via `.env` `EXPORT_DIR` variable
- Files are served via `FileResponse` — no URL expiry in local mode
- Path traversal prevention: export paths are constructed entirely server-side from UUIDs and validated format names

### 7.3 Report Versioning

`ResearchReport` currently has `UNIQUE(run_id)` constraint — only one report per run. Phase 5 removes this constraint and adds `version_number`. A `report_versions` table archives prior versions when `revise_report` runs. The current (latest) version remains in `research_reports`.

---

## 8. Frontend State Management

**Decision: No state management library added.**

The existing pattern of per-component `useState` + `useEffect` is sufficient for Phase 5. The workspace has a single root `ResearchWorkspace` component that holds run state and passes it down. SSE events update local component state via a `useLiveActivity` custom hook.

A global state library (Zustand, Jotai) would only be justified if multiple disconnected parts of the UI need to share the same live state simultaneously. In the current architecture, all Phase 5 live state is local to the workspace page.

---

## 9. Interaction Between Phases

### 9.1 Phase 4 → Phase 5 Dependencies

| Phase 4 Asset | Phase 5 Usage |
|--------------|--------------|
| `AgentExecutionEvent` model | SSE replay source; all events persisted |
| `GET /runs/{id}/activity` | Used for SSE reconnect replay |
| `ResearchRun.current_stage` | Progress tracking source |
| `ResearchTask.status` | Task-level progress calculation |
| `CriticReview.review_status` | Approval trigger decision |
| `ResearchReport` (upsert logic) | Report versioning must extend this |
| `Citation.apa_formatted` | Report export citation rendering |
| `ClaimVerification` records | Evidence Viewer drill-down |
| LangGraph checkpointer | Approval resume via graph.ainvoke |

### 9.2 No Breaking Changes Policy

Phase 5 must not break any Phase 1–4 functionality. All new backend changes must be additive:
- New tables via new Alembic migrations (H, I, J)
- New API routes in new files (`approvals.py`, `exports.py`)
- New SSE endpoint added to `runs.py` (does not modify existing endpoints)
- New nodes in LangGraph graph (interrupt targets only; existing nodes unmodified)
