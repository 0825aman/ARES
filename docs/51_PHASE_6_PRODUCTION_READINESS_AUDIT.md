# 51 — Phase 6 Production Readiness Audit

## MAAR — Multi-Agent Autonomous Researcher
## Audit Date: 2026-11-14 | Phase 1–5 Complete

---

## 1. Purpose

This document records the findings of a systematic production-readiness audit of the MAAR codebase after the completion of Phases 1–5. It classifies every relevant architectural area and identifies gaps that Phase 6 must address.

---

## 2. Classification Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Implemented and working |
| ⚠️ | Implemented but incomplete or requires hardening |
| ❌ | Planned but not implemented / missing |
| 🔴 | Broken or requires correction |
| — | Not applicable to this project |

---

## 3. Repository Overview

```
maar/
├── backend/          FastAPI + SQLAlchemy + LangGraph
├── frontend/         Next.js 14 (App Router) + TypeScript + Tailwind
├── docs/             Planning documents (40–50)
├── .gitignore        ✅ Covers Python, Node, .env, *.db
├── README.md         ✅ Local setup instructions (dev-mode only)
└── maar-phase*-plan.md
```

No Docker files exist anywhere in the repository.

---

## 4. Frontend Audit

### 4.1 Application Structure

| Feature | Status | Notes |
|---------|--------|-------|
| Next.js 14 App Router | ✅ | Pages, layouts, dynamic routes in place |
| TypeScript throughout | ✅ | tsconfig.json, strict mode |
| Tailwind CSS + shadcn/ui | ✅ | components.json, Radix UI primitives |
| Dashboard page | ✅ | Project overview, stats, empty state |
| Projects list page | ✅ | Full CRUD via API |
| Project detail page | ✅ | Research workspace, tabs |
| Research workspace | ✅ | SSE-driven live updates (Phase 5) |
| Settings page | ✅ | Placeholder |
| Login / Registration | ❌ | Not present — local-first single-user design |
| Auth middleware (middleware.ts) | ❌ | No protected routes |
| Error boundary (error.tsx) | ❌ | No global error boundary |
| Loading boundary (loading.tsx) | ⚠️ | Skeleton states per-component, no global loading.tsx |
| Responsive design | ✅ | Mobile-aware layout |

### 4.2 API Client

| Feature | Status | Notes |
|---------|--------|-------|
| apiFetch / apiFetchMultipart | ✅ | Generic typed fetch wrappers |
| ApiError class | ✅ | Custom error with HTTP status |
| FastAPI detail extraction | ✅ | Handles string and array detail formats |
| Authorization header support | ❌ | No bearer token injection |
| Request trace ID header | ❌ | No correlation ID propagation |
| Retry logic | ❌ | No automatic retries on network failure |
| Request timeout | ❌ | No timeout on fetch calls |
| Environment URL config | ✅ | NEXT_PUBLIC_API_URL + API_URL |

### 4.3 State and Data

| Feature | Status | Notes |
|---------|--------|-------|
| React useState (no library) | ✅ | Intentional (Phase 5 decision) |
| useSSE hook | ✅ | Fetch-based SSE, reconnect, Last-Event-ID |
| Approval workflow state | ✅ | pendingApproval, ApprovalBanner, ApprovalModal |
| Export panel | ✅ | PDF/DOCX/Markdown download |
| Cross-link (evidence → source) | ✅ | Programmatic tab switch + drawer open |
| Live badges | ✅ | LiveBadge with pulse animation |

---

## 5. Backend Audit

### 5.1 Application Layer

| Feature | Status | Notes |
|---------|--------|-------|
| FastAPI app | ✅ | main.py, lifespan, CORS, routers |
| Startup auto-migration | ✅ | Alembic upgrade head on startup |
| Stuck-run recovery | ✅ | Marks pending/running runs as failed on restart |
| Upload/export dir creation | ✅ | mkdir on startup |
| CORSMiddleware | ✅ | Whitelist from ALLOWED_ORIGINS env var |
| Request ID middleware | ❌ | No trace correlation |
| Rate limiting middleware | ❌ | No request rate limiting |
| Request logging middleware | ❌ | No structured request/response log |
| Global exception handler | ❌ | No @app.exception_handler(Exception) |
| Graceful shutdown | ⚠️ | ASGI lifespan handles DB recovery but no graceful drain |

### 5.2 API Routes

| Route Module | Status | Notes |
|-------------|--------|-------|
| health.py | ✅ | GET /health checks DB |
| projects.py | ✅ | Full CRUD |
| runs.py | ✅ | Start, list, get, report |
| documents.py | ✅ | Upload, list, delete |
| sources.py | ✅ | List, get by ID |
| evidence.py | ✅ | List, get by ID |
| claims.py | ✅ | List |
| reviews.py | ✅ | Get critic review |
| citations.py | ✅ | List, bibliography |
| sse.py | ✅ | GET stream endpoint (Phase 5) |
| approvals.py | ✅ | Approval lifecycle (Phase 5) |
| exports.py | ✅ | Export triggers and download (Phase 5) |
| auth.py | ❌ | No authentication routes |
| users.py | ❌ | No user management routes |

### 5.3 Configuration

| Setting | Status | Notes |
|---------|--------|-------|
| .env.example | ✅ | Comprehensive, 78 lines, no real secrets |
| Pydantic Settings | ✅ | Type-safe config with defaults |
| LOG_FORMAT (text/json) | ✅ | Switchable via env |
| EXPORT_DIR | ✅ | Phase 5 addition |
| UPLOAD_DIR | ✅ | Configurable |
| APP_ENV | ✅ | development / production |
| Required API key validation | ❌ | Empty string default (no startup failure on missing key) |
| EXPORT_DIR disk space limit | ❌ | No configured limits |
| Config documentation | ⚠️ | .env.example has inline comments but no reference doc |

### 5.4 Error Handling

| Feature | Status | Notes |
|---------|--------|-------|
| Route-level try/except | ✅ | Present in all route handlers |
| safe_error_message() | ✅ | Strips internal paths, truncates at 500 chars |
| GraphRecursionError catch | ✅ | Executor top-level catch |
| DB error handling in routes | ✅ | Returns 500 with sanitized message |
| Pydantic validation errors | ✅ | 422 returned automatically by FastAPI |
| Global exception handler | ❌ | Unhandled exceptions return 500 without logging |
| Consistent error response format | ⚠️ | FastAPI default {"detail": ...} but not standardized |
| Request ID in error responses | ❌ | No correlation |
| Stack trace suppression | ✅ | safe_error_message strips paths |

### 5.5 Logging

| Feature | Status | Notes |
|---------|--------|-------|
| Structured JSON logging | ✅ | Optional via LOG_FORMAT=json |
| Human-readable text logging | ✅ | Default |
| Startup/recovery logging | ✅ | Stuck run recovery logged |
| Agent event logging (DB) | ✅ | AgentExecutionEvent model |
| LLM usage logging | ✅ | llm_call_count, tokens, cost on ResearchRun |
| Request trace ID | ❌ | No correlation ID in logs |
| Request/response logging | ❌ | No middleware for request duration |
| Sensitive data redaction | ⚠️ | API keys not logged; prompts not filtered |
| Log level per module | ⚠️ | Only watchfiles and httpx suppressed |
| Centralized log destination | ❌ | stdout only |

### 5.6 Database

| Feature | Status | Notes |
|---------|--------|-------|
| SQLite + aiosqlite | ✅ | Local-first default |
| SQLAlchemy async ORM | ✅ | AsyncSession, async_sessionmaker |
| Alembic migrations (13 files) | ✅ | Full history from Phase 2 to 5 |
| Auto-migration on startup | ✅ | upgrade head in lifespan |
| Foreign key constraints (DDL) | ✅ | ondelete CASCADE on all FKs |
| Cascade deletes (ORM) | ✅ | cascade="all, delete-orphan" |
| Indexes on key columns | ⚠️ | status, created_at, category indexed; FK columns not all indexed |
| WAL mode | ❌ | Not configured (default journal_mode=DELETE) |
| SQLite busy_timeout | ❌ | Not configured (concurrent writes may fail silently) |
| SQLite foreign_keys PRAGMA | ❌ | Not enforced at runtime (DDL exists but SQLite ignores FK by default) |
| Connection pooling config | ❌ | Default SimplePool (no pool_size, max_overflow) |
| Database backup procedure | ❌ | No documented backup/restore |
| Data retention policy | ❌ | No cleanup for old runs/exports |
| PostgreSQL compatibility | ⚠️ | Mostly compatible; SQLite-specific paths in Alembic env.py |

### 5.7 AI and Agent System

| Feature | Status | Notes |
|---------|--------|-------|
| Supervisor agent | ✅ | Routes decisions across all phases |
| Planner agent | ✅ | research_question → structured plan |
| Researcher agent | ✅ | Web and document evidence collection |
| Critic agent | ✅ | Report quality review |
| Claim verification | ✅ | Phase 4, basic and thorough depth |
| Citation validator | ✅ | Phase 4 |
| LLM provider abstraction | ✅ | OpenAI, Watsonx, Groq, Gemini, Mock |
| Fallback LLM provider | ✅ | Rate-limit fallback chain |
| LangGraph checkpointing | ✅ | AsyncSqliteSaver, thread_id=run_id |
| Human approval interrupts | ✅ | interrupt_before at plan + critic checkpoints |
| Web retrieval (Tavily) | ✅ | Primary search provider |
| Academic retrieval (arXiv, S2) | ✅ | Optional, Phase 4 |
| SSRF protection | ✅ | IP blocklist in web_fetcher.py |
| Prompt injection protection | ⚠️ | "Ignore instructions" in system prompt only |
| Tool permission enforcement | ⚠️ | No per-agent tool restrictions in code |
| Agent retry with backoff | ⚠️ | LLM rate-limit fallback only; no structured retry policy |
| Workflow recursion guard | ✅ | LANGGRAPH_DEFAULT_RECURSION_LIMIT=100 |
| LLM usage tracking | ✅ | Approximate token count + cost |

### 5.8 Security

| Feature | Status | Notes |
|---------|--------|-------|
| CORS whitelist | ✅ | Localhost-only default |
| SSRF protection | ✅ | IP blocklist in web_fetcher.py |
| SQL injection prevention | ✅ | SQLAlchemy ORM (parameterized) |
| File upload size limit | ✅ | MAX_UPLOAD_SIZE_MB=20 |
| File count limit per upload | ✅ | Max 10 files per request |
| Path traversal protection | ⚠️ | No explicit filename sanitization visible |
| Prompt injection protection | ⚠️ | Weak (instruction text only) |
| Authentication | ❌ | Intentionally absent (local tool) |
| RBAC / authorization | ❌ | No roles, all data globally accessible |
| Secrets in env | ✅ | .env excluded from git |
| Dependency vulnerability scanning | ❌ | No dependabot / safety check |

### 5.9 Tests

| Category | Count | Status |
|----------|-------|--------|
| Phase 5: Approval workflow | 11 | ✅ All passing |
| Phase 5: Export | 11 | ✅ All passing |
| Phase 5: SSE stream | 8 | ✅ All passing |
| Phase 5: SSE fanout | 7 | ✅ All passing |
| Phase 4: Sources / Evidence | Mixed | ⚠️ 25 pre-existing failures (deleted Watsonx project, missing pypdf) |
| Phase 1–3 integration | Multiple | ✅ Passing |
| **Total test functions** | ~288 | 349 passing, 25 pre-existing env failures |
| CI/CD pipeline | ❌ | No GitHub Actions or other CI |
| Coverage measurement | ⚠️ | Not currently configured |
| Performance/load tests | ❌ | None |
| Security tests | ❌ | None |

### 5.10 Deployment

| Feature | Status | Notes |
|---------|--------|-------|
| Dockerfile (backend) | ❌ | Not present |
| Dockerfile (frontend) | ❌ | Not present |
| docker-compose.yml | ❌ | Not present |
| .dockerignore | ❌ | Not present |
| .env.example (backend) | ✅ | Comprehensive |
| .env.local.example (frontend) | ✅ | Present |
| README (Windows native setup) | ✅ | PowerShell instructions |
| README (production deployment) | ❌ | Only dev mode (--reload) documented |
| Health check endpoint | ✅ | GET /health |
| Graceful shutdown | ⚠️ | ASGI lifespan handles some cleanup |

---

## 6. Gap Summary by Phase 6 Milestone

### M6.2 — Authentication and Authorization
**Current State**: No authentication. Local single-user tool. All endpoints public.

**Gaps**:
- No user model, no password hashing, no token management
- All projects/runs visible to any HTTP client on the network
- No ownership model on projects or runs
- No RBAC
- Frontend has no login page, no protected routes, no auth state

**Decision Required**: Whether to implement full multi-user auth OR a lightweight single-user API key / local password gate appropriate for a local-first tool. See document 53 for decision rationale.

### M6.3 — Database Optimization
**Current State**: SQLite with basic configuration. Migrations in place. Auto-upgrade on startup.

**Gaps**:
- WAL mode not enabled (can cause write contention)
- SQLite `PRAGMA foreign_keys = ON` not enforced at runtime
- `busy_timeout` not configured (concurrent access may throw immediately)
- FK columns not all indexed (e.g., run_id on most tables — may cause slow join/delete)
- No database backup procedure
- No data retention or cleanup for old export files
- PostgreSQL migration path not documented

**Low-risk items** (additive):
- WAL mode via PRAGMA in connection event listener
- foreign_keys enforcement via PRAGMA
- Missing FK indexes via Alembic migration

**Higher-risk items** (require care):
- Changing migration startup behavior
- Any data retention that could delete user data

### M6.4 — Error Handling and Retry
**Current State**: Route-level try/except everywhere. safe_error_message() in executor. FallbackLLMProvider for rate limits. No global handler.

**Gaps**:
- No global FastAPI exception handler → unhandled exceptions leak default 500 without log correlation
- No structured retry policy (exponential backoff + jitter)
- No circuit breaker for external APIs
- No idempotency enforcement on approval decisions
- No retry on database transient failures
- No standardized error response envelope (FastAPI default only)
- No request correlation ID propagated through the stack

### M6.5 — AI Evaluation and Benchmarking
**Current State**: No evaluation framework exists. `test_evaluation_metrics.py` has 2 placeholder API tests.

**Gaps**:
- No benchmark dataset
- No retrieval quality measurement
- No evidence extraction accuracy measurement
- No claim verification accuracy measurement
- No citation quality measurement
- No latency benchmarks
- No regression test suite for research quality

### M6.6 — Security and Prompt Injection
**Current State**: SSRF protection in place. CORS whitelist. File upload limits. Weak prompt injection mitigation.

**Gaps**:
- Prompt injection relies solely on "Ignore instructions" in system prompts
- No content sanitization before injecting into LLM context
- No per-agent tool permission enforcement in code (design exists, not enforced)
- No filename sanitization for uploaded documents
- No dependency vulnerability scanning
- DNS rebinding risk exists (TOCTOU between SSRF check and fetch, low risk in practice)

### M6.7 — Docker Deployment
**Current State**: No Docker files exist. README covers native Windows and macOS/Linux dev setup.

**Gaps**:
- No Dockerfile for backend
- No Dockerfile for frontend
- No docker-compose.yml
- No .dockerignore
- No production uvicorn configuration
- No documented production deployment procedure
- No multi-stage Docker builds
- No health check in Docker config
- No volume mounts for persistent data
- Tesseract not documented as dependency (not in requirements.txt)

### M6.8 — Monitoring and Logging
**Current State**: Structured JSON logging available. Health endpoint exists. LangSmith optional.

**Gaps**:
- No request trace ID in logs
- No request/response logging middleware (duration, status code)
- Health endpoint returns 200 even when DB status is "error"
- No Prometheus metrics endpoint
- No operational dashboard
- Sensitive data redaction not formally implemented (accidental logging of research content possible)

---

## 7. Risk Register

| ID | Risk | Severity | Likelihood | Mitigation |
|----|------|----------|------------|------------|
| R1 | Prompt injection via research_question | MEDIUM | LOW | Sanitize input, use prompt templates |
| R2 | Indirect prompt injection via web content | MEDIUM | MEDIUM | Content delimiters, input validation |
| R3 | File path traversal on document storage | MEDIUM | LOW | Sanitize filenames, use UUID paths |
| R4 | SQLite write contention on concurrent runs | MEDIUM | MEDIUM | Enable WAL mode, busy_timeout |
| R5 | Unhandled exception exposes internal detail | LOW | MEDIUM | Global exception handler |
| R6 | Export disk exhaustion | LOW | LOW | Retention policy, size monitoring |
| R7 | Deleted Watsonx cloud project breaks tests | LOW | DONE | Pre-existing, documented |
| R8 | Dependency with known vulnerability | MEDIUM | UNKNOWN | Add safety / pip-audit to CI |
| R9 | Missing authentication on shared network | HIGH | LOW | Local-first by design; document network isolation requirement |
| R10 | LLM rate limit cascades to run failure | MEDIUM | MEDIUM | Retry with backoff already partially addressed |

---

## 8. Positive Findings

The following production-readiness features are already well-implemented and require no Phase 6 work:

- **SSRF protection**: Comprehensive IP blocklist with DNS resolution before check
- **CORS whitelist**: Configured and enforced, localhost-only default
- **Cascade deletes**: All relationships correctly use cascade delete-orphan
- **SQL injection prevention**: SQLAlchemy ORM used throughout
- **File upload limits**: Size and count limits in place
- **safe_error_message()**: Prevents internal path leakage in persisted errors
- **Alembic migration history**: 13 clean migrations with downgrade paths
- **LLM fallback chain**: Rate-limit fallback with configurable provider list
- **LangGraph checkpointing**: Workflow recovery across restarts
- **Structured JSON logging**: Available and switchable via env
- **SSE infrastructure**: Complete fan-out, replay, heartbeat (Phase 5)
- **Human approval workflow**: Complete (Phase 5)
- **Report export**: PDF/DOCX/Markdown (Phase 5)
- **gitignore coverage**: Comprehensive, .env and *.db excluded

---

## 9. Pre-Existing Test Failures (Not Phase 6 Regressions)

| Category | Count | Cause |
|----------|-------|-------|
| Watsonx credential failures | ~15 | Deleted IBM Cloud project |
| pypdf/python-docx not installed | 2 | Missing from active venv |
| langgraph checkpoint compat | 3 | Version mismatch |
| **Total pre-existing failures** | ~25 | Environment only, not code regressions |
| **Passing tests** | 349 | All Phase 5 + earlier tests |

---

## 10. Architecture Diagram (Current State)

```
┌─────────────────────────────────────────────────────────────────┐
│  Developer Browser (localhost:3000)                             │
│  Next.js 14 · TypeScript · Tailwind · shadcn/ui                │
│                                                                  │
│  Pages: Dashboard / Projects / Workspace                        │
│  Components: ResearchPanel, SourcePanel, EvidenceExplorer,     │
│              ApprovalBanner, ExportPanel, LiveBadge             │
│  API Client: apiFetch (no auth headers)                        │
│  SSE Client: useSSE hook (fetch-based, Last-Event-ID)          │
└──────────────────────┬──────────────────────────────────────────┘
                       │  HTTP / SSE (localhost:8000)
┌──────────────────────▼──────────────────────────────────────────┐
│  FastAPI 0.111 · Python 3.14 · uvicorn                         │
│                                                                  │
│  Middleware: CORSMiddleware only                                │
│  Routes: projects / runs / documents / sources / evidence /    │
│          claims / reviews / citations / sse / approvals /      │
│          exports / health                                        │
│                                                                  │
│  Services: 24 service modules (approval, export, SSE, etc.)    │
│  Graph: LangGraph StateGraph                                    │
│    └─ Nodes: initialize / supervisor / planner / researcher /  │
│              critic / claim_extractor / citation_validator /    │
│              finalize_report / fail_workflow                     │
│    └─ Checkpointer: AsyncSqliteSaver                           │
│  Providers: OpenAI / Watsonx / Groq / Gemini + Fallback chain  │
│  SSRF guard: IP blocklist in web_fetcher.py                    │
└──────────────────────┬──────────────────────────────────────────┘
                       │  aiosqlite
┌──────────────────────▼──────────────────────────────────────────┐
│  SQLite (maar_dev.db + maar_checkpoints.db)                     │
│  13 Alembic migrations · CASCADE deletes · Status indexes       │
│  No WAL mode · No FK PRAGMA · No connection pool config         │
└─────────────────────────────────────────────────────────────────┘
                       │  filesystem
┌──────────────────────▼──────────────────────────────────────────┐
│  Local Filesystem                                               │
│  uploads/ (20 MB max per file, 10 files per request)           │
│  exports/ (PDF, DOCX, MD — no size/retention limits)           │
└─────────────────────────────────────────────────────────────────┘
```
