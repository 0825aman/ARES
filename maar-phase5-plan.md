# MAAR Phase 5 — Master Plan

## Multi-Agent Autonomous Researcher — Complete Research Experience

---

## Overview

Phase 5 delivers the live, interactive research experience layer for the MAAR platform. It transforms the Phase 4 application — which has a working multi-agent research graph but only static REST-polled panels — into a real-time, fully interactive system where the user can watch research unfold, make human approval decisions, explore collected evidence, and export structured research reports.

**Status:** Planning complete. Awaiting implementation approval.

---

## Scope

Phase 5 adds:

1. **Server-Sent Events stream** — real-time push of all graph events to the frontend
2. **Live workspace panels** — AgentActivityFeed, RunStatusCard, SourcePanel, EvidenceExplorer all update live via SSE
3. **Source Explorer** — filter, search, and inspect sources with a detail drawer
4. **Evidence Viewer** — filter by type and relevance, inspect evidence, cross-link to sources and claims
5. **Human Approval Workflow** — two LangGraph `interrupt_before` checkpoints with full frontend approve/reject/revise UI
6. **Report Export** — generate and download research reports as PDF, DOCX, or Markdown
7. **Report Versioning** — multiple report versions when revision loops occur
8. **Complete workspace integration** — all panels, tabs, and state transitions working together

**Does NOT include:** Authentication, cloud hosting, Redis, background task queues, mobile app, multi-user support.

---

## Architecture Summary

```
Browser (Next.js)
  └─ Workspace Page
       ├─ useSSE hook  ──── GET /api/v1/runs/{id}/stream ────►  SSEManager (asyncio.Queue fan-out)
       │                                                               │
       │                                                         Publishes from:
       │                                                           - AgentExecutionEvent insert
       │                                                           - ResearchRun status change
       │                                                           - ResearchSource insert
       │                                                           - Evidence insert
       │                                                           - ApprovalRequest create/resolve
       │
       ├─ RunStatusCard         subscribes: run_status_changed
       ├─ MultiAgentStatusCard  subscribes: agent_status_changed
       ├─ AgentActivityFeed     subscribes: activity_event
       ├─ SourcePanel           subscribes: source_added
       ├─ EvidenceExplorer      subscribes: evidence_added
       ├─ ApprovalBanner        subscribes: approval_required / approval_resolved
       │
       ├─ ApprovalModal  ──── POST /runs/{id}/approval/{aid}/decide ──► ApprovalService
       │                                                                      └─ graph.ainvoke (resume)
       │
       └─ ExportPanel    ──── POST /runs/{id}/export ──────────────► ExportService
                                                                          ├─ reportlab → PDF
                                                                          ├─ python-docx → DOCX
                                                                          └─ string format → MD
```

---

## Planning Documents

| # | Document | Status |
|---|---|---|
| 40 | Phase 5 Requirements | ✅ Complete |
| 41 | Phase 5 Technical Architecture | ✅ Complete |
| 42 | Live Activity and Progress Design | ✅ Complete |
| 43 | Source Explorer and Evidence Viewer Design | ✅ Complete |
| 44 | Human Approval Workflow Design | ✅ Complete |
| 45 | Report Generation and Export Design | ✅ Complete |
| 46 | Frontend Research Workspace Specification | ✅ Complete |
| 47 | Backend API Specification | ✅ Complete |
| 48 | Database and Persistence Changes | ✅ Complete |
| 49 | Testing, Security, and Acceptance Criteria | ✅ Complete |
| 50 | Implementation Roadmap and Architectural Decisions | ✅ Complete |

---

## Database Changes Summary

Three Alembic migrations (H, I, J) are required:

| Migration | Changes |
|---|---|
| H | `sequence` column on `agent_execution_events`; new `approval_requests` table |
| I | `version_number` + `is_current` on `research_reports`; relax UNIQUE constraint; new `report_versions` table |
| J | New `export_records` table |

---

## New Dependencies

| Package | Purpose | Side | Added in |
|---|---|---|---|
| `sse-starlette` | SSE endpoint support | Backend | M5.1 |
| `reportlab` | PDF generation | Backend | M5.6 |

No new frontend dependencies required. All needed shadcn/ui components are already installed.

---

## Module Sequence

| Module | Description | Key Deliverable |
|---|---|---|
| **M5.1** | Backend SSE stream | Working `GET /runs/{id}/stream` endpoint |
| **M5.2** | Live frontend updates | `useSSE` hook; polling removed from activity feed |
| **M5.3** | Source Explorer | Filter + drawer + live source updates |
| **M5.4** | Evidence Viewer | Filter + drawer + live evidence updates |
| **M5.5** | Human Approval | Interrupt checkpoints + approval UI |
| **M5.6** | Report Export | PDF/DOCX/MD export + versioning |
| **M5.7** | Workspace Integration | All panels + tabs + state transitions |
| **M5.8** | Polish + Testing | All tests pass; build clean |

---

## Sub-Tasks for Implementation

Each sub-task maps to one module. Implement one at a time.

### [x] Sub-Task 1: M5.1 — Backend SSE Infrastructure

**Intent:** Build the SSE server infrastructure — fan-out manager, sequence numbering, stream endpoint, and integration hooks.

**Expected Outcomes:**
- `GET /runs/{run_id}/stream` returns `text/event-stream`
- Events published when agent events, run status, sources, or evidence change
- `Last-Event-ID` replay works
- Multiple concurrent clients receive the same events

**Todo List:**
1. Add `sse-starlette` to `requirements.txt`
2. Run Alembic Migration H
3. Add `sequence` column to `AgentExecutionEvent` ORM model
4. Create `ApprovalRequest` ORM model
5. Create `SSEManager` service (`sse_manager.py`)
6. Update `AgentExecutionEvent` creation to assign sequence via `SELECT MAX(sequence)+1`
7. Create SSE router with stream endpoint, heartbeat, and replay
8. Register router
9. Hook SSE publish calls into event creation paths for all event types
10. Write and pass all SSE stream + fan-out tests

**Relevant files:**
- `backend/app/models/event.py`
- `backend/app/services/event_service.py`
- `backend/app/api/v1/routes/sse.py` (new)
- `backend/app/api/v1/router.py`
- `backend/docs/42_LIVE_ACTIVITY_AND_PROGRESS_DESIGN.md`
- `maar/docs/47_BACKEND_API_SPECIFICATION.md`
- `maar/docs/48_DATABASE_AND_PERSISTENCE_CHANGES.md`

**Status:** [ ] pending

---

### [x] Sub-Task 2: M5.2 — Live Frontend Activity

**Intent:** Replace REST polling in workspace components with SSE-driven updates.

**Expected Outcomes:**
- `useSSE` hook manages one EventSource per workspace
- AgentActivityFeed, RunStatusCard, MultiAgentStatusCard receive live events
- 60s polling fallback activates when SSE disconnects
- SSE connection indicator visible in workspace header

**Todo List:**
1. Create `useSSE.ts` hook (fetch-based, supports Last-Event-ID header)
2. Create `SSEConnectionIndicator.tsx`
3. Update `AgentActivityFeed.tsx` — remove setInterval polling, subscribe to `activity_event`
4. Update `RunStatusCard.tsx` — subscribe to `run_status_changed`, add `awaiting_approval` status style
5. Update `MultiAgentStatusCard.tsx` — subscribe to `agent_status_changed`
6. Update workspace page — single `useSSE` instance, pass callbacks to children
7. Write and pass all `useSSE` hook tests

**Relevant files:**
- `maar/frontend/src/lib/hooks/useSSE.ts` (new)
- `maar/frontend/src/components/workspace/AgentActivityFeed.tsx`
- `maar/frontend/src/components/workspace/RunStatusCard.tsx`
- `maar/frontend/src/components/workspace/MultiAgentStatusCard.tsx`
- `maar/docs/42_LIVE_ACTIVITY_AND_PROGRESS_DESIGN.md`
- `maar/docs/46_FRONTEND_RESEARCH_WORKSPACE_SPECIFICATION.md`

**Status:** [x] done

---

### [x] Sub-Task 3: M5.3 — Source Explorer

**Intent:** Upgrade the Source Explorer with filtering, a detail drawer, pagination, and live SSE updates.

**Expected Outcomes:**
- Source panel has filter bar (content type, reliability, text search)
- Clicking a source opens a Sheet drawer with full detail and derived evidence
- New sources appear in real time from SSE
- Load-more pagination works

**Todo List:**
1. Create `SourceDetailDrawer.tsx`
2. Update `SourcePanel.tsx` — add filter bar, pagination, SSE subscription, click handler
3. Wire cross-link from drawer evidence list to Evidence Viewer
4. Write and pass all Source Explorer tests

**Relevant files:**
- `maar/frontend/src/components/workspace/SourcePanel.tsx`
- `maar/docs/43_SOURCE_EXPLORER_AND_EVIDENCE_VIEWER_DESIGN.md`

**Status:** [ ] pending

---

### [x] Sub-Task 4: M5.4 — Evidence Viewer

**Intent:** Upgrade the Evidence Viewer with filtering, a detail drawer, and live SSE updates.

**Expected Outcomes:**
- Evidence panel has filter bar (type, relevance, claim linkage)
- Clicking evidence opens a Sheet drawer with claim and source cross-links
- New evidence appears in real time from SSE
- Evidence type colour coding applied

**Todo List:**
1. Create `EvidenceDetailDrawer.tsx`
2. Update `EvidenceExplorer.tsx` — add filter bar, SSE subscription, click handler, colour coding
3. Wire cross-link from drawer to `SourceDetailDrawer` and `ClaimVerificationPanel`
4. Write and pass all Evidence Viewer tests

**Relevant files:**
- `maar/frontend/src/components/workspace/EvidenceExplorer.tsx`
- `maar/docs/43_SOURCE_EXPLORER_AND_EVIDENCE_VIEWER_DESIGN.md`

**Status:** [ ] pending

---

### [x] Sub-Task 5: M5.5 — Human Approval Workflow

**Intent:** Add two LangGraph interrupt checkpoints and the full approval UI — banner, modal, decision API.

**Expected Outcomes:**
- Research runs pause at planning and critic review checkpoints
- Frontend shows approval banner with content-specific prompt
- User can approve, reject, or request revision
- Graph resumes correctly after each decision type
- Expired approvals handled gracefully

**Todo List:**
1. Create `ApprovalRequest` ORM model and run Migration H (already in M5.1 — confirm done)
2. Create `ApprovalService`
3. Update `workflow.py` interrupt_before list
4. Add `planning_complete_node` and `critic_review_approval_node` to nodes
5. Update executor to detect suspension and create ApprovalRequest
6. Create approval API routes and register router
7. Wire SSE publish for `approval_required` and `approval_resolved`
8. Create `ApprovalBanner.tsx` and `ApprovalModal.tsx`
9. Update workspace page — approval state, SSE subscriptions, fallback poll
10. Write and pass all approval workflow tests (backend + frontend)

**Relevant files:**
- `maar/backend/app/graph/workflow.py`
- `maar/backend/app/graph/executor.py`
- `maar/backend/app/graph/nodes.py`
- `maar/docs/44_HUMAN_APPROVAL_WORKFLOW_DESIGN.md`

**Status:** [ ] pending

---

### [x] Sub-Task 6: M5.6 — Report Generation and Export

**Intent:** Generate downloadable research report files (PDF, DOCX, Markdown) and implement report versioning.

**Expected Outcomes:**
- POST export endpoint generates file and returns download URL
- All three formats produce valid downloadable files
- Download endpoint returns binary file with correct MIME type
- Report versioning archives previous version before creating new
- Export Panel visible in workspace when report exists

**Todo List:**
1. Add `reportlab` to `requirements.txt`
2. Run Alembic Migrations I and J
3. Create `ReportVersion` and `ExportRecord` ORM models
4. Update `ResearchReport` model
5. Create `ReportVersioningService`
6. Create `ExportService` (PDF, DOCX, Markdown generators)
7. Create export and report version API routes
8. Update `main.py` startup for EXPORT_DIR creation
9. Create `ExportPanel.tsx`
10. Update Report tab in workspace
11. Write and pass all export and versioning tests

**Relevant files:**
- `maar/backend/app/models/report.py`
- `maar/docs/45_REPORT_GENERATION_AND_EXPORT_DESIGN.md`
- `maar/docs/48_DATABASE_AND_PERSISTENCE_CHANGES.md`

**Status:** [ ] pending

---

### [x] Sub-Task 7: M5.7 — Complete Workspace Integration

**Intent:** Wire all Phase 5 components together into a coherent workspace; verify all state transitions.

**Expected Outcomes:**
- Workspace cross-links between Source, Evidence, Claim panels working
- All five tabs render correctly in all run states
- Live badges on Source and Evidence tabs
- No layout issues at common breakpoints
- Approval banner lifecycle working end to end

**Todo List:**
1. Add `activeSourceId` and `activeEvidenceId` state to workspace page
2. Create `LiveBadge.tsx` and wire to Source / Evidence tab headers
3. Verify all run status transitions render correctly in all workspace components
4. Test cross-link: Evidence drawer → Source drawer
5. Test cross-link: Evidence drawer → Claims tab
6. Verify responsive layout at 768px and 1280px
7. Write and pass workspace integration tests

**Relevant files:**
- `maar/frontend/src/app/projects/[id]/runs/[runId]/page.tsx`
- `maar/docs/46_FRONTEND_RESEARCH_WORKSPACE_SPECIFICATION.md`

**Status:** [ ] pending

---

### [x] Sub-Task 8: M5.8 — End-to-End Testing and UX Polish

**Intent:** Validate the complete Phase 5 system, ensure all tests pass, and document known issues.

**Expected Outcomes:**
- All 271 Phase 1–4 tests still pass
- All Phase 5 tests pass
- `npm run build` succeeds with no TypeScript errors
- All acceptance criteria from document 49 satisfied
- Known issues documented

**Todo List:**
1. Run full pytest suite — fix any regressions
2. Run `npm run build` — fix any TypeScript errors
3. Review all empty states across all panels
4. Review all error states (API failure handling)
5. Review all loading skeletons
6. Manually test complete research run with SSE DevTools open
7. Manually test approval workflow end to end
8. Manually test all three export formats
9. Write `PHASE_5_KNOWN_ISSUES.md`
10. Confirm all acceptance criteria checkboxes in document 49

**Status:** [ ] pending

---

## Key Technical Constraints

1. `sse-starlette` for SSE — not WebSocket, not native EventSource alone
2. `reportlab` for PDF — not weasyprint (requires system libs)
3. `asyncio.to_thread` for export generation — not synchronous blocking
4. `python-docx` for DOCX — already installed, used in Phase 4
5. LangGraph `interrupt_before` for approval — not flag-based polling in nodes
6. In-memory `asyncio.Queue` for SSE fan-out — not Redis
7. No new frontend state management library — `useState` is sufficient
8. Three separate Alembic migrations (H, I, J) — not one large migration

---

## Instruction for Agent Implementation

When implementing, process one sub-task at a time:

1. Read the relevant planning document(s) listed under each sub-task
2. Read the relevant existing source files before modifying them
3. Implement the sub-task
4. Run tests for the completed sub-task
5. Update this plan file — mark sub-task `[x] done`
6. Report completion to user before starting the next sub-task
7. Wait for user confirmation before proceeding

Do not start M5.2 before M5.1 tests pass. Do not start M5.5 before M5.2 is confirmed working. Follow the dependency order strictly.
