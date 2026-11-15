# 49 — Testing, Security, and Acceptance Criteria

## Phase 5

---

## 1. Overview

This document defines the testing strategy, test cases, and acceptance criteria for Phase 5. It is structured around the eight modules (M5.1–M5.8) and covers backend, frontend, and integration testing.

Phase 4 delivered 271 passing tests. Phase 5 must maintain all existing tests and add new tests for every new capability.

---

## 2. Backend Testing

### 2.1 Test framework

All backend tests use `pytest` with `httpx.AsyncClient` for async endpoint testing. Fixtures follow the existing Phase 4 patterns in `backend/tests/`.

### 2.2 SSE Stream Tests (M5.1)

**Test file:** `backend/tests/test_sse_stream.py`

| Test Case | Description | Expected Result |
|---|---|---|
| `test_sse_stream_opens` | GET `/runs/{run_id}/stream` — valid run | HTTP 200, content-type `text/event-stream` |
| `test_sse_stream_run_not_found` | GET `/runs/invalid-id/stream` | HTTP 404 |
| `test_sse_connected_event` | First message on stream open | Event type `connected` with `run_id` |
| `test_sse_heartbeat_emitted` | Wait > 30s (mocked time) | `heartbeat` event emitted |
| `test_sse_last_event_id_replay` | Open stream with `Last-Event-ID: 5` | Only events with sequence > 5 replayed |
| `test_sse_activity_event_forwarded` | New `AgentExecutionEvent` inserted | `activity_event` appears on stream |
| `test_sse_run_completed_closes_stream` | Run status → completed | `run_completed` event emitted, stream closes |

### 2.3 Approval Workflow Tests (M5.5)

**Test file:** `backend/tests/test_approval_workflow.py`

| Test Case | Description | Expected Result |
|---|---|---|
| `test_get_approval_no_pending` | GET approval for run with no pending | HTTP 200, body `null` |
| `test_get_approval_pending` | GET approval with pending record | HTTP 200, full approval record |
| `test_decide_approved` | POST decide with `approved` | HTTP 200, `decision = approved`, `decided_at` set |
| `test_decide_rejected` | POST decide with `rejected` | HTTP 200, run status → `failed` |
| `test_decide_revision_requested` | POST decide with `revision_requested` and notes | HTTP 200, notes persisted |
| `test_decide_already_decided` | POST decide on already-decided approval | HTTP 409 |
| `test_decide_expired` | POST decide on expired approval | HTTP 409 |
| `test_decide_invalid_decision` | POST decide with `"maybe"` | HTTP 422 |
| `test_decide_notes_too_long` | POST decide with notes > 2000 chars | HTTP 422 |
| `test_get_approval_history` | GET all approvals for a run | HTTP 200, list of all records |
| `test_approval_run_id_not_found` | POST decide for non-existent run | HTTP 404 |

### 2.4 Export Tests (M5.6)

**Test file:** `backend/tests/test_export.py`

| Test Case | Description | Expected Result |
|---|---|---|
| `test_export_pdf` | POST export with `format: pdf` | HTTP 200, status `ready`, file exists on disk |
| `test_export_docx` | POST export with `format: docx` | HTTP 200, status `ready`, file exists on disk |
| `test_export_markdown` | POST export with `format: markdown` | HTTP 200, status `ready`, file exists on disk |
| `test_export_invalid_format` | POST export with `format: html` | HTTP 422 |
| `test_export_no_report` | POST export for run without a report | HTTP 404 |
| `test_export_download` | GET download for ready export | HTTP 200, binary response, correct content-type |
| `test_export_download_not_ready` | GET download for pending export | HTTP 409 |
| `test_export_list` | GET exports for run | HTTP 200, list of export records |
| `test_export_pdf_content` | Inspect generated PDF bytes | Contains report title, executive summary |
| `test_export_docx_content` | Inspect generated DOCX | Document has expected paragraph count |
| `test_export_markdown_content` | Read generated .md file | Contains all section headers |

**Note on file cleanup:** Export tests write files to a temporary directory created by the test fixture and removed in teardown.

### 2.5 Report Versioning Tests (M5.6)

**Test file:** `backend/tests/test_report_versioning.py`

| Test Case | Description | Expected Result |
|---|---|---|
| `test_report_version_1_default` | New report created | `version_number = 1`, `is_current = True` |
| `test_report_second_version` | Second report created for same run | Old report `is_current = False`, new `version_number = 2` |
| `test_report_archive_snapshot` | After version bump | `report_versions` contains snapshot of v1 |
| `test_get_reports_for_run` | GET `/runs/{run_id}/reports` | Returns both versions, current first |

### 2.6 SSE Fan-Out Tests (M5.1)

**Test file:** `backend/tests/test_sse_fanout.py`

| Test Case | Description | Expected Result |
|---|---|---|
| `test_multiple_clients_same_run` | Two SSE clients on same run_id | Both receive the same events |
| `test_events_not_cross_run` | Two clients on different runs | Each receives only its own run's events |
| `test_client_disconnect_cleanup` | SSE client disconnects mid-stream | Queue is removed from fan-out manager |

---

## 3. Frontend Testing

### 3.1 Test framework

Frontend tests use Vitest (already configured) with React Testing Library.

### 3.2 SSE Hook Tests (M5.2)

**Test file:** `frontend/src/lib/hooks/__tests__/useSSE.test.ts`

| Test Case | Expected Result |
|---|---|
| Hook opens EventSource on mount | `EventSource` constructed with correct URL |
| Hook exposes `connected: true` after first message | State updated |
| Hook calls provided callbacks on event type match | Callback invoked with parsed data |
| Hook reconnects after disconnect | `EventSource` recreated |
| Hook cleans up on unmount | `EventSource.close()` called |

### 3.3 Approval Components

**Test file:** `frontend/src/components/workspace/__tests__/ApprovalBanner.test.tsx`

| Test Case | Expected Result |
|---|---|
| Banner renders when `pendingApproval` is set | Banner element visible |
| Banner hidden when `pendingApproval` is null | No banner element |
| "View Plan & Decide" opens modal | Modal dialog appears |
| Approval decision buttons present in modal | Three buttons visible |
| Submitting approval calls POST endpoint | API call made with correct body |
| Countdown timer shows time remaining | Expiry time displayed |

### 3.4 Source Explorer Tests

**Test file:** `frontend/src/components/workspace/__tests__/SourcePanel.test.tsx`

| Test Case | Expected Result |
|---|---|
| Sources list renders from API data | Source rows rendered |
| Empty state when no sources | Empty state copy visible |
| Filter by content type hides non-matching | Filtered rows not visible |
| Clicking source row opens drawer | Sheet drawer appears |
| Source drawer shows title, URL, reliability | Detail elements rendered |
| New SSE source_added event prepends to list | New row at top |

### 3.5 Evidence Viewer Tests

**Test file:** `frontend/src/components/workspace/__tests__/EvidenceExplorer.test.tsx`

| Test Case | Expected Result |
|---|---|
| Evidence list renders | Evidence rows rendered |
| Supporting evidence has green border | Green left-border class applied |
| Contradicting evidence has red border | Red left-border class applied |
| Filter by type works | Non-matching types hidden |
| Clicking row opens detail drawer | Sheet drawer visible |
| Evidence drawer shows claim link when claim_id set | Claim link rendered |

### 3.6 Export Panel Tests

**Test file:** `frontend/src/components/workspace/__tests__/ExportPanel.test.tsx`

| Test Case | Expected Result |
|---|---|
| Export panel hidden when no report | Component not rendered |
| Three format buttons rendered | PDF, Word, Markdown buttons visible |
| Clicking PDF button calls POST export | API call made |
| Download triggered after export ready | Browser download initiated |
| Previous exports list shows existing records | Export rows rendered |
| Re-download button works | Download URL navigated |

---

## 4. Integration Testing

### 4.1 End-to-End SSE Integration

**Scenario:** Run a research run from start to completion with an SSE client connected.

**Steps:**
1. Create research project and run via API
2. Open SSE stream for the run
3. Start the run via `POST /runs/{run_id}/start`
4. Verify `run_status_changed` events arrive as the run progresses
5. Verify `activity_event` events arrive as agents execute
6. Verify `source_added` events arrive when sources are fetched
7. Verify `run_completed` event arrives and stream closes

**Acceptance:** All expected event types received in correct order; stream closes cleanly.

### 4.2 Approval Workflow Integration

**Scenario:** Run pauses for plan approval; user approves; run continues.

**Steps:**
1. Start a research run
2. Wait for `approval_required` SSE event (or poll `GET /approval`)
3. Verify `run.status === "awaiting_approval"`
4. Submit `POST /approval/{id}/decide` with `approved`
5. Verify `run.status` returns to `running`
6. Verify `approval_resolved` SSE event arrives
7. Verify run continues and eventually completes

**Acceptance:** Run completes successfully after approval without manual graph intervention.

### 4.3 Export Integration

**Scenario:** Completed run report is exported in all three formats.

**Steps:**
1. Use a completed run that has a `ResearchReport`
2. POST export with `format: pdf`; verify `status: ready` and file exists
3. GET download; verify binary PDF response
4. POST export with `format: docx`; verify file
5. POST export with `format: markdown`; verify file contains all section headers
6. GET `/runs/{run_id}/exports`; verify three records

**Acceptance:** All three formats generate valid files downloadable via API.

### 4.4 Report Versioning Integration

**Scenario:** A research run completes, requests revision, and completes again.

**Steps:**
1. Run completes, v1 report created
2. Verify `GET /runs/{run_id}/reports` returns `[{version: 1, is_current: true}]`
3. Simulate revision by calling report creation again (triggers versioning logic)
4. Verify v1 is archived in `report_versions`
5. Verify `GET /runs/{run_id}/reports` returns v1 (is_current=false) and v2 (is_current=true)

**Acceptance:** Version history intact; current report correctly identified.

---

## 5. Phase 5 Acceptance Criteria

The following criteria must all be satisfied before Phase 5 is considered complete.

### M5.1 — Backend Event and Activity System (SSE)

- [ ] `GET /runs/{run_id}/stream` returns `text/event-stream` response
- [ ] SSE stream emits `connected` event on open
- [ ] SSE stream emits `heartbeat` every 30 seconds
- [ ] SSE stream emits `activity_event` when a new agent event is persisted
- [ ] SSE stream emits `run_status_changed` when run status changes
- [ ] SSE stream emits `source_added` and `evidence_added` when new records are created
- [ ] `Last-Event-ID` header causes replay of missed events
- [ ] Multiple clients on the same run receive all events
- [ ] Stream closes cleanly when run reaches terminal state

### M5.2 — Live Frontend Activity

- [ ] `useSSE` hook connects to stream on workspace mount
- [ ] SSE connection indicator shows green when connected
- [ ] AgentActivityFeed receives and displays live events without polling
- [ ] RunStatusCard updates from SSE `run_status_changed` events
- [ ] 60s polling fallback activates when SSE is disconnected
- [ ] New SSE events auto-scroll feed when user is at bottom

### M5.3 — Source Explorer

- [ ] Source list loads from API
- [ ] Filter bar filters by content type and reliability
- [ ] Clicking source row opens detail drawer
- [ ] Detail drawer shows full source metadata and derived evidence
- [ ] New sources appear in real time via SSE
- [ ] Source count badge updates live

### M5.4 — Evidence Viewer

- [ ] Evidence list loads from API
- [ ] Evidence type filter works
- [ ] Clicking evidence row opens detail drawer
- [ ] Evidence drawer cross-links to parent source
- [ ] New evidence items appear in real time via SSE
- [ ] Evidence type colour coding applied correctly

### M5.5 — Human Approval Workflow

- [ ] Research plan generates an `ApprovalRequest` with status `pending`
- [ ] SSE emits `approval_required` event
- [ ] Workspace shows approval banner with correct content
- [ ] Approval modal opens with plan or review details
- [ ] User can approve, reject, or request revisions
- [ ] Approving resumes the graph and run continues
- [ ] Rejecting sets run status to `failed`
- [ ] Revision request resumes graph with notes
- [ ] Expired approvals return HTTP 409 on decide
- [ ] Critic review checkpoint fires when `review_status = needs_attention`

### M5.6 — Report Generation and Export

- [ ] PDF export generates valid PDF file on disk
- [ ] DOCX export generates valid Word document
- [ ] Markdown export generates well-formatted .md file
- [ ] Download endpoint returns correct MIME type and triggers browser download
- [ ] Export panel shows in workspace when report exists
- [ ] All three format buttons work from the frontend
- [ ] Report versioning creates new version on re-generation
- [ ] Previous version archived in `report_versions`
- [ ] Version selector appears when version > 1

### M5.7 — Complete Workspace Integration

- [ ] All five workspace tabs render without error
- [ ] Approval banner appears and disappears correctly
- [ ] Live badges on tabs update without full page reload
- [ ] No layout shifts when switching tabs
- [ ] Source and evidence drawers open from cross-links in other panels
- [ ] Workspace handles `run.status = awaiting_approval` visually

### M5.8 — Testing and UX Polish

- [ ] All existing 271 tests still pass
- [ ] All new Phase 5 backend tests pass
- [ ] All new Phase 5 frontend tests pass
- [ ] No TypeScript compilation errors
- [ ] Frontend builds without warnings
- [ ] Empty states display for all panels
- [ ] Error states display when API calls fail
- [ ] Loading skeletons display during initial data load

---

## 6. Security Considerations

Phase 5 is a local development application with no authentication. The following are noted as future hardening items, not required for Phase 5:

| Risk | Current Mitigation | Future Hardening |
|---|---|---|
| SSE stream open to any local client | CORS limits to localhost:3000 | JWT auth on SSE endpoint |
| Export files on local disk | No auth required — local only | Pre-signed download URLs |
| Approval decision not authenticated | Local only — single user | User session validation |
| `context_snapshot` may contain sensitive research data | Local DB — no network exposure | Field-level encryption at rest |

---

## 7. Test Data Requirements

Phase 5 tests require:

1. A completed research run with a `ResearchReport` (for export tests)
2. A research run in `awaiting_approval` state with a pending `ApprovalRequest` (for approval tests)
3. A research run with > 5 sources and > 5 evidence items (for explorer tests)

These are created programmatically in test fixtures using factory functions. No external data files are required.
