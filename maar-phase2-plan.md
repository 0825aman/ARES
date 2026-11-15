# MAAR Phase 2 — Master Implementation Plan

**Project**: Multi-Agent Autonomous Researcher (MAAR)
**Phase**: 2 — First End-to-End Research Workflow
**Status**: ✅ Phase 2 Complete

---

## Overview

Phase 2 delivers the first functional research workflow. A user can open a research project, submit a research question, optionally upload documents, and start a research run. The backend executes a 7-stage sequential workflow — gathering information from the web and/or uploaded documents, synthesizing evidence, and generating a structured report. The user can monitor progress and view the completed result.

All planning documents are in `maar/docs/`. Milestones must be implemented sequentially (except Milestones 2 and 3 which can be parallelized).

**Two-command startup (after Phase 2 setup):**

Windows PowerShell:
```powershell
# Terminal 1 — Backend
cd maar\backend; .venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd maar\frontend; npm run dev
```

> See `docs/17_IMPLEMENTATION_ROADMAP.md` for full setup and new dependencies.

---

## Phase 1 Status (Prerequisite)

All Phase 1 sub-tasks must be complete and tests passing (69/69) before Phase 2 begins.

- [x] Sub-Task 1: Repository Setup and Environment
- [x] Sub-Task 2: Backend Foundation and Database
- [x] Sub-Task 3: Backend API Endpoints (69/69 tests pass)
- [x] Sub-Task 4: Frontend Foundation and Layout
- [x] Sub-Task 5: Dashboard Page
- [x] Sub-Task 6: Research Projects Pages
- [x] Sub-Task 7: Research Workspace Page

---

## Phase 2 Milestones

---

### Milestone 1: Database Schema and Alembic

**Status**: [x] done

**Intent**
Introduce Alembic migration management and create the 4 new database tables required by Phase 2: `research_runs`, `uploaded_documents`, `evidence_records`, and `research_reports`. Replace `create_all()` with Alembic's `upgrade head`. Add startup recovery for stuck runs.

**Relevant Documents**
- `docs/13_DATABASE_SCHEMA_CHANGES.md` — full schema, relationships, migration strategy
- `docs/11_PHASE_2_TECHNICAL_ARCHITECTURE.md` — Section 2 (component map)
- `docs/19_ARCHITECTURAL_DECISIONS.md` — ADR-102

**Todo List**
1. Add `alembic` to `requirements.txt`. Install in venv.
2. Run `alembic init alembic` in `maar/backend/`.
3. Configure `alembic/env.py`: import all models, use async engine, set `render_as_batch=True`.
4. Implement `app/models/run.py` — `ResearchRun` ORM.
5. Implement `app/models/document.py` — `UploadedDocument` ORM.
6. Implement `app/models/evidence.py` — `EvidenceRecord` ORM.
7. Implement `app/models/report.py` — `ResearchReport` ORM.
8. Add `runs` relationship to `ResearchProject` in `app/models/project.py`.
9. Update `app/models/__init__.py` to import all new models.
10. Generate initial migration: `alembic revision --autogenerate -m "phase2_research_workflow"`.
11. Apply: `alembic upgrade head`.
12. Replace `create_all()` in `app/main.py` lifespan with `alembic upgrade head`.
13. Add startup recovery in lifespan: mark stuck `running` runs as `failed`.
14. Verify: `pytest tests/ -v` — all 69 Phase 1 tests still pass.
15. Verify: `alembic downgrade -1` works without error.

**Expected Outcomes**
- `alembic upgrade head` creates all 4 tables on a fresh database.
- `alembic upgrade head` on a Phase 1 database preserves all project data.
- All 69 Phase 1 tests pass.
- Startup recovery correctly marks stuck runs as failed.

---

### Milestone 2: Document Upload API

**Status**: [x] done

**Intent**
Implement file upload, validation (extension, MIME, size), safe storage, content hashing, and the document list/delete API. Can be tested without any workflow logic.

**Relevant Documents**
- `docs/15_DOCUMENT_AND_WEB_RETRIEVAL_DESIGN.md` — Sections 1 (upload/storage), 2 (extraction)
- `docs/14_BACKEND_API_SPECIFICATION.md` — Sections 2.1, 2.2, 2.3
- `docs/18_TESTING_SECURITY_AND_RELIABILITY.md` — Section 1.1

**Todo List**
1. Add `python-magic-bin`, `pypdf`, `python-docx`, `python-multipart` to `requirements.txt`. Install.
2. Add `UPLOAD_DIR`, `MAX_UPLOAD_SIZE_MB` to `app/core/config.py`.
3. Create upload directory on startup if absent.
4. Implement `app/schemas/document.py` — all request/response Pydantic schemas.
5. Implement `app/services/document_service.py`:
   - `validate_and_store()` — MIME check, size check, safe filename, SHA-256 hash, deduplication.
   - `extract_text()` — dispatch to PDF/DOCX/TXT extractor.
   - `list_documents()`, `get_document()`, `delete_document()`.
6. Implement `app/api/v1/routes/documents.py` — 3 endpoints.
7. Register document router in `app/api/v1/router.py`.
8. Write `tests/test_documents.py` — all 13 test cases from doc 18.
9. Verify: all tests pass including 69 Phase 1 tests.

**Expected Outcomes**
- `POST /api/v1/projects/{id}/documents` accepts PDF/DOCX/TXT, rejects others.
- Files stored on disk with safe names under `{UPLOAD_DIR}/{project_id}/`.
- Duplicate files (same SHA-256) reuse existing stored file.
- `DELETE` blocked with 409 when document is attached to a running run.

---

### Milestone 3: Provider Abstractions

**Status**: [x] done

**Intent**
Implement the LLM and web search provider abstractions with real (OpenAI, Tavily) and mock implementations. Implement SSRF-safe URL fetcher. All provider behavior is testable without real API keys.

**Relevant Documents**
- `docs/11_PHASE_2_TECHNICAL_ARCHITECTURE.md` — Section 5 (provider abstraction)
- `docs/15_DOCUMENT_AND_WEB_RETRIEVAL_DESIGN.md` — Sections 3, 4
- `docs/19_ARCHITECTURAL_DECISIONS.md` — ADR-104, ADR-105, ADR-108

**Todo List**
1. Add `openai`, `tavily-python`, `trafilatura`, `httpx` (promote to main requirements) to `requirements.txt`. Install.
2. Add all provider env vars to `app/core/config.py`.
3. Implement `app/providers/llm.py` — `LLMProvider` ABC, `OpenAIProvider`, `MockLLMProvider`.
4. Implement `app/providers/web_search.py` — `WebSearchProvider` ABC, `TavilySearchProvider`, `MockWebSearchProvider`.
5. Implement `app/providers/web_fetcher.py` — `is_safe_url()`, `fetch_url()`.
6. Implement provider factory functions.
7. Write `tests/test_providers.py` — all 9 test cases from doc 18.
8. Verify: SSRF tests pass without internet access.

**Expected Outcomes**
- `is_safe_url("http://localhost")` → False.
- `is_safe_url("https://example.com")` → True.
- `MockLLMProvider.complete()` returns canned JSON without API call.
- `MockWebSearchProvider.search()` returns canned results.

---

### Milestone 4: Research Workflow Engine

**Status**: [x] done

**Intent**
Implement the 7-stage sequential research workflow. This is the core Phase 2 capability. All logic uses injected providers so it is fully testable with mocks.

**Relevant Documents**
- `docs/12_RESEARCH_WORKFLOW_DESIGN.md` — all 7 stages, state machine, failure matrix
- `docs/19_ARCHITECTURAL_DECISIONS.md` — ADR-103, ADR-106
- `docs/13_DATABASE_SCHEMA_CHANGES.md` — ORM relationships

**Todo List**
1. Implement `app/schemas/run.py` — all Pydantic schemas.
2. Implement `app/services/run_service.py` — CRUD, status transitions with validation, duplicate-run guard.
3. Implement `app/services/evidence_normalizer.py` — web and document evidence → EvidenceRecord.
4. Implement `app/services/context_builder.py` — relevance scoring, budget selection, source labeling.
5. Implement `app/services/report_generator.py` — LLM call, JSON parsing, citation resolution.
6. Implement `app/services/research_workflow.py` — top-level coroutine with top-level exception handler.
7. Write `tests/test_workflow.py` — all 14 test cases from doc 18 using mock providers.
8. Verify: all workflow tests pass. All prior tests still pass.

**Expected Outcomes**
- Happy-path workflow transitions run from `pending → completed` with a report in DB.
- All failure scenarios correctly produce `status=failed` with non-empty `error_message`.
- No real API calls made during automated tests.

---

### Milestone 5: Run and Report API Endpoints

**Status**: [x] done

**Intent**
Expose the research workflow through HTTP. The frontend can now start runs, poll status, and retrieve completed reports.

**Relevant Documents**
- `docs/14_BACKEND_API_SPECIFICATION.md` — Sections 2.4–2.7
- `docs/18_TESTING_SECURITY_AND_RELIABILITY.md` — Section 1.4

**Todo List**
1. Implement `app/api/v1/routes/runs.py` — 4 endpoints (start, list, get, report).
2. Register runs router in `app/api/v1/router.py`.
3. Write `tests/test_run_api.py` — all 12 test cases from doc 18.
4. Integration test: `POST /runs` → mock workflow completes → `GET /runs/{id}/report` returns report.
5. Verify: `POST /runs` returns 201 immediately (background task does not block response).
6. Verify: all tests pass.

**Expected Outcomes**
- `POST /api/v1/projects/{id}/runs` returns 201 with `status=pending` immediately.
- `GET /api/v1/projects/{id}/runs/{run_id}/report` returns 404 while pending, 200 when complete.
- 409 returned when a run is already active for the project.

---

### Milestone 6: Frontend Research Submission UI

**Status**: [x] done

**Intent**
Implement ResearchForm, FileUploadArea, and ResearchPanel. Replace workspace placeholders with the real submission UI. Users can submit research runs from the browser.

**Relevant Documents**
- `docs/16_FRONTEND_IMPLEMENTATION_SPECIFICATION.md` — Sections 3, 4, 8, 9
- `docs/14_BACKEND_API_SPECIFICATION.md` — Sections 2.1, 2.4

**Todo List**
1. Install new shadcn/ui components: `Tabs`, `Checkbox`, `Progress`.
2. Implement `src/lib/types/run.ts` — all TypeScript types.
3. Add `apiFetchMultipart()` to `src/lib/api/client.ts`.
4. Implement `src/lib/api/runs.ts` — all API functions.
5. Implement `FileUploadArea.tsx` — drop zone, file list, eager upload.
6. Implement `ResearchForm.tsx` — research question, checkboxes, file area, submit.
7. Implement `ResearchPanel.tsx` — loads run history, routes to correct sub-component.
8. Update `/projects/[id]/page.tsx`: replace three `PlaceholderSection` blocks with `<ResearchPanel>`.
9. Verify: `npm run build` passes with zero type errors.
10. Manual test: submit web-only form → run created → API verified via `/docs`.

**Expected Outcomes**
- Workspace shows ResearchForm when no runs exist.
- Source selection validation works inline.
- File upload shows name, size, remove button.
- Invalid files show inline errors without being added to queue.
- Submitting creates a run and transitions to status view.

---

### Milestone 7: Frontend Progress and Report Display

**Status**: [x] done

**Intent**
Implement RunStatusCard (with polling), ResearchReport (full report rendering), RunHistory, and RunFailedCard. Complete the end-to-end UI flow.

**Relevant Documents**
- `docs/16_FRONTEND_IMPLEMENTATION_SPECIFICATION.md` — Sections 5, 6, 7
- `docs/18_TESTING_SECURITY_AND_RELIABILITY.md` — Section 2

**Todo List**
1. Implement `RunStatusCard.tsx` — polling via `setInterval(3000)`, stage indicator, elapsed time.
2. Implement `RunFailedCard.tsx` — error message display.
3. Implement `ResearchReport.tsx` — all report sections.
4. Implement `FindingsSection.tsx` — collapsible sources.
5. Implement `SourcesList.tsx` — web links and document references.
6. Implement `RunHistory.tsx` — run list with status badges and "View Report →" links.
7. Verify: `npm run build` passes.
8. Manual test: run completes → report renders → all sections visible.
9. Manual test: browser refresh on completed workspace → report still shown.

**Expected Outcomes**
- Polling updates stage label every 3 seconds.
- Completed run transitions to ResearchReport with all sections rendered.
- Web citations are clickable links.
- Document citations show filename and page/chunk reference.
- Browser refresh on completed workspace preserves report display.

---

### Milestone 8: End-to-End Validation

**Status**: [x] done

**Intent**
Full stack validation with real API keys. Complete the Phase 2 acceptance checklist.

**Relevant Documents**
- `docs/18_TESTING_SECURITY_AND_RELIABILITY.md` — Sections 3, 5

**Todo List**
1. Add real API keys to `maar/backend/.env` (`LLM_API_KEY`, `SEARCH_API_KEY`).
2. Run `pytest tests/ -v` — target: all Phase 1 + Phase 2 tests pass.
3. Run `npm run build` — must pass with zero errors.
4. Execute all 7 E2E scenarios from doc 18 Section 3.
5. Execute all items in the Phase 2 Completion Checklist in doc 18 Section 5.
6. Fix any issues found.
7. Update this plan file: mark all milestones `[x] done`.
8. Update `maar-phase2-plan.md` status to `✅ Phase 2 Complete`.

**Expected Outcomes**
- All automated tests pass.
- All E2E scenarios verified manually.
- All Phase 2 Completion Checklist items checked.

---

## Phase 2 Completion Gate

Before Phase 2 is declared complete, all items in `docs/18_TESTING_SECURITY_AND_RELIABILITY.md` Section 5 must be checked off, and all milestones above must be `[x] done`.

---

## Notes for Agent Mode Implementation

- Implement milestones sequentially: 1 → (2 and 3 in parallel) → 4 → 5 → 6 → 7 → 8.
- After completing each milestone, update its **Status** to `[x] done` in this file.
- After each milestone, run `pytest tests/ -v` (backend) and `npm run build` (frontend where applicable).
- Do not begin the next milestone until the current one passes all its acceptance criteria.
- Milestones 2 and 3 have no dependency on each other and can be developed simultaneously.
- Never use real API keys in test code. All tests use mock providers via dependency overrides.
- The research workflow is the most complex component — read `docs/12_RESEARCH_WORKFLOW_DESIGN.md` in full before implementing Milestone 4.
