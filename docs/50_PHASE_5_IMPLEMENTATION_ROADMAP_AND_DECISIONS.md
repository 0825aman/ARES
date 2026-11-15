# 50 — Phase 5 Implementation Roadmap and Architectural Decisions

## Phase 5

---

## 1. Implementation Sequence

Phase 5 is implemented in eight modules. Each module is a discrete, independently testable unit of work. Modules must be completed in the order listed — later modules depend on earlier ones.

```
M5.1 → M5.2 → M5.3 → M5.4 → M5.5 → M5.6 → M5.7 → M5.8
```

---

## 2. Module Breakdown

### M5.1 — Backend Event and Activity System (SSE)

**Depends on:** Existing Phase 4 backend (complete)

**Work items:**

1. Add `sse-starlette` to `backend/requirements.txt`
2. Run Alembic Migration H:
   - Add `sequence` column to `agent_execution_events`
   - Create `approval_requests` table
3. Update `AgentExecutionEvent` ORM model with `sequence` field
4. Create `ApprovalRequest` ORM model at `backend/app/models/approval.py`
5. Update `backend/app/models/__init__.py` with new imports
6. Create `SSEManager` class at `backend/app/services/sse_manager.py`:
   - `asyncio.Queue`-based fan-out per `run_id`
   - `subscribe(run_id)` → returns async generator of events
   - `publish(run_id, event)` → pushes to all queues for that run
   - `unsubscribe(run_id, queue)` → removes queue from fan-out map
7. Create `EventSequenceService` in `backend/app/services/event_service.py`:
   - `next_sequence(db, run_id)` → `SELECT MAX(sequence)+1` within transaction
8. Update `AgentExecutionEvent` creation path to set `sequence`
9. Create SSE router at `backend/app/api/v1/routes/sse.py`:
   - `GET /runs/{run_id}/stream` endpoint using `EventSourceResponse`
   - DB replay on `Last-Event-ID`
   - Heartbeat task
10. Register SSE router in `backend/app/api/v1/router.py`
11. Hook SSE publish calls into existing event creation points:
    - After `AgentExecutionEvent` insert → emit `activity_event`
    - After `ResearchRun.status` update → emit `run_status_changed`
    - After `ResearchSource` insert → emit `source_added`
    - After `Evidence` insert → emit `evidence_added`
12. Write `backend/tests/test_sse_stream.py` and `test_sse_fanout.py`

**Acceptance:** All SSE stream tests pass; events visible in browser DevTools EventStream panel.

---

### M5.2 — Live Frontend Activity and Progress Tracking

**Depends on:** M5.1 (SSE backend endpoint working)

**Work items:**

1. Create `frontend/src/lib/hooks/useSSE.ts`:
   - Fetch-based reconnecting SSE client (not native `EventSource` — needs custom headers)
   - Manages `connected` state
   - Accepts event handler callbacks by event type
   - Sends `Last-Event-ID` on reconnect
2. Create `frontend/src/components/workspace/SSEConnectionIndicator.tsx`
3. Update `AgentActivityFeed.tsx`:
   - Remove `setInterval` polling
   - Subscribe to `activity_event` via `useSSE`
   - Keep 60s polling as fallback
   - Auto-scroll behaviour
4. Update `RunStatusCard.tsx`:
   - Subscribe to `run_status_changed` via `useSSE`
   - Handle `awaiting_approval` status with amber styling
5. Update `MultiAgentStatusCard.tsx`:
   - Subscribe to `agent_status_changed` via `useSSE`
6. Update workspace page to instantiate `useSSE` once and pass callbacks down
7. Write `frontend/src/lib/hooks/__tests__/useSSE.test.ts`

**Acceptance:** Activity feed updates in real time; no polling network calls visible during active run; SSE indicator turns green on connect.

---

### M5.3 — Source Explorer

**Depends on:** M5.1 (for SSE `source_added`), M5.2 (for live badge update)

**Work items:**

1. Create `SourceDetailDrawer.tsx` using shadcn/ui `Sheet`
2. Update `SourcePanel.tsx`:
   - Add filter bar (content type chips, reliability slider, text search)
   - Add "Load more" pagination
   - Wire SSE `source_added` events to prepend new rows
   - Add click handler → opens `SourceDetailDrawer`
   - Add live count badge on tab
3. Add cross-link support: source detail drawer lists derived evidence items
4. Write `frontend/src/components/workspace/__tests__/SourcePanel.test.tsx`

**Acceptance:** Source filter, drawer, live update, and load-more all work end to end.

---

### M5.4 — Evidence Viewer

**Depends on:** M5.1, M5.2, M5.3 (cross-link to source drawer)

**Work items:**

1. Create `EvidenceDetailDrawer.tsx` using shadcn/ui `Sheet`
2. Update `EvidenceExplorer.tsx`:
   - Add filter bar (evidence type chips, relevance slider, linked-claim toggle)
   - Wire SSE `evidence_added` events
   - Add click handler → opens `EvidenceDetailDrawer`
   - Add live count badge on tab
3. Add cross-link: evidence drawer → opens `SourceDetailDrawer` for parent source
4. Add cross-link: evidence drawer → opens `ClaimVerificationPanel` filtered to linked claim
5. Write `frontend/src/components/workspace/__tests__/EvidenceExplorer.test.tsx`

**Acceptance:** Evidence filter, drawer, live update, and cross-links all work end to end.

---

### M5.5 — Human Approval Workflow

**Depends on:** M5.1 (SSE for `approval_required` event), M5.2 (workspace state for approval)

**Work items:**

**Backend:**
1. Create `ApprovalService` at `backend/app/services/approval_service.py`:
   - `create_approval(db, run_id, checkpoint_name, node_name, context_snapshot)` → `ApprovalRequest`
   - `decide(db, approval_id, decision, notes)` → resumes graph, updates run
   - `get_pending(db, run_id)` → `ApprovalRequest | None`
   - `expire_check(db, approval_id)` → marks expired if past `expires_at`
2. Update `backend/app/graph/workflow.py`:
   - Change `interrupt_before=[]` to `interrupt_before=["planning_complete_node", "critic_review_approval_node"]`
3. Add `planning_complete_node` and `critic_review_approval_node` nodes to `backend/app/graph/nodes.py`
4. Update graph builder in `workflow.py` to include new nodes in the execution path
5. Update `AgentExecutor` to detect suspension (`state.next` non-empty) and create `ApprovalRequest`
6. Create approval API routes at `backend/app/api/v1/routes/approvals.py`:
   - `GET /runs/{run_id}/approval`
   - `POST /runs/{run_id}/approval/{approval_id}/decide`
   - `GET /runs/{run_id}/approvals`
7. Register approval router
8. Wire SSE publish: after `create_approval` → emit `approval_required`; after `decide` → emit `approval_resolved`
9. Write `backend/tests/test_approval_workflow.py`

**Frontend:**
10. Create `ApprovalBanner.tsx`
11. Create `ApprovalModal.tsx` using shadcn/ui `Dialog`
12. Update workspace page:
    - Add `pendingApproval` state
    - Subscribe to SSE `approval_required` and `approval_resolved` events
    - Poll `GET /runs/{run_id}/approval` as fallback on workspace open
    - Render `ApprovalBanner` conditionally
13. Write `frontend/src/components/workspace/__tests__/ApprovalBanner.test.tsx`

**Acceptance:** Full approval round-trip works — run pauses, frontend shows banner, user approves, run resumes.

---

### M5.6 — Report Generation and Export

**Depends on:** M5.5 (report versioning triggered by revision loops in approval workflow)

**Work items:**

**Backend:**
1. Add `reportlab` to `backend/requirements.txt`
2. Run Alembic Migration I (report versioning columns) and Migration J (export_records)
3. Create `ReportVersion` ORM model at `backend/app/models/report_version.py`
4. Create `ExportRecord` ORM model at `backend/app/models/export_record.py`
5. Update `ResearchReport` model with `version_number` and `is_current` columns
6. Create `ReportVersioningService` in `backend/app/services/report_service.py`:
   - `create_new_version(db, run_id, report_data)` → archives current, creates new version
7. Create `ExportService` at `backend/app/services/export_service.py`:
   - `generate_pdf(report, output_path)` using reportlab
   - `generate_docx(report, output_path)` using python-docx
   - `generate_markdown(report, output_path)` pure string formatting
8. Create export and report version API routes at `backend/app/api/v1/routes/exports.py`:
   - `POST /runs/{run_id}/export`
   - `GET /runs/{run_id}/export/{export_id}/download`
   - `GET /runs/{run_id}/exports`
   - `GET /runs/{run_id}/reports`
9. Update `main.py` startup to create `EXPORT_DIR`
10. Write `backend/tests/test_export.py` and `test_report_versioning.py`

**Frontend:**
11. Create `ExportPanel.tsx`
12. Update `ResearchReportView` display area to show version badge
13. Update Report tab in workspace to render `ExportPanel` below `ResearchReportView`
14. Write `frontend/src/components/workspace/__tests__/ExportPanel.test.tsx`

**Acceptance:** All three export formats generate downloadable files; version history visible in workspace.

---

### M5.7 — Complete Research Workspace Integration

**Depends on:** M5.1–M5.6 all complete

**Work items:**

1. Audit workspace page for any remaining REST polling loops that should be replaced by SSE
2. Add `LiveBadge` component and wire to Source and Evidence tab headers
3. Implement cross-link workspace state:
   - `activeSourceId` state on workspace page
   - `activeEvidenceId` state on workspace page
   - `SourceDetailDrawer` and `EvidenceDetailDrawer` controlled by these states
4. Verify all five tabs render correct content in all run states (not_started, running, awaiting_approval, completed, failed)
5. Verify approval banner appears and hides correctly for all state transitions
6. Verify responsive layout at 768px and 1280px breakpoints
7. Write `frontend/src/components/workspace/__tests__/WorkspacePage.integration.test.tsx`

**Acceptance:** Complete workspace operates as specified in document 46 without layout issues or missing state transitions.

---

### M5.8 — End-to-End Testing and UX Polish

**Depends on:** M5.7 complete

**Work items:**

1. Run full test suite — all 271 existing tests plus all new Phase 5 tests must pass
2. Run `npm run build` — no TypeScript errors, no compilation warnings
3. Review all empty states — every panel must have meaningful copy
4. Review all error states — API failures must display user-friendly messages
5. Review loading skeletons — all panels must show skeletons before first data load
6. Run a complete research run end-to-end with the SSE stream open in DevTools and verify all event types appear
7. Test approval workflow: start a run, wait for approval banner, approve, verify continuation
8. Generate exports in all three formats and verify downloads
9. Verify SSE reconnection: disconnect network briefly and reconnect; verify missed events are replayed
10. Document any known limitations or deferred items in `PHASE_5_KNOWN_ISSUES.md`

**Acceptance:** All acceptance criteria from document 49 satisfied; `npm run build` passes; all tests pass.

---

## 3. Dependency Graph

```
M5.1  ──────────────────────────────────────────────────────────────────►
         M5.2  ────────────────────────────────────────────────────────►
               M5.3  ──────────────────────────────────────────────────►
               M5.4  ──────────────────────────────────────────────────►
         M5.2  M5.1
               ──► M5.5  ──────────────────────────────────────────────►
                         M5.6  ─────────────────────────────────────────►
                               M5.7  ────────────────────────────────────►
                                     M5.8
```

---

## 4. Architectural Decisions

### Decision 1: SSE over WebSocket

**Options considered:**
- Native browser WebSocket
- `python-socketio`
- Server-Sent Events via `sse-starlette`

**Decision:** SSE.

**Rationale:**
- Research updates are unidirectional (server → client). User actions (start run, submit approval) use REST calls, not the stream.
- SSE is an HTTP/1.1 standard — no upgrade handshake, no reconnection protocol to implement on the server.
- Native `EventSource` auto-reconnects; `Last-Event-ID` gives replay for free.
- `sse-starlette` integrates directly with FastAPI's ASGI stack with minimal boilerplate.
- WebSocket would add complexity without benefit for this use case.

**Trade-off:** SSE is HTTP/1.1 and carries per-connection overhead with HTTP/2 multiplexing disabled. At one local user per server, this is irrelevant.

---

### Decision 2: Fetch-based SSE client over native EventSource

**Problem:** Native `EventSource` does not support custom request headers, so `Last-Event-ID` must come from the URL query parameter in the native implementation. This works but pollutes URLs.

**Decision:** Use a fetch-based SSE client in the frontend (small utility — no external library required).

**Rationale:**
- A fetch-based client allows sending `Last-Event-ID` as a proper HTTP header
- Avoids adding a third-party library dependency for SSE
- The implementation is ~50 lines

---

### Decision 3: Synchronous export generation

**Options considered:**
- Synchronous (blocking in route handler)
- FastAPI `BackgroundTasks`
- `asyncio.to_thread` for CPU-bound PDF work

**Decision:** `asyncio.to_thread` wrapping synchronous export calls.

**Rationale:**
- reportlab and python-docx are synchronous libraries
- Running them directly in an async route would block the event loop
- `asyncio.to_thread` offloads to a thread pool without requiring a separate task queue
- Files are typically < 100KB; generation takes < 500ms
- No background task polling, no task status endpoint complexity

**Correction from initial spec:** Document 45 specified "synchronous". The correct implementation is `asyncio.to_thread` — still a single HTTP request/response cycle from the client's perspective, but non-blocking on the server.

---

### Decision 4: LangGraph interrupt_before for human approval

**Options considered:**
- Poll a `pause_requested` flag in each node
- Use LangGraph `interrupt_before`
- Store approval decisions in shared state and check them in supervisor routing

**Decision:** `interrupt_before` on two dedicated nodes.

**Rationale:**
- LangGraph's `interrupt_before` is designed precisely for this pattern — pause before a node, resume with input
- The checkpointer (`AsyncSqliteSaver`) persists graph state across the pause; no additional state serialisation required
- Clean separation: the interrupt nodes are minimal (no business logic) — just suspension points
- Resume via `graph.ainvoke` with the same `thread_id` is the idiomatic LangGraph pattern

**Trade-off:** If the application restarts while a graph is suspended, the checkpoint survives in `maar_checkpoints.db` and the run can be resumed. However, the in-memory SSE queue for that run is lost. The `ApprovalRequest` record in the application DB ensures the frontend can still display the approval state after a restart via polling fallback.

---

### Decision 5: In-memory Queue for SSE fan-out

**Options considered:**
- Redis pub/sub
- Database polling
- In-memory `asyncio.Queue` per connected client

**Decision:** In-memory `asyncio.Queue`.

**Rationale:**
- Single server process, single local user — no need for distributed pub/sub
- Redis would be a mandatory infrastructure dependency for a local-only app
- Database polling adds latency and DB load
- `asyncio.Queue` fan-out is correct, efficient, and fits in ~80 lines
- Queues are cleaned up when clients disconnect

**Trade-off:** If the server restarts, all queued events are lost. The `Last-Event-ID` replay from DB mitigates this — clients reconnect and receive all persisted events from their last-seen sequence number.

---

### Decision 6: Three Alembic migrations (H, I, J) instead of one

**Rationale:** Separate migrations allow partial rollback if one schema change causes issues. Migration H (events + approvals) can be deployed and tested before report versioning (I) or exports (J) are implemented. This matches the module implementation sequence.

---

### Decision 7: ReportVersion as archive table, not versioned main table

**Options considered:**
- Soft-delete with version_number on main table (chosen approach)
- Separate `report_versions` table with full content; main table always points to current

**Decision:** `is_current` flag on main table + `report_versions` archive.

**Rationale:**
- `GET /reports?run_id=` with `WHERE is_current = TRUE` returns the current report with zero joins
- Full content duplication in `report_versions` is justified — reports are text-heavy but small (< 50KB each); storing the snapshot avoids reconstructing history
- The main `research_reports` table retains all version rows for referential integrity with `export_records`

---

## 5. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| SSE connection dropped by proxy | Low (localhost) | Medium | Heartbeat + 60s polling fallback |
| Graph suspension detected incorrectly | Medium | High | Explicit check of `state.next` after every `ainvoke` call |
| Export file path conflict (same run, same format, fast re-export) | Low | Low | Timestamp in filename guarantees uniqueness |
| SQLite table rebuild migration fails on corrupted DB | Low | High | Backup DB before running migrations; include in setup docs |
| `asyncio.to_thread` pool exhaustion under many simultaneous exports | Very low (local, 1 user) | Low | Non-issue for Phase 5 |

---

## 6. Files Added in Phase 5 (Complete List)

### Backend — New files

```
backend/app/models/approval.py
backend/app/models/report_version.py
backend/app/models/export_record.py
backend/app/services/sse_manager.py
backend/app/services/approval_service.py
backend/app/services/export_service.py
backend/app/api/v1/routes/sse.py
backend/app/api/v1/routes/approvals.py
backend/app/api/v1/routes/exports.py
backend/alembic/versions/h8c9d0e1f2a3_phase5_migration_h.py
backend/alembic/versions/i9d0e1f2a3b4_phase5_migration_i.py
backend/alembic/versions/j0e1f2a3b4c5_phase5_migration_j.py
backend/tests/test_sse_stream.py
backend/tests/test_sse_fanout.py
backend/tests/test_approval_workflow.py
backend/tests/test_export.py
backend/tests/test_report_versioning.py
```

### Backend — Modified files

```
backend/requirements.txt                    (+ sse-starlette, + reportlab)
backend/app/models/__init__.py              (+ new model imports)
backend/app/models/event.py                 (+ sequence column)
backend/app/models/report.py                (+ version_number, is_current columns)
backend/app/models/run.py                   (+ approval_requests relationship)
backend/app/graph/workflow.py               (interrupt_before updated)
backend/app/graph/nodes.py                  (+ 2 new nodes)
backend/app/graph/executor.py               (+ suspension detection + resume logic)
backend/app/services/event_service.py       (+ sequence assignment)
backend/app/api/v1/router.py                (+ 3 new routers registered)
backend/app/core/config.py                  (+ EXPORT_DIR, APPROVAL_EXPIRY_HOURS)
backend/app/main.py                         (+ startup: create EXPORT_DIR)
```

### Frontend — New files

```
frontend/src/lib/hooks/useSSE.ts
frontend/src/components/workspace/SSEConnectionIndicator.tsx
frontend/src/components/workspace/ApprovalBanner.tsx
frontend/src/components/workspace/ApprovalModal.tsx
frontend/src/components/workspace/SourceDetailDrawer.tsx
frontend/src/components/workspace/EvidenceDetailDrawer.tsx
frontend/src/components/workspace/ExportPanel.tsx
frontend/src/components/workspace/LiveBadge.tsx
frontend/src/lib/hooks/__tests__/useSSE.test.ts
frontend/src/components/workspace/__tests__/ApprovalBanner.test.tsx
frontend/src/components/workspace/__tests__/SourcePanel.test.tsx
frontend/src/components/workspace/__tests__/EvidenceExplorer.test.tsx
frontend/src/components/workspace/__tests__/ExportPanel.test.tsx
frontend/src/components/workspace/__tests__/WorkspacePage.integration.test.tsx
```

### Frontend — Modified files

```
frontend/src/components/workspace/AgentActivityFeed.tsx    (SSE, polling removal)
frontend/src/components/workspace/RunStatusCard.tsx        (SSE, awaiting_approval)
frontend/src/components/workspace/MultiAgentStatusCard.tsx (SSE)
frontend/src/components/workspace/SourcePanel.tsx          (filter, drawer, live)
frontend/src/components/workspace/EvidenceExplorer.tsx     (filter, drawer, live)
frontend/src/app/projects/[id]/runs/[runId]/page.tsx       (approval state, useSSE, drawers)
```

### Docs — New files

```
maar/docs/PHASE_5_KNOWN_ISSUES.md    (created during M5.8)
```
