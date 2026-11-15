# MAAR Phase 5 — Known Issues and Limitations

## Document: Phase 5 Known Issues
## Status: Final — Written at Phase 5 completion

---

## 1. Environment Dependencies (Pre-existing, Not Phase 5 Regressions)

### KI-001: `pypdf` and `python-docx` not installed in test environment
- **Affected tests:** `test_document_processing.py` (2 tests)
- **Symptom:** `ModuleNotFoundError: No module named 'pypdf'`
- **Root cause:** These packages are listed in `requirements.txt` but were not installed in the development virtual environment before Phase 5. They are needed only for document processing, not for Phase 5 SSE/approval/export functionality.
- **Resolution:** Run `pip install pypdf python-docx` in the backend venv. The packages are already in `requirements.txt`.

### KI-002: IBM Watsonx AI project deleted
- **Affected tests:** 15–20 tests in `test_evidence_extraction.py`, `test_source_providers.py`, `test_claim_verification.py`, `test_sequential_claim_verification.py`
- **Symptom:** `CannotSetProjectOrSpace: 404 Not Found — deleted project`
- **Root cause:** The IBM Watsonx AI cloud project referenced in the `.env` was deleted externally. These tests make live API calls and fail without valid credentials.
- **Resolution:** Update `WATSONX_PROJECT_ID` in `.env` with a valid project, or switch `LLM_PROVIDER` to `openai` / `groq` for local testing.

### KI-003: `langgraph.checkpoint.sqlite` compatibility
- **Affected tests:** `test_multi_agent_workflow.py` (3 tests)
- **Symptom:** Import errors or checkpointer failures
- **Root cause:** The `langgraph-checkpoint-sqlite` package version may have breaking changes with LangGraph 1.2.20.
- **Resolution:** Verify `langgraph-checkpoint-sqlite` version matches; consider pinning to a known-compatible version.

---

## 2. Phase 5 Functional Limitations

### KI-004: Export download requires port knowledge
- **Affected feature:** `ExportPanel.tsx` download button
- **Symptom:** The frontend hardcodes the backend port by replacing `3000` → `8000` in `window.location.origin` to construct the download URL. This is a workaround because the download endpoint returns a binary file and cannot go through the Next.js API proxy.
- **Impact:** Works correctly in the standard development setup (frontend :3000, backend :8000). Will break if ports differ.
- **Resolution:** Configure a Next.js API route that proxies the download, or use an environment variable for the API base URL in the download link construction.

### KI-005: `_resume_graph` runs in a background `asyncio.create_task`
- **Affected feature:** Approval workflow resume after user approval
- **Symptom:** If the event loop shuts down before graph resume completes (e.g., server restart immediately after submitting an approval), the resume is silently lost. The run stays in `awaiting_approval` status.
- **Impact:** Low risk in normal use. Only affects the edge case of a server restart immediately after approval submission.
- **Resolution:** Future phase: implement a persistent resume queue (database-backed) that survives server restarts.

### KI-006: SSE reconnection sends all queued events on reconnect
- **Affected feature:** `useSSE.ts` with `Last-Event-ID`
- **Symptom:** If a client reconnects after a long disconnect and many events were queued, the replay may include events the client already processed (depending on whether the browser preserved the EventSource state).
- **Impact:** Duplicate events may appear in `AgentActivityFeed` briefly. The deduplication logic (`prev.some(e => e.id === event.id)`) prevents visible duplicates in the UI.
- **Resolution:** No action needed; deduplication is in place. For production, consider a TTL on the SSE event queue.

### KI-007: Report versioning not hooked into `finalize_report_node`
- **Affected feature:** Report versioning when a revision loop runs
- **Symptom:** If a research run completes a revision loop (critic requests revision → agents re-run → new report generated), the `finalize_report_node` will attempt to insert a new `ResearchReport` for the same `run_id`. The old `UNIQUE(run_id)` constraint has been replaced by `UNIQUE(run_id, version_number)`, so the insert will succeed — but the previous report will NOT be automatically archived to `report_versions` unless `archive_current_and_bump()` from `report_versioning_service.py` is called.
- **Impact:** Multiple report records may exist for one run, all with `is_current = True`. The `/reports` list endpoint returns all of them (newest first), so the frontend will show the latest. The `GET /report` (singular) endpoint still returns the first record found, which may be the older one.
- **Resolution:** Next phase: integrate `archive_current_and_bump()` into `finalize_report_node` or `report_service.py` before creating a new report.

### KI-008: Cross-link from Evidence drawer to Source drawer requires `projectId` and `runId`
- **Affected feature:** `SourcePanel` `openSourceId` cross-link
- **Symptom:** For completed runs in static mode (sources passed as array), if `projectId`/`runId` are not passed to `SourcePanel`, the cross-link fetch will silently fail and the drawer will not open for sources not in the initial list.
- **Impact:** The cross-link only works fully in self-fetching mode (active runs). For completed runs, we pass `projectId` and `runId` alongside `sources` in `ResearchPanel.tsx` (fixed in M5.7), so this is mitigated.
- **Resolution:** No further action required; both props are now passed for completed runs.

---

## 3. UX Limitations

### KI-009: Export download opens in same window on some browsers
- **Affected feature:** Export Panel download
- **Symptom:** On some browsers, the programmatic `a.click()` download may open the file inline rather than triggering a save dialog, depending on browser MIME type configuration.
- **Impact:** Cosmetic. The file is still correctly generated and served.
- **Resolution:** The backend sets `Content-Disposition: attachment` which should force a save dialog on all standard browsers.

### KI-010: `ApprovalBanner` only appears in the "In Progress" tab
- **Affected feature:** Approval workflow UX
- **Symptom:** If the user is on the Sources or Evidence tab when the graph suspends and an `approval_required` SSE event arrives, they won't see the banner immediately — they need to switch to the "In Progress" tab.
- **Impact:** Low — the SSE connection indicator and run status card will show `awaiting_approval` on the current tab if `RunStatusCard`/`MultiAgentStatusCard` are visible. When the user switches to "In Progress", the banner appears.
- **Resolution:** Future: show a toast notification for approval_required regardless of active tab.

---

## 4. Test Coverage Gaps

### KI-011: No frontend unit tests for ApprovalModal, ApprovalBanner, ExportPanel, LiveBadge
- **Status:** Vitest tests cover only `useSSE.ts` (12 tests). Component tests for Phase 5 UI components are not written.
- **Resolution:** Phase 6: add React Testing Library tests for all Phase 5 components.

### KI-012: No integration test for full SSE event flow
- **Status:** Backend SSE tests (15 tests) test the stream endpoint in isolation. There is no test that verifies the complete chain: graph event → `event_service.publish_event()` → `SSEManager` → HTTP stream → frontend `dispatchEvent`.
- **Resolution:** Phase 6: add an end-to-end integration test using a test HTTP client that reads the SSE stream.

---

## 5. Performance Notes

### KI-013: `getSources()` and `getEvidence()` load all items on first fetch
- **Status:** The backend returns all sources/evidence in a single response (no server-side pagination). The frontend slices client-side. For very large runs (1000+ sources), this may be slow.
- **Resolution:** Phase 6: add server-side pagination with `limit`/`offset` query params.

---

*Document generated at Phase 5 completion. Last updated: 2026-11-14.*
