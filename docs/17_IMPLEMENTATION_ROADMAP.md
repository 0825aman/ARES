# 17 — Implementation Roadmap (Phase 2)

**Project**: Multi-Agent Autonomous Researcher (MAAR)
**Phase**: 2 — First End-to-End Research Workflow
**Status**: Planning

---

## Overview

Phase 2 is implemented in 8 sequential milestones. Each milestone is independently testable and produces a concrete, verifiable deliverable. No milestone begins before the previous one passes its acceptance criteria.

Milestones 1–4 are backend-only. Milestone 5 integrates the frontend. Milestones 6–7 complete the research pipeline. Milestone 8 is end-to-end validation.

---

## Milestone 1 — Database Schema and Alembic

**Depends on**: Phase 1 complete (all backend tests passing)

**Intent**: Introduce Alembic migration management and create all 4 new database tables. This is the foundation for every subsequent milestone.

**Todo**:
1. Add `alembic` to `requirements.txt`.
2. Run `alembic init alembic` in `maar/backend/`.
3. Configure `alembic/env.py`:
   - Import all ORM models.
   - Use the async engine from `app/core/database.py`.
   - Set `render_as_batch = True` for SQLite compatibility.
4. Implement `app/models/run.py` (`ResearchRun` ORM with all columns and indexes).
5. Implement `app/models/document.py` (`UploadedDocument` ORM).
6. Implement `app/models/evidence.py` (`EvidenceRecord` ORM).
7. Implement `app/models/report.py` (`ResearchReport` ORM).
8. Add `runs` relationship to `ResearchProject` ORM in `app/models/project.py`.
9. Update `app/models/__init__.py` to import all new models (required for Alembic autogenerate).
10. Generate initial migration: `alembic revision --autogenerate -m "phase2_research_workflow"`.
11. Apply migration: `alembic upgrade head`.
12. Replace `create_all()` in `app/main.py` lifespan with programmatic `alembic upgrade head`.
13. Add startup recovery: query `status = running` runs on startup → set to `failed` with message "Server restart during execution".

**Acceptance criteria**:
- `alembic upgrade head` runs without error on a fresh database.
- `alembic upgrade head` runs without error on an existing Phase 1 database (no data loss to `research_projects`).
- All 4 new tables exist with correct columns and foreign keys.
- `alembic downgrade -1` reverses the migration cleanly.
- All Phase 1 pytest tests still pass (69/69).

---

## Milestone 2 — Document Upload API

**Depends on**: Milestone 1

**Intent**: Implement file upload, validation, storage, and the document list/delete API. This can be tested without any research workflow logic.

**Todo**:
1. Add `python-magic-bin` (Windows) / `python-magic` (Linux/macOS), `pypdf`, `python-docx`, `trafilatura`, `httpx` to `requirements.txt`.
2. Implement `app/schemas/document.py` (request/response schemas for upload, list, delete).
3. Implement `app/services/document_service.py`:
   - `validate_and_store(project_id, upload_file)` — validation, MIME check, safe storage, hash.
   - `list_documents(project_id)` — query by project.
   - `delete_document(document_id)` — disk delete + DB delete (blocked if run is active).
4. Implement `app/api/v1/routes/documents.py` with 3 endpoints (upload, list, delete).
5. Register document router in `app/api/v1/router.py`.
6. Add `UPLOAD_DIR` and `MAX_UPLOAD_SIZE_MB` to `app/core/config.py`.
7. Create upload directory on startup if it does not exist.
8. Write tests in `tests/test_documents.py`:
   - Upload valid PDF, DOCX, TXT.
   - Reject invalid extension.
   - Reject oversized file.
   - List documents for project.
   - Delete document.
   - Attempt delete of document attached to running run (409).

**Acceptance criteria**:
- Uploading a PDF to `POST /api/v1/projects/{id}/documents` returns 201 with document metadata.
- File appears on disk at the expected path.
- Invalid extensions return 422.
- All new tests pass. All Phase 1 tests still pass.

---

## Milestone 3 — Provider Abstractions

**Depends on**: Milestone 1 (no dependency on Milestone 2)

**Intent**: Implement the LLM and web search provider abstractions. This milestone produces testable interfaces before the workflow is built.

**Todo**:
1. Implement `app/providers/llm.py`:
   - `LLMProvider` abstract base class.
   - `OpenAIProvider` implementation using `openai` async client.
   - `MockLLMProvider` for testing (returns a deterministic canned response).
2. Implement `app/providers/web_search.py`:
   - `WebSearchProvider` abstract base class.
   - `TavilySearchProvider` implementation.
   - `MockWebSearchProvider` for testing.
3. Implement `app/providers/web_fetcher.py`:
   - `is_safe_url()` SSRF validation.
   - `fetch_url()` using `httpx` + `trafilatura`.
4. Add all provider env vars to `app/core/config.py` (`LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_TIMEOUT_SECONDS`, `SEARCH_PROVIDER`, `SEARCH_API_KEY`, `SEARCH_MAX_RESULTS`, `WEB_FETCH_TIMEOUT_SECONDS`, `WEB_FETCH_MAX_CONTENT_KB`).
5. Implement provider factory functions: `get_llm_provider()`, `get_search_provider()`.
6. Add `openai`, `tavily-python` to `requirements.txt`.
7. Write tests in `tests/test_providers.py`:
   - SSRF: localhost URL blocked.
   - SSRF: RFC-1918 URL blocked.
   - SSRF: valid public URL passes.
   - MockLLMProvider returns expected response.
   - MockSearchProvider returns expected results.

**Acceptance criteria**:
- `is_safe_url("http://localhost:8080")` returns `False`.
- `is_safe_url("http://192.168.1.1")` returns `False`.
- `is_safe_url("https://example.com")` returns `True`.
- Provider tests pass without real API keys (mock-only tests).

---

## Milestone 4 — Research Workflow Engine

**Depends on**: Milestones 2 and 3

**Intent**: Implement the full 7-stage sequential research workflow. This is the core of Phase 2.

**Todo**:
1. Implement `app/services/run_service.py`:
   - `create_run()` — validate source selection, check for active run, create DB record.
   - `get_run()`, `list_runs()` — queries.
   - `update_run_status()`, `update_run_stage()` — status transitions with validation.
2. Implement `app/schemas/run.py` (all request/response schemas).
3. Implement `app/services/evidence_normalizer.py`:
   - `normalize_web_result()` — `SearchResult → EvidenceRecord`.
   - `normalize_document_chunk()` — `ExtractedChunk → EvidenceRecord`.
4. Implement `app/services/context_builder.py`:
   - `build_evidence_context(evidence_records, research_question)` — relevance scoring, budget selection, source labeling.
5. Implement `app/services/report_generator.py`:
   - `generate_report(context, run)` — calls LLM, parses JSON, resolves citations.
6. Implement `app/services/research_workflow.py`:
   - `run_research_workflow(run_id: str)` top-level coroutine.
   - Calls all 7 stages in sequence.
   - Top-level exception handler writes `status=failed`.
7. Write `tests/test_workflow.py` using `MockLLMProvider` and `MockWebSearchProvider`:
   - Full workflow execution with web + documents.
   - Web-only workflow.
   - Document-only workflow.
   - All documents fail extraction (web enabled → continues).
   - All documents fail extraction (web disabled → fails).
   - Web search fails → continues with documents.
   - LLM fails twice → run status = failed.
   - Verify DB state after each scenario.

**Acceptance criteria**:
- `run_research_workflow(run_id)` transitions run from `pending → completed` in the happy path.
- Failure scenarios correctly set `status = failed` with non-empty `error_message`.
- A `ResearchReport` record exists in the DB after a successful run.
- All workflow tests pass with mocked providers (no real API calls).

---

## Milestone 5 — Run and Report API Endpoints

**Depends on**: Milestone 4

**Intent**: Expose the research workflow through HTTP. The frontend can now start runs, poll status, and retrieve reports.

**Todo**:
1. Implement `app/api/v1/routes/runs.py`:
   - `POST /{project_id}/runs` — validate, create run, start `BackgroundTask`.
   - `GET /{project_id}/runs` — list runs.
   - `GET /{project_id}/runs/{run_id}` — get single run.
   - `GET /{project_id}/runs/{run_id}/report` — get completed report.
2. Register runs router in `app/api/v1/router.py`.
3. Write `tests/test_run_api.py`:
   - `POST /runs` creates run and returns 201 with `status=pending`.
   - `POST /runs` with no source → 422.
   - `POST /runs` when another run is active → 409.
   - `GET /runs` lists all runs for project.
   - `GET /runs/{id}` returns run status.
   - `GET /runs/{id}/report` returns 404 while run is pending.
   - `GET /runs/{id}/report` returns 200 after mock completion.
4. Integration test: POST → poll → report (using mock providers via dependency override).

**Acceptance criteria**:
- `POST /api/v1/projects/{id}/runs` returns 201 immediately (background task does not block).
- Polling `GET /api/v1/projects/{id}/runs/{run_id}` reflects stage updates.
- `GET /api/v1/projects/{id}/runs/{run_id}/report` returns the full report structure.
- All API tests pass.

---

## Milestone 6 — Frontend Research Submission UI

**Depends on**: Milestone 5

**Intent**: Implement the ResearchForm and FileUploadArea frontend components. Users can submit research runs from the workspace.

**Todo**:
1. Add shadcn/ui `Tabs`, `Checkbox`, `Progress` components (`npx shadcn-ui@latest add tabs checkbox progress`).
2. Implement `src/lib/types/run.ts` with all new TypeScript types.
3. Add `apiFetchMultipart()` to `src/lib/api/client.ts`.
4. Implement `src/lib/api/runs.ts` with all API functions.
5. Implement `FileUploadArea.tsx` — drop zone, file list, eager upload.
6. Implement `ResearchForm.tsx` — research question, source selection, document upload, submission.
7. Implement `ResearchPanel.tsx` — fetches run history on mount, routes to correct sub-component.
8. Update `/projects/[id]/page.tsx` to replace the three `PlaceholderSection` blocks with `<ResearchPanel>`.
9. Verify: `npm run build` passes with no type errors.
10. Verify: Submitting the form creates a run via the API and transitions to the status view.

**Acceptance criteria**:
- The workspace shows `ResearchForm` when no runs exist.
- Submitting with no source selected shows inline error.
- Uploading a valid PDF shows the file in the list with name and size.
- Uploading an invalid file shows an inline error without adding it to the queue.
- Submitting successfully creates a run and transitions to `RunStatusCard`.

---

## Milestone 7 — Frontend Progress and Report Display

**Depends on**: Milestone 6

**Intent**: Implement the polling status view and the completed research report display.

**Todo**:
1. Implement `RunStatusCard.tsx` — polling logic, stage indicator, started-at time.
2. Implement `RunFailedCard.tsx` — error display.
3. Implement `ResearchReport.tsx` — full report rendering.
4. Implement `FindingsSection.tsx` — collapsible sources list.
5. Implement `SourcesList.tsx` — web links and document references.
6. Implement `RunHistory.tsx` — run list with status badges and "View Report →" links.
7. Verify: polling works — status card updates as backend stages progress.
8. Verify: completed run transitions to report view.
9. Verify: failed run shows `RunFailedCard` with error message.
10. Verify: `npm run build` passes.

**Acceptance criteria**:
- Polling updates the stage label every 3 seconds.
- When run completes, the report renders with all sections.
- Web citations show clickable URLs.
- Document citations show filename and page number.
- Refreshing the browser on a completed workspace page shows the report (data is persisted).

---

## Milestone 8 — End-to-End Validation

**Depends on**: Milestones 1–7

**Intent**: Full end-to-end validation across the complete application stack.

**Todo**:
1. Configure real API keys in `maar/backend/.env` (`LLM_API_KEY`, `SEARCH_API_KEY`).
2. Run the backend: `uvicorn app.main:app --reload --port 8000`.
3. Run the frontend: `npm run dev`.
4. Execute the Phase 2 completion checklist (see `18_TESTING_SECURITY_AND_RELIABILITY.md` Section 5).
5. Run all backend tests: `pytest tests/ -v` — all must pass.
6. Run frontend build: `npm run build` — must pass with zero errors.
7. Document any issues found and fix before declaring Phase 2 complete.
8. Update `maar-phase2-plan.md` to mark all milestones `[x] done`.

**Acceptance criteria**: All items in the Phase 2 completion checklist in document 18 are verified.

---

## Dependency Graph

```
Milestone 1 (Database)
    ├── Milestone 2 (Document Upload API)
    │       └── Milestone 4 (Workflow Engine)
    │                   └── Milestone 5 (Run API)
    │                               ├── Milestone 6 (Frontend Submission)
    │                               │           └── Milestone 7 (Progress + Report)
    │                               │                           └── Milestone 8 (E2E)
    └── Milestone 3 (Providers)
                └── Milestone 4 (Workflow Engine)
```

Milestones 2 and 3 can be developed in parallel. All other milestones are strictly sequential.

---

## New Dependencies Summary

| Package | Purpose | Added to |
|---|---|---|
| `alembic` | DB migrations | `requirements.txt` |
| `pypdf` | PDF text extraction | `requirements.txt` |
| `python-docx` | DOCX text extraction | `requirements.txt` |
| `trafilatura` | Web content extraction | `requirements.txt` |
| `httpx` | Async HTTP client (already in dev) | `requirements.txt` (promote to main) |
| `python-magic-bin` | MIME type detection (Windows) | `requirements.txt` |
| `openai` | OpenAI LLM API client | `requirements.txt` |
| `tavily-python` | Tavily search API client | `requirements.txt` |
| `python-multipart` | FastAPI multipart/form-data support | `requirements.txt` |
