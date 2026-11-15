# 30 — Phase 4 Implementation Audit

**Project:** Multi-Agent Autonomous Researcher (MAAR)
**Phase:** 4 — Intelligence, Evidence Extraction, Fact-Checking and Citation Verification
**Date:** November 2026
**Auditors:** Senior AI Architect / Technical Lead
**Revision:** 2 — Updated to reflect finalized architectural decisions

---

## 1. Audit Purpose

This document records the findings of a complete repository audit conducted prior to Phase 4 implementation. It classifies every capability required by Phase 4 as already implemented, partially implemented, not implemented, or implemented but requiring correction.

**Finalized decisions incorporated in this revision:**
- Verification depth: basic (default, key findings + high-impact claims) / thorough (all claims). Applies to BOTH sequential and multi-agent workflows.
- arXiv routing: not restricted to STEM — category-based routing with query relevance, all categories eligible.
- Critic cycle limit: maximum 2 cycles, no forced approval — terminal statuses are `needs_attention` or `rejected`, not auto-approved.
- Claim verification is a reusable, workflow-independent backend service callable from both sequential and multi-agent pipelines.

---

## 2. Classification Key

| Symbol | Meaning |
|--------|---------|
| ✅ | Already implemented and directly reusable |
| ⚠️ | Partially implemented — requires extension or correction |
| ❌ | Not implemented — new work required |
| 🔧 | Implemented but requires correction before use |

---

## 3. Backend Infrastructure

### 3.1 FastAPI Application

| Capability | Status | Notes |
|-----------|--------|-------|
| API server (FastAPI + uvicorn) | ✅ | Stable, async, production-ready |
| Route registration (`api/v1/router.py`) | ✅ | Clean prefix-based registration |
| Health check endpoint | ✅ | DB connectivity check included |
| Pydantic v2 validation layer | ✅ | Used consistently across all routes |
| HTTP error handling (422, 404, 409, 500) | ✅ | Consistent pattern across all routes |
| CORS configuration | ✅ | ALLOWED_ORIGINS env var |
| Background task execution | ✅ | FastAPI BackgroundTasks used for workflow dispatch |

### 3.2 Database and ORM

| Capability | Status | Notes |
|-----------|--------|-------|
| SQLite with aiosqlite async driver | ✅ | Fully operational |
| SQLAlchemy 2.0 async ORM | ✅ | All models use mapped_column, async sessions |
| Alembic migrations (2 versions applied) | ✅ | Phase 2: 835db006d5e4, Phase 3: 219aca45d63e |
| Async session factory (AsyncSessionLocal) | ✅ | Imported module-level in all agents/nodes |
| Cascade deletes (project → run → evidence) | ✅ | FK constraints with CASCADE defined |
| UTC-aware timestamps | ✅ | `datetime.now(timezone.utc)` used throughout |
| JSON stored as TEXT in SQLite | ✅ | key_findings, sources, objectives all TEXT columns |

### 3.3 Existing ORM Models (9 tables)

| Model | Status | Notes |
|-------|--------|-------|
| ResearchProject | ✅ | Stable — gains `category` use for source routing |
| ResearchRun | ⚠️ | Needs `verification_depth`, `llm_call_count`, `estimated_cost_usd`, `total_tokens_used` columns |
| UploadedDocument | ⚠️ | Needs `chunk_count`, `has_images`, `ocr_attempted` columns |
| EvidenceRecord | ⚠️ | Needs `source_id`, `chunk_id`, `evidence_type`, `evidence_relationship`, `section_name`, `extraction_method`, `extraction_confidence` columns |
| ResearchReport | ⚠️ | Needs `verification_summary`, `critic_review_id`, `review_status`, `has_validated_citations` columns |
| ResearchPlan | ✅ | Complete — no Phase 4 changes needed |
| ResearchTask | ✅ | Complete — no Phase 4 changes needed |
| AgentExecutionEvent | ✅ | Append-only audit log — no changes needed |
| LangGraph checkpoint tables | ✅ | Managed by AsyncSqliteSaver — no changes needed |

**New tables required for Phase 4:**
- `document_chunks` — structured extracted chunks with section/heading metadata (document-scoped, run-independent)
- `sources` — normalized source catalog with academic metadata, DOI, author, publication date
- `claims` — atomic factual claims extracted from report findings
- `claim_verifications` — per-claim verification status, rationale, evidence links
- `critic_reviews` — structured Critic Agent output per run, versioned

### 3.4 Configuration

| Capability | Status | Notes |
|-----------|--------|-------|
| LLM provider abstraction (OpenAI / Watsonx) | ✅ | Switchable via LLM_PROVIDER env var |
| Web search provider abstraction (Tavily) | ✅ | Switchable via SEARCH_PROVIDER env var |
| SSRF protection | ✅ | `is_safe_url()` blocks private/local IPs |
| Upload size and type validation | ✅ | MAX_UPLOAD_SIZE_MB, allowed extensions |
| Context budget (LLM_CONTEXT_BUDGET_CHARS) | ✅ | 60,000 chars default |
| Multi-agent cycle limit (MAX_SUPERVISOR_CYCLES) | ✅ | 3 default |
| LangSmith optional integration | ✅ | Environment-variable only, not in Settings class |

**New config required for Phase 4:**

| Variable | Default | Purpose |
|----------|---------|---------|
| `VERIFICATION_DEPTH` | `"basic"` | Default verification depth for all new runs |
| `MAX_CLAIMS_PER_RUN` | `20` | Hard cap on claims verified per run |
| `ARXIV_ENABLED` | `false` | Enable arXiv provider (free, no key) |
| `SEMANTIC_SCHOLAR_API_KEY` | `""` | Optional — enables Semantic Scholar with higher rate limits |
| `OCR_ENABLED` | `false` | Whether to attempt LLM-based OCR on image PDFs |
| `CRITIC_MAX_REVIEW_CYCLES` | `2` | Maximum Critic review cycles per run |
| `LLM_COST_PER_1K_TOKENS` | `0.0` | For cost tracking — set per provider/model |
| `ENABLE_LLM_USAGE_TRACKING` | `true` | Whether to track token counts and estimated cost |

---

## 4. Phase 2 Sequential Workflow

| Capability | Status | Notes |
|-----------|--------|-------|
| Web search and retrieval | ✅ | Snippet fallback added; robust to missing raw_content |
| Document upload and storage | ✅ | PDF, DOCX, TXT validated and stored |
| Document text extraction (PDF, DOCX, TXT) | ✅ | pypdf, python-docx, plain text |
| Text chunking (8000-char chunks, 400 overlap) | ✅ | `chunk_text()` in evidence_normalizer |
| Evidence normalization | ✅ | `NormalizedEvidence` dataclass, relevance scoring |
| Evidence persistence (EvidenceRecord) | ✅ | Stored with source_type, url, page_number |
| Context selection within budget | ✅ | `build_evidence_context()` greedy selection |
| Report generation (LLM + structured JSON) | ✅ | Retry + template-echo detection added |
| Report persistence (ResearchReport) | ✅ | JSON fields stored as TEXT |
| **Claim verification (basic depth)** | ❌ | **New for Phase 4 — applies to sequential runs** |
| **LLM usage tracking** | ❌ | **New for Phase 4 — applies to all runs** |

**Gap:** Text extraction preserves content but does not preserve section headings, heading hierarchy, or table structure. Phase 4 requires richer chunk metadata.

**Updated scope:** Phase 4 claim verification is a reusable service. Sequential runs will invoke it after report generation with `verification_depth="basic"` by default. The Critic Agent and iterative review loop are multi-agent only.

---

## 5. Phase 3 Multi-Agent Workflow

| Capability | Status | Notes |
|-----------|--------|-------|
| LangGraph 1.2.20 with AsyncSqliteSaver | ✅ | Compiled graph singleton, async checkpointing |
| ResearchWorkflowState TypedDict | ✅ | 19 fields with append_unique and merge reducers |
| Graph topology (6 nodes, conditional routing) | ✅ | Full topology in workflow.py |
| initialize_run_node | ✅ | Validates run, logs workflow_start event |
| finalize_report_node | ✅ | Loads evidence from DB, reuses Phase 2 report generation |
| fail_workflow_node | ✅ | Marks run failed, cleans up running tasks |
| planning_node (Planner Agent) | ✅ | LLM → ResearchPlan, 1 retry, dedup, priority sort |
| research_node (Research Agent) | ✅ | Web search + doc extraction, evidence persistence, LLM synthesis |
| supervisor_node (Supervisor Agent) | ✅ | State evaluation, forced termination, 6 decision types |
| Plan/task persistence (plan_service) | ✅ | Versioned, task_order preserved |
| Agent event audit log (event_service) | ✅ | Append-only, 9 event types |
| Graph executor (background task entry point) | ✅ | run_multi_agent_workflow() |
| Sequential routing to Phase 2 workflow | ✅ | workflow_mode="sequential" routes to run_research_workflow |

**Missing from Phase 3 / required for Phase 4:**
- No Critic Agent node
- No claim identification step
- No claim verification step (will use shared service)
- No evidence-to-claim linking
- No citation validation step
- No source deduplication across tasks (same URL can appear in multiple tasks)
- No LLM usage tracking

---

## 6. Document Processing

| Capability | Status | Notes |
|-----------|--------|-------|
| File upload (multi-file, multipart) | ✅ | Up to 20 MB per file |
| MIME type validation (python-magic) | ✅ | Type must match extension |
| Duplicate detection (SHA-256 hash) | ✅ | Reuses storage path if same hash |
| PDF text extraction (pypdf) | ✅ | Page-by-page extraction |
| DOCX extraction (python-docx) | ✅ | Paragraph-level extraction |
| TXT extraction | ✅ | UTF-8 with error replacement |
| Encrypted PDF detection | ✅ | FileNotDecryptedError caught and reported |
| Text chunking | ✅ | Fixed-size with overlap |
| Chunk-to-page-number preservation | ⚠️ | page_number stored on EvidenceRecord but not on chunk itself |
| Section/heading extraction | ❌ | Not implemented — chunking is purely text-length based |
| Table extraction | ❌ | Not implemented |
| OCR for scanned PDFs | ❌ | Planned as LLM-based (conditional on vision model availability) |
| DocumentChunk ORM model | ❌ | Not implemented — currently only EvidenceRecord used |
| Extraction quality assessment | ❌ | No low-text-content detection |
| Structured chunk metadata | ❌ | Section title, heading level, table flag — not present |

---

## 7. Source Collection and Retrieval

| Capability | Status | Notes |
|-----------|--------|-------|
| Tavily web search | ✅ | General web coverage |
| Raw content fetch (trafilatura) | ✅ | With SSRF protection and timeout |
| Snippet fallback for failed fetches | ✅ | Added after Phase 3 |
| Source deduplication (by URL within task) | ⚠️ | Dedup per task only — same URL can recur across tasks in a run |
| Source metadata (URL, title, date) | ⚠️ | published_date in SearchResult — not persisted to DB |
| Source credibility assessment | ❌ | Not implemented |
| arXiv academic paper retrieval | ❌ | Not implemented — Phase 4 |
| Semantic Scholar integration | ❌ | Not implemented — Phase 4 |
| Multi-provider routing by category + query | ❌ | Not implemented — Phase 4 |
| Source ORM model (separate from EvidenceRecord) | ❌ | Sources are inlined into EvidenceRecord |
| DOI-based retrieval | ❌ | Not implemented |
| Publisher/organization metadata | ❌ | Not implemented |
| Peer-review status metadata | ❌ | Not implemented — arXiv preprints must not be assumed peer-reviewed |
| Source freshness evaluation | ❌ | Not implemented |
| Run-level source deduplication across tasks | ❌ | Not implemented |
| Rate limiting per search provider | ❌ | Relies on provider limits |

---

## 8. Evidence Schema and Extraction

| Capability | Status | Notes |
|-----------|--------|-------|
| EvidenceRecord ORM (14 fields) | ✅ | Covers basic source attribution |
| NormalizedEvidence dataclass | ✅ | In-memory representation before DB persistence |
| Evidence-to-task linking (task_id FK) | ✅ | Added in Phase 3 |
| Evidence source type (web vs document) | ✅ | source_type field |
| Evidence relevance scoring | ✅ | Token-overlap scoring (simple but functional) |
| Atomic claim extraction | ❌ | Not implemented |
| Evidence relationship types (supports/contradicts) | ❌ | Not implemented — no evidence_relationship field |
| Evidence type classification | ❌ | No statistical/experimental/observational distinction |
| Section name preservation in evidence | ❌ | Not implemented |
| Extraction method metadata | ❌ | Not implemented |
| Extraction confidence score | ❌ | Not implemented |
| Contradiction detection between evidence items | ❌ | Not implemented |
| Direct quote vs paraphrase distinction | ❌ | Not implemented |

---

## 9. Claim Identification and Verification

| Capability | Status | Notes |
|-----------|--------|-------|
| Claim ORM model | ❌ | Not implemented |
| Claim extraction from report findings (basic) | ❌ | Not implemented |
| Claim extraction from full report (thorough) | ❌ | Not implemented |
| High-impact claim prioritization (basic depth) | ❌ | Not implemented — basic mode must prioritize statistical, causal, medical claims |
| Claim type classification | ❌ | Not implemented |
| Evidence-to-claim matching | ❌ | Not implemented |
| Verification status (supported/contradicted/etc.) | ❌ | Not implemented |
| ClaimVerification ORM model | ❌ | Not implemented |
| Verification depth config (basic/thorough) | ❌ | Not implemented |
| Verification depth stored on run | ❌ | Not implemented |
| LLM-based claim verification | ❌ | Not implemented |
| Verification rationale storage | ❌ | Not implemented |
| Reusable service (callable from both workflows) | ❌ | Not implemented — must not be LangGraph-specific |
| Sequential workflow integration | ❌ | Not implemented — Phase 4 adds this |

---

## 10. LLM Usage and Cost Tracking

| Capability | Status | Notes |
|-----------|--------|-------|
| Per-run LLM call count | ❌ | Not implemented — required for Phase 4 |
| Per-run token usage (input + output) | ❌ | Not implemented |
| Per-run estimated cost | ❌ | Not implemented |
| Per-run API latency tracking | ❌ | Not implemented |
| Provider/model logging | ❌ | Config values logged at startup only |
| LLM usage stored on ResearchRun | ❌ | No columns exist for this |

**Note:** Cost optimization must never compromise evidence traceability. Usage tracking is observability only — it does not gate features or degrade verification quality.

---

## 11. Critic / Reviewer Agent

| Capability | Status | Notes |
|-----------|--------|-------|
| Critic Agent LangGraph node | ❌ | Not implemented |
| CriticReview ORM model | ❌ | Not implemented |
| CriticReview Pydantic schema | ❌ | Not implemented |
| Supervisor routing on Critic output | ❌ | Not implemented — Supervisor has no critic_review decisions |
| Bounded retry (max 2 cycles, no forced approval) | ❌ | Not implemented |
| Terminal statuses: needs_attention / rejected | ❌ | Not implemented — distinct from auto-approval |
| Unresolved issues visible in final report | ❌ | Not implemented |
| Review API endpoint | ❌ | Not implemented |
| Critic applies to multi-agent runs only | — | By design — sequential runs do not get Critic Agent |

---

## 12. Citation Management

| Capability | Status | Notes |
|-----------|--------|-------|
| Claim-to-evidence relationship | ❌ | Not implemented |
| Evidence-to-source relationship | ⚠️ | Implicit via EvidenceRecord.url/document_id — not a separate Citation model |
| Citation ORM model | ❌ | Not implemented |
| Citation metadata (DOI, page, section) | ❌ | Not implemented |
| Citation validation (verify evidence exists) | ❌ | Not implemented |
| Citation formatting (APA, IEEE) | ❌ | Not implemented — must be deterministic, not LLM-generated |
| Report-level citation traceability | ❌ | Not implemented |
| Broken URL detection | ❌ | Not implemented |
| Bibliography generation | ❌ | Not implemented |
| Available to both workflows | ❌ | Must be a shared service, not multi-agent only |

---

## 13. API Endpoints

| Capability | Status | Notes |
|-----------|--------|-------|
| Document processing status endpoint | ❌ | Not implemented |
| Document chunks endpoint | ❌ | Not implemented |
| Sources list/detail endpoints | ❌ | Not implemented — no Source model |
| Evidence list/filter endpoints | ❌ | Not implemented |
| Claims list/detail endpoints | ❌ | Not implemented |
| Claim verification endpoints | ❌ | Not implemented |
| Critic review endpoints | ❌ | Not implemented — multi-agent only |
| Citation endpoints | ❌ | Not implemented |
| Verification depth on StartRunRequest | ❌ | Not implemented |
| LLM usage fields on RunResponse | ❌ | Not implemented |

---

## 14. Frontend

| Capability | Status | Notes |
|-----------|--------|-------|
| Research workspace layout | ✅ | Tabs-based panel (ResearchPanel) |
| Research form (question, mode, sources) | ✅ | Including sequential/multi-agent toggle |
| Verification depth selector on form | ❌ | Not implemented |
| Run status display (sequential) | ✅ | RunStatusCard with polling |
| Multi-agent status display | ✅ | MultiAgentStatusCard with plan + activity feed |
| Research report display | ✅ | ResearchReportView |
| Document upload area | ✅ | FileUploadArea |
| Run history | ✅ | RunHistory |
| Source panel | ❌ | Not implemented — both workflows |
| Evidence explorer | ❌ | Not implemented — both workflows |
| Claim verification panel | ❌ | Not implemented — both workflows |
| Critic review panel | ❌ | Not implemented — multi-agent only |
| Clickable citations in report | ❌ | Not implemented — both workflows |
| Verification status badges | ❌ | Not implemented |
| LLM usage display on run | ❌ | Not implemented |
| Phase 4 type definitions | ❌ | Claim, Source, Citation, CriticReview, VerificationStatus types needed |
| Phase 4 API calls | ❌ | Corresponding fetch functions needed |

---

## 15. Testing

| Capability | Status | Notes |
|-----------|--------|-------|
| In-memory SQLite test DB with auto-reset | ✅ | conftest.py autouse fixture |
| MockLLMProvider (response/fail/fail_times) | ✅ | Supports sequential response injection |
| MockWebSearchProvider (results/fail) | ✅ | Supports custom result lists |
| Health check tests | ✅ | 5 tests |
| Project CRUD tests | ✅ | 50+ tests |
| Run API tests | ✅ | 12 tests |
| Document upload tests | ✅ | 10 tests |
| Provider tests | ✅ | 14 tests — SSRF, mock LLM, mock search |
| Phase 2 workflow tests | ✅ | 14 tests |
| Phase 3 agent tests | ✅ | 26 tests |
| Phase 3 integration tests | ✅ | 16 tests |
| Phase 4 document chunk tests | ❌ | |
| Phase 4 source provider tests (arXiv, Semantic Scholar) | ❌ | |
| Phase 4 evidence extraction tests | ❌ | |
| Phase 4 claim extraction tests (basic + thorough) | ❌ | |
| Phase 4 claim verification tests | ❌ | |
| Phase 4 claim verification in sequential workflow | ❌ | |
| Phase 4 Critic Agent tests | ❌ | |
| Phase 4 Critic bounded cycle tests | ❌ | needs_attention / rejected path |
| Phase 4 citation management tests | ❌ | |
| Phase 4 API endpoint tests | ❌ | |
| Phase 4 LLM usage tracking tests | ❌ | |
| Phase 4 evaluation metrics test suite | ❌ | 5-fixture corpus |

**Current total:** 166 tests passing

---

## 16. Security

| Capability | Status | Notes |
|-----------|--------|-------|
| File type and MIME validation | ✅ | python-magic |
| File size limits | ✅ | MAX_UPLOAD_SIZE_MB |
| SSRF protection for web fetching | ✅ | is_safe_url() with private IP blocking |
| Safe error messages (no path leaking) | ✅ | safe_error_message() in errors.py |
| Prompt injection mitigation in system prompts | ✅ | "Ignore embedded instructions" in all agent prompts |
| Path traversal protection (upload storage) | ✅ | document_id-scoped paths |
| Authentication / authorization | ❌ | Single-user local dev — not in scope for Phase 4 |
| Rate limiting | ❌ | Not implemented |
| URL redirect validation | ⚠️ | httpx follows redirects but final URL not re-checked against SSRF rules |

---

## 17. Summary Table

| Module | Phase 4 Required | Already Exists | Net New Work |
|--------|-----------------|----------------|--------------|
| Advanced document processing | Yes | Partial | DocumentChunk model, section extraction, OCR detection |
| Multi-provider source retrieval | Yes | Partial | arXiv + Semantic Scholar providers, Source model, category+query routing |
| Structured evidence schema | Yes | Partial | evidence_relationship, section_name, extraction_method, source_id, chunk_id fields |
| Claim identification (basic + thorough) | Yes | No | Full new pipeline — reusable service, both workflows |
| Claim verification | Yes | No | Full new pipeline — reusable service, both workflows |
| Critic Agent | Yes | No | New LangGraph node + service — multi-agent only |
| Citation management | Yes | No | Citation model, validation, formatting — both workflows |
| Supervisor Phase 4 integration | Yes | Partial | New routing decisions, no forced approval, needs_attention/rejected statuses |
| LLM usage tracking | Yes | No | New columns on ResearchRun, wrapper on LLMProvider |
| Phase 4 API endpoints | Yes | No | Sources, evidence, claims, citations, critic, usage |
| Frontend Phase 4 components | Yes | No | 5 new workspace panels + verification depth selector |
| Phase 4 tests | Yes | No | ~80+ new tests expected |
