# 11 — Phase 2 Technical Architecture

**Project**: Multi-Agent Autonomous Researcher (MAAR)
**Phase**: 2 — First End-to-End Research Workflow
**Status**: Planning

---

## 1. Architectural Overview

Phase 2 adds a research execution layer on top of the Phase 1 foundation. The overall architecture remains a three-tier local application:

```
Browser (Next.js)
      ↕ HTTP/JSON (polling)
FastAPI Backend
      ↕ async SQLAlchemy
SQLite Database
      ↕ (filesystem)
Upload Storage (local directory)
      ↕ HTTP (external)
Search Provider API
LLM Provider API
```

The core addition is a **Research Workflow Engine** — a sequential Python service executed as a FastAPI background task. It reads from and writes to the same SQLite database and shared filesystem that the HTTP API uses.

---

## 2. Component Map

### 2.1 Existing Phase 1 Components (unchanged or minimally extended)

| Component | Location | Phase 2 Change |
|---|---|---|
| ResearchProject ORM model | `app/models/project.py` | Add `runs` relationship |
| ProjectService | `app/services/project_service.py` | No change |
| Project API routes | `app/api/v1/routes/projects.py` | No change |
| Settings | `app/core/config.py` | Add new env vars |
| Database engine | `app/core/database.py` | No change |
| Frontend layout / sidebar | `src/components/layout/` | No change |
| Frontend types | `src/lib/types/project.ts` | Extend, do not break |
| API client | `src/lib/api/client.ts` | No change |

### 2.2 New Phase 2 Components

**Backend:**

| Component | Location | Responsibility |
|---|---|---|
| ResearchRun ORM | `app/models/run.py` | Run lifecycle, status, stage, timestamps |
| UploadedDocument ORM | `app/models/document.py` | File metadata, storage path, content hash |
| EvidenceRecord ORM | `app/models/evidence.py` | Normalized evidence from web + docs |
| ResearchReport ORM | `app/models/report.py` | Persisted report JSON + markdown |
| ResearchRun schemas | `app/schemas/run.py` | Request/response Pydantic models |
| Document schemas | `app/schemas/document.py` | Upload response, list response |
| RunService | `app/services/run_service.py` | CRUD for runs, status transitions |
| DocumentService | `app/services/document_service.py` | File storage, validation, extraction |
| ResearchWorkflow | `app/services/research_workflow.py` | Orchestrates all workflow stages |
| WebSearchProvider | `app/providers/web_search.py` | Abstract base + SerpAPI/Tavily impl |
| WebFetcher | `app/providers/web_fetcher.py` | URL fetching with SSRF protection |
| LLMProvider | `app/providers/llm.py` | Abstract base + OpenAI impl |
| EvidenceNormalizer | `app/services/evidence_normalizer.py` | Converts raw results to EvidenceRecord |
| ContextBuilder | `app/services/context_builder.py` | Assembles evidence into LLM prompt |
| ReportGenerator | `app/services/report_generator.py` | Calls LLM, structures report |
| Run API routes | `app/api/v1/routes/runs.py` | HTTP endpoints for runs + reports |
| Document API routes | `app/api/v1/routes/documents.py` | HTTP endpoints for document upload |

**Frontend:**

| Component | Location | Responsibility |
|---|---|---|
| ResearchPanel | `src/components/workspace/ResearchPanel.tsx` | Submission form + run history tab container |
| ResearchForm | `src/components/workspace/ResearchForm.tsx` | Question input, file upload, source selection |
| FileUploadArea | `src/components/workspace/FileUploadArea.tsx` | Drop target, file list, remove buttons |
| RunStatusCard | `src/components/workspace/RunStatusCard.tsx` | Active run progress + polling |
| RunHistory | `src/components/workspace/RunHistory.tsx` | List of all runs for the project |
| ResearchReport | `src/components/workspace/ResearchReport.tsx` | Renders the completed report |
| FindingsSection | `src/components/workspace/FindingsSection.tsx` | Key findings display |
| SourcesList | `src/components/workspace/SourcesList.tsx` | Linked citations display |
| types/run.ts | `src/lib/types/run.ts` | ResearchRun, ResearchReport TypeScript types |
| api/runs.ts | `src/lib/api/runs.ts` | API functions for runs + documents |

---

## 3. Research Workflow Architecture

The workflow executes as a FastAPI background task, started immediately after the HTTP response for `POST /api/v1/projects/{id}/runs` is returned to the browser.

```
POST /runs → 201 Created (run_id returned immediately)
                ↓
         [Background Task starts]
                ↓
    Stage 1: Initialize Run (DB write: status=running)
                ↓
    Stage 2: Process Documents (if any uploaded)
                ↓
    Stage 3: Web Research (if requested)
                ↓
    Stage 4: Normalize Evidence
                ↓
    Stage 5: Build Context + Synthesize
                ↓
    Stage 6: Generate Report
                ↓
    Stage 7: Persist Report (DB write: status=completed)
```

Each stage updates the `current_stage` field on the run record. The frontend polls `GET /api/v1/projects/{id}/runs/{run_id}` every 3 seconds to display progress.

If any stage raises an unhandled exception, the workflow's top-level exception handler catches it, writes `status=failed` and `error_message` to the run record, and exits cleanly.

---

## 4. Background Execution Strategy

### Decision: FastAPI `BackgroundTasks`

Phase 2 uses FastAPI's built-in `BackgroundTasks` mechanism. The route handler adds the workflow coroutine as a background task before returning the 201 response.

**Reliability implication**: If the uvicorn process is killed while a run is in progress, the run will remain in `running` state permanently. There is no automatic recovery.

**Mitigation for Phase 2**: On startup, the application queries for any runs stuck in `running` state and transitions them to `failed` with `error_message = "Server restart during execution"`. This is implemented in the lifespan startup handler in `app/main.py`.

**Why not Celery or ARQ?**: These require a broker (Redis) which introduces infrastructure not justified for a local, single-user application. They will be evaluated for Phase 3 when concurrent execution and reliability guarantees become necessary.

---

## 5. Provider Abstraction

### 5.1 LLM Provider

```python
# app/providers/llm.py

class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, system_prompt: str, user_prompt: str) -> str: ...
    @abstractmethod
    async def health_check(self) -> bool: ...

class OpenAIProvider(LLMProvider): ...   # Phase 2 implementation
class OllamaProvider(LLMProvider): ...  # Stub for Phase 3
```

The active provider is selected by `LLM_PROVIDER` env var (default: `openai`). The provider is instantiated once at startup and injected via FastAPI dependency.

### 5.2 Web Search Provider

```python
# app/providers/web_search.py

class WebSearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, num_results: int) -> list[SearchResult]: ...

class TavilySearchProvider(WebSearchProvider): ...   # Phase 2 default
class SerpAPISearchProvider(WebSearchProvider): ...  # Alternative
```

`SEARCH_PROVIDER` env var selects the implementation (default: `tavily`).

---

## 6. Data Flow

### 6.1 Research Submission
```
Browser → POST /api/v1/projects/{id}/runs (multipart/form-data)
        → Backend validates files + request
        → Creates ResearchRun (status=pending)
        → Saves uploaded files to disk
        → Creates UploadedDocument records
        → Starts BackgroundTask
        → Returns 201 { run_id, status: "pending" }
Browser ← 201 response (immediately)
Browser starts polling GET /runs/{run_id}
```

### 6.2 Polling
```
Browser → GET /api/v1/projects/{id}/runs/{run_id}
        → Returns { status, current_stage, started_at, ... }
Browser re-polls every 3 seconds until status ∈ { completed, failed }
```

### 6.3 Report Retrieval
```
Browser → GET /api/v1/projects/{id}/runs/{run_id}/report
        → Returns full ResearchReport JSON
Browser renders report components
```

---

## 7. Frontend Architecture

### 7.1 Workspace Page Extension

The existing [`/projects/[id]/page.tsx`](../frontend/src/app/projects/%5Bid%5D/page.tsx) is extended to replace the three `PlaceholderSection` components with the real `ResearchPanel` component.

`ResearchPanel` renders one of three states:
1. **No runs yet**: `ResearchForm` (submission form)
2. **Run in progress**: `RunStatusCard` (polling, stage display)
3. **Run completed**: `ResearchReport` (rendered report) + `RunHistory` (previous runs)

### 7.2 Polling Strategy

Client component `RunStatusCard` uses `useEffect` + `setInterval` to poll every 3 seconds. On `completed` or `failed`, it clears the interval and triggers a full page data refresh via `router.refresh()`.

### 7.3 File Upload

File upload uses the browser's native `FormData` API. The `apiFetch` client is extended with a `apiFetchMultipart` variant that omits the `Content-Type: application/json` header (allowing the browser to set `multipart/form-data` with the correct boundary automatically).

---

## 8. Environment Variables (New in Phase 2)

| Variable | Default | Purpose |
|---|---|---|
| `UPLOAD_DIR` | `./uploads` | Base directory for uploaded files |
| `MAX_UPLOAD_SIZE_MB` | `20` | Maximum file size per upload |
| `LLM_PROVIDER` | `openai` | Active LLM provider (`openai`, `ollama`) |
| `LLM_API_KEY` | _(required)_ | LLM provider API key |
| `LLM_MODEL` | `gpt-4o-mini` | Model name |
| `LLM_TIMEOUT_SECONDS` | `120` | Timeout for LLM API calls |
| `SEARCH_PROVIDER` | `tavily` | Active search provider (`tavily`, `serpapi`) |
| `SEARCH_API_KEY` | _(required for web runs)_ | Search provider API key |
| `SEARCH_MAX_RESULTS` | `8` | Max search results per run |
| `WEB_FETCH_TIMEOUT_SECONDS` | `15` | Timeout per URL fetch |
| `WEB_FETCH_MAX_CONTENT_KB` | `200` | Max extracted content per URL |

---

## 9. Consistency with Phase 1

- All Phase 1 API routes remain at their existing URLs with unchanged schemas.
- The `ResearchProject` ORM model gains a `runs` relationship but no column changes — no migration required for the project table.
- The frontend's `AppShell`, `Sidebar`, `PageHeader`, design tokens, and shadcn/ui components are reused unchanged.
- The `apiFetch` client is extended non-breakingly.
- TypeScript types in `project.ts` are extended only by addition, never by removal.
