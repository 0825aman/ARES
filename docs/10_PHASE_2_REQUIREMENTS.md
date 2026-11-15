# 10 — Phase 2 Requirements

**Project**: Multi-Agent Autonomous Researcher (MAAR)
**Phase**: 2 — First End-to-End Research Workflow
**Status**: Planning

---

## 1. Scope

Phase 2 introduces the first genuinely functional research capability into MAAR. A user can submit a research question, optionally upload supporting documents, and start a research run. The backend executes a sequential research workflow — gathering information from the internet and/or uploaded documents, synthesizing the evidence, and generating a structured report. The user can monitor progress and view the completed result.

Phase 2 does NOT introduce multi-agent orchestration, autonomous agent planning, or streaming infrastructure. It is deliberately a single-workflow, sequential, modular implementation.

---

## 2. User Stories

### US-01 — Start a Research Run
As a user, I want to open an existing research project, submit a research question, optionally upload documents, choose my information sources, and start a research run — so that MAAR begins investigating on my behalf.

### US-02 — Monitor Progress
As a user, I want to see the current status and stage of a running research workflow — so that I know it is progressing and can identify when it completes or fails.

### US-03 — View Completed Results
As a user, I want to open the completed research report containing an executive summary, key findings, supporting evidence with citations, and identified limitations — so that I can review what was found and trace it back to sources.

### US-04 — Upload Documents
As a user, I want to upload PDF, DOCX, or TXT files as supplemental research material — so that the research engine can incorporate information from my own documents.

### US-05 — Web-Only Research
As a user, I want to perform research using only web sources (no document upload) — so that I can get fast results based on publicly available information.

### US-06 — Document-Only Research
As a user, I want to perform research using only my uploaded documents (no web search) — so that I can analyze private or proprietary materials without external lookups.

### US-07 — View Research History
As a user, I want to see previous research runs on a project, their status, and open their completed reports — so that I can review past work and compare runs.

### US-08 — Handle Failures Gracefully
As a user, when a research run fails, I want to see a clear failure message — so that I understand what went wrong and can take action.

---

## 3. Functional Requirements

### 3.1 Research Submission
- FR-01: The workspace must display a research submission form within an active project.
- FR-02: The form must allow the user to confirm or override the research question (defaulting to the project's research question).
- FR-03: The form must allow the user to upload zero or more documents (PDF, DOCX, TXT).
- FR-04: The form must allow the user to select at least one information source: web search, uploaded documents, or both.
- FR-05: Submitting with no source selected must be blocked with a clear validation message.
- FR-06: Selecting document-only with no uploaded files must be blocked with a clear validation message.
- FR-07: Each upload must display filename, size, and a remove button before submission.

### 3.2 Research Run Lifecycle
- FR-08: Submitting the form creates a ResearchRun record in the database with status `pending`.
- FR-09: The backend transitions the run through `pending → running → completed` (or `failed`).
- FR-10: The run must record its current workflow stage as a human-readable label.
- FR-11: The run must record `started_at` and `completed_at` timestamps.
- FR-12: A failed run must persist a `error_message` field with a safe, non-leaking description.
- FR-13: At most one run per project may be in `running` state at any time (duplicate submission prevention).

### 3.3 Document Processing
- FR-14: Uploaded files must be validated for extension, MIME type, and size (max 20 MB per file).
- FR-15: Accepted files must be stored under a safe, project-scoped directory.
- FR-16: Text must be extracted from PDF, DOCX, and TXT files.
- FR-17: Each document must retain its original filename and a content hash for deduplication.
- FR-18: Corrupted, encrypted, password-protected, or unreadable files must be rejected with a clear error; they must not abort the entire run.
- FR-19: Extracted text must be chunked to respect LLM context limits without a vector database.

### 3.4 Web Research
- FR-20: The web research stage must query the configured search provider with the research question.
- FR-21: At least 5 and at most 10 results must be attempted per run (configurable).
- FR-22: For each result, the system must attempt to fetch and extract the main text content of the page.
- FR-23: Source title, URL, retrieval timestamp, and extracted content must be persisted.
- FR-24: Failed fetches (timeout, 4xx/5xx, parse failure) must be recorded but must not abort the run.
- FR-25: Duplicate URLs (same URL appearing multiple times in results) must be deduplicated.
- FR-26: SSRF protection: only public HTTP/HTTPS URLs are permitted; private IP ranges and localhost are blocked.

### 3.5 Evidence and Synthesis
- FR-27: All evidence — regardless of source — must be stored in a normalized evidence record format.
- FR-28: Each evidence record must preserve its provenance (web or document, source identifier, origin metadata).
- FR-29: The synthesis stage must prepare a context window from available evidence and pass it to the LLM.
- FR-30: Evidence must be prioritized by relevance heuristic (keyword overlap with research question) when total size exceeds context limit.
- FR-31: The LLM must be instructed to only make claims supported by the provided evidence.

### 3.6 Report Generation
- FR-32: The generated report must contain: research question, executive summary, key findings, supporting evidence with citations, observations, contradictions (if any), limitations, and source list.
- FR-33: Web citations must include clickable URLs.
- FR-34: Document citations must reference the original filename and page/chunk number where possible.
- FR-35: The report must be persisted to the database and linked to the ResearchRun.
- FR-36: The report must be retrievable via API after the run completes.

### 3.7 Research History
- FR-37: The workspace must list all research runs for the project, ordered by creation date descending.
- FR-38: Each run entry must show: status badge, creation date, completion date (if any), source types used.
- FR-39: Completed runs must link to their report view.

---

## 4. Non-Functional Requirements

- NFR-01: The research workflow must execute as a FastAPI background task. It must not block the HTTP response.
- NFR-02: Background task failure must update the run status to `failed` — it must never silently disappear.
- NFR-03: All LLM and web requests must have configurable timeouts (defaults: LLM 120s, web fetch 15s per URL).
- NFR-04: The backend must remain responsive to other API requests while a research run executes.
- NFR-05: All file uploads must be streamed to disk; they must not be fully buffered in memory.
- NFR-06: File storage must be organized under a configurable `UPLOAD_DIR` (default: `./uploads/`).
- NFR-07: No API credentials (LLM, search provider) may be hardcoded; all must be read from environment variables.
- NFR-08: All extracted text from documents and web pages must be treated as untrusted input.
- NFR-09: Logs must not contain extracted document content, LLM prompts, or user-supplied text at INFO level.
- NFR-10: The full research workflow from submission to completed report must complete within 5 minutes under normal conditions.

---

## 5. Explicit Exclusions (Phase 2)

The following are explicitly out of scope for Phase 2:

| Excluded Capability | Reason |
|---|---|
| Multi-agent orchestration | Phase 3+ — requires LangGraph or equivalent |
| LangGraph | Deferred — sequential workflow sufficient now |
| WebSocket streaming | Polling is sufficient for Phase 2 |
| Redis / Celery task queues | No distributed requirement yet |
| Qdrant / vector databases | Simple context windowing sufficient |
| Human-in-the-loop approval | Phase 3+ feature |
| Run cancellation | Requires task tracking infrastructure not yet present |
| Multiple concurrent runs per project | Single active run constraint simplifies Phase 2 |
| Automatic re-runs / retry scheduling | Future enhancement |
| Advanced citation verification | LLM trust boundary addressed; deep verification is Phase 3 |
| Cloud deployment | Local development only |
| Authentication / multi-tenancy | Not required until Phase 3 |
| Image or audio file processing | PDF/DOCX/TXT only |
| OCR for scanned PDFs | Deferred — requires significant additional dependency |
| Structured data extraction (tables, charts) | Deferred |

---

## 6. Assumptions

- A1: The user has configured a valid LLM API key in `.env` before starting the application.
- A2: The user has configured a valid search provider API key (or has accepted web-only mode using a free-tier provider) in `.env`.
- A3: The local machine has internet access for web research runs.
- A4: Phase 1 database (`maar_dev.db`) is operational and the `research_projects` table exists.
- A5: Python packages for document parsing (pypdf, python-docx) can be installed via pip on Windows.
- A6: The research question for a run defaults to the project's `research_question` field but can be overridden per run.
