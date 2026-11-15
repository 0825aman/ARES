# 52 — Phase 6 Implementation Roadmap

## MAAR — Multi-Agent Autonomous Researcher
## Phase 6: Production Readiness

---

## 1. Scope Summary

Phase 6 transforms MAAR from a functional local research application into a reliable, secure, maintainable and reproducibly deployable engineering product.

The scope covers eight milestones:

| Milestone | Title | Description |
|-----------|-------|-------------|
| M6.1 | Audit and Architecture | Repository audit + this document |
| M6.2 | Authentication and Authorization | Local single-user auth gate |
| M6.3 | Database Optimization | SQLite hardening, indexes, backup |
| M6.4 | Error Handling and Retry | Global handlers, retry policy, correlation IDs |
| M6.5 | AI Evaluation | Benchmark dataset, evaluation metrics |
| M6.6 | Security and Prompt Injection | Input validation, content delimiters, dep scanning |
| M6.7 | Docker Deployment | Dockerfiles, Compose, production setup |
| M6.8 | Monitoring and Logging | Structured logs, health checks, metrics |
| M6.9 | Acceptance Testing | End-to-end validation and documentation |

---

## 2. Milestone Dependency Map

```
M6.1 (Audit)
  └─► M6.2 (Auth)       ─────────────────────► M6.9 (Acceptance)
  └─► M6.3 (Database)   ──────────────────────► M6.9
  └─► M6.4 (Errors)     ──────────────────────► M6.9
  └─► M6.5 (Evaluation) ──────────────────────► M6.9
  └─► M6.6 (Security)   ──────────────────────► M6.9
  └─► M6.7 (Docker)     ──── depends on M6.2 ──► M6.9
  └─► M6.8 (Monitoring) ──── depends on M6.4 ──► M6.9
```

M6.7 (Docker) must be implemented after M6.2 (Auth) because the Docker images need to include any authentication configuration. M6.8 (Monitoring) benefits from M6.4's request correlation IDs. All other milestones are independent.

---

## 3. Recommended Execution Order

1. M6.1 — CURRENT (complete)
2. M6.3 — Database Optimization (additive, lowest risk, enables reliable testing for all subsequent milestones)
3. M6.4 — Error Handling and Retry (improves reliability before adding auth complexity)
4. M6.2 — Authentication and Authorization (builds on stable foundation)
5. M6.6 — Security (builds on auth, hardens existing functionality)
6. M6.8 — Monitoring and Logging (benefits from request IDs added in M6.4)
7. M6.5 — AI Evaluation (self-contained, can run in parallel with M6.7)
8. M6.7 — Docker Deployment (packages everything after all code changes are stable)
9. M6.9 — Acceptance Testing (final validation of all milestones)

---

## 4. Milestone Detail

---

### M6.1 — Production Readiness Audit and Architecture

**Status**: ✅ Complete

**Deliverables**:
- `docs/51_PHASE_6_PRODUCTION_READINESS_AUDIT.md` — Comprehensive audit
- `docs/52_PHASE_6_IMPLEMENTATION_ROADMAP.md` — This document
- `docs/53_PHASE_6_ARCHITECTURAL_DECISIONS.md` — ADRs for key decisions

---

### M6.2 — Authentication and Authorization

**Intent**: Add a secure authentication gate appropriate for a local-first single-user research tool.

**Design Decision** (see ADR-001 in document 53):

MAAR is a **local-first single-user tool**. Full multi-user JWT authentication with RBAC would be significant over-engineering. The correct approach is a **lightweight local password gate**:

- Single admin user configured via environment variable (hashed password stored in DB)
- HTTP-only cookie session (no JWT, avoids token storage risks)
- Session expiry (configurable TTL)
- Login page in frontend
- Protected routes — all API endpoints require a valid session
- One RBAC role (admin) for the initial user; Viewer role for a potential read-only second user
- Brute-force protection via login attempt rate limiting

**New files**:
```
backend/app/models/user.py                     — User model (id, username, hashed_password, role, created_at)
backend/app/core/security.py                   — Password hashing (bcrypt), session token generation
backend/app/api/v1/routes/auth.py              — POST /auth/login, POST /auth/logout, GET /auth/me
backend/app/services/auth_service.py           — User lookup, password verify, session management
backend/alembic/versions/k_phase6_auth.py      — Migration: users + sessions tables
frontend/src/app/login/page.tsx                — Login page
frontend/src/middleware.ts                     — Next.js middleware for route protection
frontend/src/lib/api/auth.ts                   — Auth API calls (login, logout, me)
frontend/src/lib/hooks/useAuth.ts              — Auth state hook
frontend/src/components/auth/LoginForm.tsx     — Login form component
backend/tests/test_auth.py                     — Auth endpoint tests
```

**Modified files**:
```
backend/app/main.py                            — Add session middleware
backend/app/core/config.py                     — Add AUTH_SECRET_KEY, SESSION_TTL_HOURS, ADMIN_USERNAME, ADMIN_PASSWORD_HASH
backend/app/models/run.py                      — Add owner_id FK (optional, if multi-user later)
backend/app/api/v1/router.py                   — Register auth router
frontend/src/app/layout.tsx                    — AuthProvider context
frontend/src/lib/api/client.ts                 — Add credentials: 'include' for cookie sessions
```

**New dependencies**:
```
backend: bcrypt>=4.0.0, itsdangerous>=2.1.0 (for session signing)
```

**Acceptance criteria**:
- Login form authenticates user and sets HTTP-only session cookie
- All API endpoints return 401 without valid session
- Logout clears session
- Invalid passwords rejected
- Brute-force protection: 5 failed attempts → 15-minute lockout
- Session expiry works
- Existing single-user local dev experience preserved (auto-login option for dev mode)
- Auth tests pass

---

### M6.3 — Database Optimization and Migration Readiness

**Intent**: Harden the SQLite configuration, add missing indexes, implement backup procedures, and document the PostgreSQL migration path.

**Design Decision** (see ADR-002 in document 53):

SQLite remains the default. No PostgreSQL migration in Phase 6. The goal is to make SQLite as reliable as possible for local concurrent use and document what would need to change for a PostgreSQL migration.

**New files**:
```
backend/alembic/versions/l_phase6_db_indexes.py  — Add FK indexes + composite indexes
backend/app/core/database.py                      — Add PRAGMA event listener (WAL, FK, busy_timeout)
backend/scripts/backup_db.py                      — Database backup script (SQLite .backup API)
backend/scripts/restore_db.py                     — Database restore script
docs/DATABASE_BACKUP_GUIDE.md                     — Backup/restore documentation
backend/tests/test_database_config.py             — Tests for PRAGMA configuration
```

**Modified files**:
```
backend/app/core/database.py        — Add SQLite PRAGMA configuration
backend/app/core/config.py          — Add DB_BUSY_TIMEOUT_MS, DB_WAL_MODE settings
```

**Changes**:
1. **WAL mode**: `PRAGMA journal_mode=WAL` — allows concurrent reads during write
2. **Foreign keys**: `PRAGMA foreign_keys=ON` — enforces FK constraints at runtime
3. **Busy timeout**: `PRAGMA busy_timeout=5000` — wait up to 5s before giving up on locked DB
4. **Missing indexes**: 
   - `idx_runs_project_id_status` — project_id + status (dashboard query)
   - `idx_events_run_id_created_at` — event log ordering
   - `idx_sources_run_id` — source listing
   - `idx_evidence_run_id` — evidence listing
   - `idx_claims_run_id` — claim listing
   - `idx_citations_run_id_report_id` — citation/bibliography query
   - `idx_export_records_run_id_created_at` — export listing
5. **Backup**: SQLite `.backup()` API (safe hot backup, consistent point-in-time)
6. **Pagination**: Review and document existing pagination in routes

**Acceptance criteria**:
- WAL mode confirmed via PRAGMA query
- FK constraints enforced (test: insert with invalid FK fails)
- Busy timeout prevents immediate failure on contention
- New indexes confirmed via EXPLAIN QUERY PLAN
- Backup script creates consistent backup file
- Restore script restores from backup
- All existing tests still pass
- No data loss

---

### M6.4 — Centralized Error Handling and Retry

**Intent**: Add a global exception handler, structured retry with backoff, request correlation IDs, and standardized error response format.

**New files**:
```
backend/app/core/middleware.py          — RequestIDMiddleware, RequestLoggingMiddleware
backend/app/core/retry.py               — Retry decorator with exponential backoff + jitter
backend/app/core/exceptions.py         — Custom exception hierarchy
backend/tests/test_retry.py             — Retry policy tests
backend/tests/test_middleware.py        — Middleware tests
```

**Modified files**:
```
backend/app/main.py                     — Global exception handler, add middleware
backend/app/core/config.py              — Add RETRY_MAX_ATTEMPTS, RETRY_BASE_DELAY_S settings
backend/app/providers/llm.py            — Apply retry decorator to LLM calls
backend/app/providers/web_search.py     — Apply retry decorator to search calls
backend/app/services/approval_service.py — Idempotency check on create_approval
frontend/src/lib/api/client.ts          — Add X-Request-ID header, retry on 5xx
```

**Changes**:
1. **Global exception handler**: `@app.exception_handler(Exception)` → logs with trace ID, returns standard error
2. **Standard error envelope**: `{"error": {"code": "...", "message": "...", "request_id": "..."}}` 
3. **Request ID middleware**: Generates UUID per request, adds X-Request-ID header to response
4. **Request logging middleware**: Logs method, path, status code, duration at INFO level
5. **Retry decorator** (backend):
   - Configurable max_attempts, base_delay, max_delay
   - Exponential backoff: delay = min(base_delay * 2^attempt + jitter, max_delay)
   - Jitter: random(0, 0.1 * delay)
   - Retryable: HTTP 429, 500, 502, 503, 504, ConnectionError, Timeout
   - Non-retryable: HTTP 400, 401, 403, 404, 422; ValueError, TypeError
6. **Frontend retry**: Retry on 5xx responses (max 2 retries, 1s delay)
7. **Approval idempotency**: Check for existing pending approval before creating new

**Acceptance criteria**:
- Unhandled exceptions return structured JSON with request_id
- Request ID logged in all subsequent operations
- Retry fires on transient failures, skips permanent ones
- Retry tests pass with mock failures
- Request duration logged
- Existing tests still pass

---

### M6.5 — AI Evaluation and Benchmarking Framework

**Intent**: Build a reproducible evaluation framework with a benchmark dataset and metrics for research quality measurement.

**Design Decision** (see ADR-003 in document 53):

The evaluation framework is code and data in the repository — no external paid evaluation platform required. LLM-as-a-judge is used for semantic similarity only, not as ground truth.

**New files**:
```
maar/eval/                                     — Evaluation framework root
maar/eval/README.md                            — Evaluation guide
maar/eval/dataset/                             — Benchmark dataset
maar/eval/dataset/questions.json               — 20 research questions across 6 categories
maar/eval/dataset/expected/                    — Expected evaluation references per question
maar/eval/metrics/                             — Metric implementations
maar/eval/metrics/retrieval.py                 — Precision@K, Recall@K, duplicate rate
maar/eval/metrics/evidence.py                  — Extraction accuracy, completeness
maar/eval/metrics/claims.py                    — Verification accuracy, contradiction detection
maar/eval/metrics/citations.py                 — Citation correctness, broken URL rate
maar/eval/metrics/workflow.py                  — Task completion rate, latency, cost
maar/eval/runner.py                            — Benchmark runner CLI
maar/eval/reporter.py                          — JSON + Markdown report generator
maar/eval/conftest.py                          — Shared fixtures for eval tests
backend/tests/test_evaluation_metrics.py       — Unit tests for metric calculations
docs/EVALUATION_GUIDE.md                       — How to run benchmarks
```

**Dataset structure** (`questions.json`):
```json
{
  "version": "1.0",
  "questions": [
    {
      "id": "q001",
      "category": "science",
      "question": "What are the main causes of antibiotic resistance?",
      "difficulty": "medium",
      "expected_sources": ["pubmed.ncbi.nlm.nih.gov", "who.int"],
      "expected_claims": ["Overuse of antibiotics in agriculture contributes to resistance"],
      "expected_contradictions": [],
      "notes": "Well-established scientific consensus"
    }
  ]
}
```

**Metric categories**:

| Metric | Method | Ground Truth |
|--------|--------|-------------|
| Source relevance | URL domain match + LLM semantic judge | Expected source domains |
| Evidence completeness | LLM semantic coverage | Expected claim coverage |
| Claim verification accuracy | Label match | Manually labeled examples |
| Citation correctness | URL reachability + DOI validation | Expected sources |
| Task completion rate | DB query | run.status = completed |
| Run latency (p50, p95) | timestamps | None required |
| LLM cost | llm_call_count * cost_per_1k | None required |

**Acceptance criteria**:
- Dataset contains ≥10 questions across ≥4 categories
- Metrics produce numerical outputs (not just pass/fail)
- Runner produces structured JSON report
- Metric unit tests pass (do not require live LLM calls)
- Evaluation does not depend on paid monitoring platform
- Cost and latency measured per run

---

### M6.6 — Security and Prompt Injection Protection

**Intent**: Harden the system against prompt injection, strengthen file upload security, add dependency vulnerability scanning, and enforce per-agent tool permissions.

**New files**:
```
backend/app/core/content_sanitizer.py          — External content sanitization
backend/app/core/tool_permissions.py           — Per-agent tool permission registry
backend/tests/test_prompt_injection.py         — Prompt injection tests
backend/tests/test_file_security.py            — File upload security tests
backend/tests/test_ssrf.py                     — SSRF tests
.github/dependabot.yml                         — Dependency vulnerability scanning
docs/SECURITY.md                               — Security documentation
```

**Modified files**:
```
backend/app/providers/web_fetcher.py            — Strengthen SSRF, add redirect validation
backend/app/services/document_service.py        — Filename sanitization, magic byte check
backend/app/agents/planner.py                   — PromptTemplate, content delimiters
backend/app/agents/researcher.py                — PromptTemplate, content delimiters
backend/app/agents/supervisor.py                — PromptTemplate
backend/app/agents/critic.py                    — PromptTemplate
backend/requirements.txt                        — Add safety[optional] for dep scanning
```

**Changes**:

1. **Prompt templates**: Replace f-string prompt building with LangChain `ChatPromptTemplate`
   - System prompt in `SystemMessage`
   - User research question in `HumanMessage` with explicit delimiters
   - Extracted web/document content clearly delimited: `<external_content>...</external_content>`

2. **Content delimiters**: Wrap all external content (web pages, document text) before LLM injection:
   ```
   <external_content source="{url}">
   {extracted_text}
   </external_content>
   ```

3. **Input validation**: Validate `research_question`:
   - Max length: 1000 characters
   - No XML/HTML injection markers (`<`, `>`, `{`, `}` stripped or escaped)
   - No null bytes or control characters

4. **Filename sanitization**: For uploaded documents:
   - Strip directory separators (`/`, `\`, `..`)
   - UUID-based internal storage paths (never use original filename for storage)
   - Original filename stored in DB only (for display)

5. **Magic byte validation**: Verify PDF/DOCX file headers, not just extension

6. **Per-agent tool permissions**:
   ```python
   AGENT_TOOLS = {
       "planner": [],           # LLM only, no tools
       "researcher": ["web_search", "web_fetch", "document_search"],
       "supervisor": [],        # LLM only
       "critic": [],            # LLM only
   }
   ```

7. **Dependency scanning**: `pip-audit` or `safety` check in CI

8. **SSRF hardening**:
   - Validate redirects (don't follow to private IPs)
   - Block `file://`, `ftp://`, `javascript://` schemes explicitly

**Acceptance criteria**:
- Prompt injection test: Injected instruction in research_question does not change agent behavior
- Prompt injection test: Injected instruction in fetched web content does not change agent behavior
- File security test: Directory traversal in filename rejected
- File security test: File with wrong extension and wrong magic bytes rejected
- SSRF test: Private IP URL rejected
- SSRF test: DNS-resolving-to-private-IP rejected
- Dependency scan produces report (zero critical vulnerabilities or documented exceptions)
- All existing tests still pass

---

### M6.7 — Docker Deployment and Reproducible Setup

**Intent**: Enable any developer to run MAAR from a clean environment using Docker Compose with a single command.

**New files**:
```
maar/backend/Dockerfile                         — Multi-stage Python image
maar/frontend/Dockerfile                        — Multi-stage Node.js image
maar/docker-compose.yml                         — Full stack orchestration
maar/docker-compose.dev.yml                     — Development overrides (--reload, hot reload)
maar/.dockerignore                              — Exclude dev artifacts
maar/frontend/.dockerignore                     — Frontend-specific excludes
maar/backend/.dockerignore                      — Backend-specific excludes
docs/DOCKER_GUIDE.md                            — Docker setup and operations guide
docs/WINDOWS_SETUP_GUIDE.md                     — Native Windows setup guide
docs/PRODUCTION_CONFIG_REFERENCE.md             — All env vars documented
```

**Modified files**:
```
maar/README.md                                  — Add Docker quick-start, update setup
maar/frontend/.env.local.example               — Ensure Docker-compatible URL
maar/backend/.env.example                      — Add Docker-specific vars
```

**Dockerfile design**:

Backend (`maar/backend/Dockerfile`):
```
Stage 1 (builder): python:3.11-slim + build-essential
  - pip install requirements.txt
Stage 2 (runtime): python:3.11-slim
  - Copy installed packages from builder
  - Create non-root user (maar)
  - Copy app/
  - HEALTHCHECK: curl /health
  - CMD: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

Frontend (`maar/frontend/Dockerfile`):
```
Stage 1 (deps): node:18-alpine
  - npm ci
Stage 2 (builder): node:18-alpine
  - npm run build
Stage 3 (runtime): node:18-alpine
  - Copy .next/standalone + public/
  - Create non-root user
  - CMD: node server.js
```

Docker Compose (`maar/docker-compose.yml`):
```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes:
      - maar-uploads:/app/uploads
      - maar-exports:/app/exports
      - maar-db:/app/data
    environment:
      DATABASE_URL: sqlite+aiosqlite:////app/data/maar.db
    env_file: ./backend/.env
    healthcheck: ...
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
      API_URL: http://backend:8000
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped

volumes:
  maar-uploads:
  maar-exports:
  maar-db:
```

**Acceptance criteria**:
- `docker compose up --build` succeeds on clean environment
- Frontend accessible at http://localhost:3000
- Backend accessible at http://localhost:8000
- GET /health returns {"status": "ok"}
- Database persists across container restarts
- Uploaded documents persist across restarts
- Exported files persist across restarts
- Real API keys configured via .env — not baked into image
- Non-root user in both containers
- Native Windows setup documented and tested

---

### M6.8 — Monitoring, Logging, and Operational Reliability

**Intent**: Add structured request logging, improve health checks, add operational metrics, and ensure sensitive data is not logged.

**New files**:
```
backend/app/core/middleware.py          — (May already exist from M6.4; extend here)
backend/app/api/v1/routes/health.py    — Extended health check with ready/live distinction
backend/app/core/metrics.py            — Application metrics (counters, histograms)
docs/MONITORING_GUIDE.md               — Logging, metrics, and troubleshooting guide
```

**Modified files**:
```
backend/app/core/middleware.py          — Add request duration, request ID to all logs
backend/app/core/logging_config.py     — Add sensitive data filter, expand structured fields
backend/app/api/v1/routes/health.py    — Distinguish liveness from readiness; fix 200-on-error
backend/app/core/config.py             — Add LOG_SENSITIVE_PROMPTS=false setting
```

**Changes**:

1. **Health endpoint improvements**:
   - `GET /health/live` → 200 if app is running (liveness)
   - `GET /health/ready` → 200 only if DB is accessible (readiness)
   - Existing `GET /health` → unchanged for backward compat (returns both statuses)
   - Fix: Return HTTP 503 when DB is "error" (currently always returns 200)

2. **Request logging**:
   - Logs: method, path, status_code, duration_ms, request_id, user_id (if auth enabled)
   - Excludes: health check paths (configurable)
   - Redacts: Authorization header values, cookie values in logs

3. **Sensitive data filter**:
   - Log filter that redacts API keys if accidentally included
   - Pattern: `[a-zA-Z0-9_]{20,}` preceded by key/secret/token → replaced with `[REDACTED]`

4. **Operational metrics** (in-process, no external service required):
   - Research run start/complete/fail counters (increment on status change)
   - LLM call counter (per provider)
   - Export generation counter (per format)
   - Export failure counter
   - Request count (per route, per status code)
   - All stored in memory, exposed at `GET /metrics` as JSON

5. **LangSmith documentation**: Document how to enable, what data is transmitted, how to disable

**Acceptance criteria**:
- `GET /health/ready` returns 503 when DB is unavailable
- Request logs include duration_ms and request_id
- Sensitive patterns not present in log output
- `GET /metrics` returns operational counters
- LangSmith remains optional (app functions without LANGCHAIN_API_KEY)
- All existing tests still pass

---

### M6.9 — Production Acceptance Testing and Documentation

**Intent**: Final end-to-end validation of all Phase 6 milestones and documentation update.

**New files**:
```
docs/README.md                              — Documentation index
docs/INSTALLATION_GUIDE.md                 — Full installation guide
docs/DOCKER_GUIDE.md                       — Docker deployment (from M6.7)
docs/WINDOWS_SETUP_GUIDE.md               — Native Windows setup (from M6.7)
docs/AUTHENTICATION_GUIDE.md              — Auth configuration
docs/DATABASE_BACKUP_GUIDE.md             — Backup/restore (from M6.3)
docs/SECURITY.md                          — Security documentation (from M6.6)
docs/EVALUATION_GUIDE.md                  — Evaluation framework (from M6.5)
docs/MONITORING_GUIDE.md                  — Monitoring and troubleshooting (from M6.8)
docs/ENVIRONMENT_REFERENCE.md            — All environment variables
docs/PHASE_6_COMPLETION_REPORT.md        — Final Phase 6 report
backend/tests/test_e2e_workflow.py        — End-to-end workflow test
```

**Modified files**:
```
maar/README.md                             — Comprehensive updated README
```

**End-to-end test** (`test_e2e_workflow.py`):
- Creates project
- Starts research run (sequential mode, mock LLM)
- Verifies events are logged
- Verifies run completes
- Verifies report is generated
- Verifies export can be triggered (all three formats)
- Verifies run history is queryable
- Verifies project deletion cascades correctly

**Acceptance criteria** (all must pass):
- All M6.2–M6.8 acceptance criteria satisfied
- End-to-end test passes with mock LLM
- Docker Compose starts cleanly on simulated clean environment
- README covers: install, configure, run, backup, troubleshoot
- No Phase 1–5 functionality regressed
- Pre-existing test failures documented and explained

---

## 5. Files to Create (All Milestones)

### Backend New Files
```
app/models/user.py
app/core/security.py
app/core/middleware.py
app/core/retry.py
app/core/exceptions.py
app/core/content_sanitizer.py
app/core/tool_permissions.py
app/core/metrics.py
app/api/v1/routes/auth.py
app/services/auth_service.py
alembic/versions/k_phase6_auth.py
alembic/versions/l_phase6_db_indexes.py
scripts/backup_db.py
scripts/restore_db.py
tests/test_auth.py
tests/test_retry.py
tests/test_middleware.py
tests/test_database_config.py
tests/test_prompt_injection.py
tests/test_file_security.py
tests/test_ssrf.py
tests/test_e2e_workflow.py
Dockerfile
.dockerignore
```

### Frontend New Files
```
src/app/login/page.tsx
src/middleware.ts
src/lib/api/auth.ts
src/lib/hooks/useAuth.ts
src/components/auth/LoginForm.tsx
.dockerignore
Dockerfile
```

### Repository Root New Files
```
docker-compose.yml
docker-compose.dev.yml
.dockerignore
eval/README.md
eval/dataset/questions.json
eval/dataset/expected/
eval/metrics/retrieval.py
eval/metrics/evidence.py
eval/metrics/claims.py
eval/metrics/citations.py
eval/metrics/workflow.py
eval/runner.py
eval/reporter.py
docs/51_PHASE_6_PRODUCTION_READINESS_AUDIT.md
docs/52_PHASE_6_IMPLEMENTATION_ROADMAP.md
docs/53_PHASE_6_ARCHITECTURAL_DECISIONS.md
docs/INSTALLATION_GUIDE.md
docs/DOCKER_GUIDE.md
docs/WINDOWS_SETUP_GUIDE.md
docs/AUTHENTICATION_GUIDE.md
docs/DATABASE_BACKUP_GUIDE.md
docs/SECURITY.md
docs/EVALUATION_GUIDE.md
docs/MONITORING_GUIDE.md
docs/ENVIRONMENT_REFERENCE.md
docs/PHASE_6_COMPLETION_REPORT.md
```

---

## 6. Files to Modify (All Milestones)

```
backend/app/main.py                        — Auth middleware, global exception handler
backend/app/core/config.py                 — Auth settings, retry settings, monitoring settings
backend/app/core/database.py               — SQLite PRAGMAs
backend/app/core/logging_config.py         — Sensitive data filter, expanded fields
backend/app/api/v1/router.py               — Auth router registration
backend/app/api/v1/routes/health.py        — Liveness/readiness split, fix 503 on DB error
backend/app/providers/llm.py               — Retry decorator
backend/app/providers/web_fetcher.py       — Redirect SSRF validation, scheme blocklist
backend/app/providers/web_search.py        — Retry decorator
backend/app/agents/planner.py              — ChatPromptTemplate, content delimiters
backend/app/agents/researcher.py           — ChatPromptTemplate, content delimiters
backend/app/agents/supervisor.py           — ChatPromptTemplate
backend/app/agents/critic.py               — ChatPromptTemplate
backend/app/services/document_service.py   — Filename sanitization, magic byte check
backend/app/services/approval_service.py   — Idempotency check
backend/requirements.txt                   — bcrypt, itsdangerous, pip-audit
frontend/src/lib/api/client.ts             — credentials: include, X-Request-ID, retry
frontend/src/app/layout.tsx                — AuthProvider
maar/README.md                             — Updated documentation
```

---

## 7. New Dependencies

| Package | Purpose | Side | Milestone |
|---------|---------|------|-----------|
| bcrypt>=4.0.0 | Password hashing | Backend | M6.2 |
| itsdangerous>=2.1.0 | Session signing | Backend | M6.2 |
| starlette-session or custom | HTTP cookie sessions | Backend | M6.2 |
| pip-audit or safety | Dependency scanning | Backend dev | M6.6 |

No frontend authentication library required (vanilla cookie session handled by browser).

---

## 8. Database Changes

| Migration | Description | Type |
|-----------|------------|------|
| k_phase6_auth | users + sessions tables | Additive |
| l_phase6_db_indexes | FK indexes + composite indexes | Additive |
| (optional) m_phase6_owner_id | owner_id FK on research_projects | Additive |

All migrations are additive — no destructive schema changes.

---

## 9. Breaking Changes

There are **no planned breaking API changes** in Phase 6. All existing Phase 1–5 API endpoints remain unchanged.

Authentication (M6.2) will add a **login requirement** to all existing endpoints. If running in development mode with the `AUTO_LOGIN_DEV=true` env flag, this is bypassed to preserve the existing developer experience.

---

## 10. Phased Master Plan File

A `maar-phase6-plan.md` will be created at the repository root alongside the existing phase plan files. It will track sub-task completion status.
