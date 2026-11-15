# MAAR Environment Variable Reference

This document provides a comprehensive reference for all configuration options and environment variables used across the Multi-Agent Autonomous Researcher (MAAR) backend and frontend services.

---

## Quick Navigation

- [Backend Configuration (`backend/.env`)](#backend-configuration-backendenv)
  - [Core Application](#core-application)
  - [Storage & Uploads](#storage--uploads)
  - [Primary LLM Configuration](#primary-llm-configuration)
  - [Provider-Specific Credentials](#provider-specific-credentials)
  - [LLM Resilience & Fallbacks](#llm-resilience--fallbacks)
  - [Web Search & External Ingestion](#web-search--external-ingestion)
  - [Multi-Agent & Workflow](#multi-agent--workflow)
  - [Database Reliability (Phase 6)](#database-reliability-phase-6)
  - [Network Retries (Phase 6)](#network-retries-phase-6)
  - [Authentication & Access Control (Phase 6)](#authentication--access-control-phase-6)
- [Frontend Configuration (`frontend/.env.local`)](#frontend-configuration-frontendenvlocal)
- [Docker Environment Mapping](#docker-environment-mapping)
- [Security Recommendations](#security-recommendations)

---

## Backend Configuration (`backend/.env`)

All backend variables are loaded via Pydantic `BaseSettings` (`app/core/config.py`). Values can be provided in `backend/.env` or passed via system environment variables.

### Core Application

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `DATABASE_URL` | String | `sqlite+aiosqlite:///./maar_dev.db` | No | SQLAlchemy async connection URI. Supports SQLite via `aiosqlite`. In Docker, use `sqlite+aiosqlite:////app/data/maar.db`. |
| `ALLOWED_ORIGINS` | String | `http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000` | No | Comma-delimited list of origins permitted by CORS middleware. |
| `APP_ENV` | String | `development` | No | Current runtime environment (`development`, `production`, `test`). |
| `APP_VERSION` | String | `0.1.0` | No | Application version reported in healthcheck payloads. |
| `LOG_FORMAT` | String | `text` | No | Logging format: `text` for readable console logs, or `json` for structured JSON logs. |

---

### Storage & Uploads

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `UPLOAD_DIR` | String | `./uploads` | No | Directory where uploaded source documents are securely stored using UUID paths. In Docker: `/app/uploads`. |
| `EXPORT_DIR` | String | `./exports` | No | Directory where exported reports (PDF, DOCX, Markdown) are persisted. In Docker: `/app/exports`. |
| `MAX_UPLOAD_SIZE_MB` | Integer | `20` | No | Maximum permitted file upload size in megabytes. |

---

### Primary LLM Configuration

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `LLM_PROVIDER` | String | `openai` | Yes | Target LLM provider: `openai`, `watsonx`, `groq`, `gemini`, or `openrouter`. |
| `LLM_API_KEY` | String | `""` | Yes | API authentication key for the selected primary provider (e.g., OpenAI or IBM Cloud API key). |
| `LLM_MODEL` | String | `gpt-4o-mini` | No | Model identifier for the primary provider (e.g., `gpt-4o-mini`, `meta-llama/llama-3-3-70b-instruct`). |
| `LLM_TIMEOUT_SECONDS` | Integer | `120` | No | Timeout in seconds for LLM inference requests before raising an exception. |
| `LLM_CONTEXT_BUDGET_CHARS` | Integer | `60000` | No | Maximum character budget allocated for source contexts fed into synthesis prompts. |

---

### Provider-Specific Credentials

#### IBM watsonx.ai
| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `WATSONX_URL` | String | `""` | If `watsonx` | URL of the watsonx instance (e.g., `https://us-south.ml.cloud.ibm.com`). |
| `WATSONX_PROJECT_ID` | String | `""` | If `watsonx` | Target IBM watsonx project GUID. |

#### OpenAI
| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `OPENAI_API_KEY` | String | `""` | Optional | Used for OpenAI fallback or if `LLM_API_KEY` is not set. |
| `OPENAI_FALLBACK_MODEL` | String | `gpt-4o-mini` | No | Model used when falling back to OpenAI. |

#### Groq
| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `GROQ_API_KEY` | String | `""` | If using Groq | Authentication key for Groq Cloud. |
| `GROQ_MODEL` | String | `llama-3.3-70b-versatile` | No | Model identifier for Groq. |

#### Google Gemini
| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `GEMINI_API_KEY` | String | `""` | If using Gemini | Google AI Studio API key. |
| `GEMINI_MODEL` | String | `gemini-3.8-flash` | No | Gemini model name. |

#### OpenRouter
| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `OPENROUTER_API_KEY` | String | `""` | If OpenRouter | API key for OpenRouter routing. |
| `OPENROUTER_MODEL` | String | `meta-llama/llama-3.1-8b-instruct` | No | Model identifier on OpenRouter. |

---

### LLM Resilience & Fallbacks

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `FALLBACK_LLM_PROVIDERS` | String | `""` | No | Comma-delimited list of fallback providers to invoke on HTTP 429 rate limit (e.g., `groq,openai`). |

---

### Web Search & External Ingestion

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `SEARCH_PROVIDER` | String | `tavily` | Yes | Search backend (`tavily`). |
| `SEARCH_API_KEY` | String | `""` | Yes | API authentication key for Tavily search. |
| `SEARCH_MAX_RESULTS` | Integer | `8` | No | Maximum number of search results to retrieve per query iteration. |
| `WEB_FETCH_TIMEOUT_SECONDS` | Integer | `15` | No | Timeout for fetching target web page content. |
| `WEB_FETCH_MAX_CONTENT_KB` | Integer | `200` | No | Maximum bytes of scraped web text retained for processing. |
| `ARXIV_ENABLED` | Boolean | `false` | No | Enable arXiv academic paper search ingestion. |
| `SEMANTIC_SCHOLAR_API_KEY` | String | `""` | No | Optional API key to increase rate limits for Semantic Scholar paper queries. |

---

### Multi-Agent & Workflow

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `MAX_SUPERVISOR_CYCLES` | Integer | `3` | No | Maximum iterations the Supervisor agent may route between Planner and Researcher. |
| `CHECKPOINT_DB_URL` | String | `./maar_checkpoints.db` | No | SQLite path for LangGraph thread checkpoints. In Docker: `/app/data/maar_checkpoints.db`. |
| `VERIFICATION_DEPTH` | String | `basic` | No | Claim verification mode: `basic` (key findings only) or `thorough` (all report sections). |
| `MAX_CLAIMS_PER_RUN` | Integer | `20` | No | Hard cap on atomic claims extracted and verified per research run. |
| `CRITIC_MAX_REVIEW_CYCLES` | Integer | `2` | No | Maximum number of revision cycles permitted for the Critic agent before final output. |
| `ENABLE_LLM_USAGE_TRACKING` | Boolean | `true` | No | Tracks prompt/completion token usage and estimation metrics per run. |
| `LLM_COST_PER_1K_TOKENS` | Float | `0.0` | No | Multiplier for estimating dollar cost per 1,000 processed tokens. |

---

### Database Reliability (Phase 6)

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `DB_WAL_MODE` | Boolean | `true` | No | Enables SQLite Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) for high concurrency. |
| `DB_BUSY_TIMEOUT_MS` | Integer | `5000` | No | SQLite busy handler wait time in milliseconds (`PRAGMA busy_timeout=5000;`). |

---

### Network Retries (Phase 6)

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `RETRY_MAX_ATTEMPTS` | Integer | `3` | No | Maximum attempts for retryable transient errors (HTTP 429, 502, 503, 504, connect timeouts). |
| `RETRY_BASE_DELAY_S` | Float | `1.0` | No | Initial exponential backoff delay in seconds with random jitter. |

---

### Authentication & Access Control (Phase 6)

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `AUTH_SECRET_KEY` | String | `""` | Production | Secret key used for signing session identifiers and token integrity. |
| `SESSION_TTL_HOURS` | Integer | `8` | No | Lifetime of valid login session cookies in hours. |
| `AUTO_LOGIN_DEV` | Boolean | `false` | No | Set to `true` in local development to bypass session cookie validation. |
| `ADMIN_USERNAME` | String | `admin` | No | Username for the primary administrative user seeded at startup. |
| `ADMIN_PASSWORD_HASH` | String | `""` | Production | Bcrypt password hash for the admin account. |
| `AUTH_MAX_ATTEMPTS` | Integer | `5` | No | Maximum consecutive failed logins before triggering IP/account lockout. |
| `AUTH_LOCKOUT_MINUTES` | Integer | `15` | No | Duration of brute-force lockout window in minutes. |

---

## Generating Passwords and Secrets

### Generate Bcrypt Password Hash
Run the following in your Python environment:
```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'YourSecurePasswordHere', bcrypt.gensalt()).decode())"
```
Place the output in `ADMIN_PASSWORD_HASH` in `.env`.

### Generate Auth Secret Key
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
Place the output in `AUTH_SECRET_KEY` in `.env`.

---

## Frontend Configuration (`frontend/.env.local`)

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `API_URL` | String | `http://localhost:8000` | No | Internal backend URL used by Next.js Server Components and server-side actions. In Docker: `http://backend:8000`. |
| `NEXT_PUBLIC_API_URL` | String | `http://localhost:8000` | No | Public backend base URL used by browser client components. |
| `NODE_ENV` | String | `development` | No | Environment runtime (`development` or `production`). |

---

## Docker Environment Mapping

When running with `docker compose up`, backend configuration is loaded from `backend/.env`. Container paths should be adjusted as follows:

| Environment Variable | Local Development Value | Docker Compose Value |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./maar_dev.db` | `sqlite+aiosqlite:////app/data/maar.db` |
| `CHECKPOINT_DB_URL` | `./maar_checkpoints.db` | `/app/data/maar_checkpoints.db` |
| `UPLOAD_DIR` | `./uploads` | `/app/uploads` |
| `EXPORT_DIR` | `./exports` | `/app/exports` |
| `API_URL` (Frontend) | `http://localhost:8000` | `http://backend:8000` |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | `http://localhost:8000` |

---

## Security Recommendations

1. **Never commit `.env` or `.env.local`**: Ensure these files are listed in `.gitignore`.
2. **Production Secrets**: In production environments, never leave `ADMIN_PASSWORD_HASH` empty or `AUTO_LOGIN_DEV=true`.
3. **Restricted CORS**: Always limit `ALLOWED_ORIGINS` to trusted hostnames in production.
4. **Volume Permissions**: When using Docker, maintain permissions on named volumes (`maar-db`, `maar-uploads`, `maar-exports`) so that non-root user `maar` (UID 1001) can read and write.
