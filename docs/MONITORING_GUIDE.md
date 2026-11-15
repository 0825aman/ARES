# MAAR Monitoring, Logging & Observability Guide

This guide describes operational monitoring, structured logging, sensitive data redaction, health checks, and in-process metrics in MAAR.

---

## 1. Health & Liveness Endpoints

MAAR exposes three operational health probes:

| Endpoint | Purpose | Success Code | Failure Code | Behavior |
|----------|---------|--------------|--------------|----------|
| `GET /health/live` | Liveness probe | 200 | N/A | Process is alive and accepting connections |
| `GET /health/ready` | Readiness probe | 200 | 503 | Verifies SQLite database is reachable and readable |
| `GET /health` | Backward-compatible status | 200 | 503 | Returns detailed component status JSON |

---

## 2. In-Process Metrics Endpoint

MAAR exposes thread-safe operational metrics at `GET /metrics` without requiring external APM or paid subscriptions:

```json
{
  "started_at": "2026-11-14T15:00:00.000000+00:00",
  "counters": {
    "runs_started": 12,
    "runs_completed": 10,
    "runs_failed": 2
  },
  "llm_calls_total": {
    "provider=openai": 25,
    "provider=watsonx": 8
  },
  "exports_total": {
    "format=pdf": 6,
    "format=docx": 4,
    "format=markdown": 8
  },
  "http_requests_total": {
    "method=GET,status=200": 150,
    "method=POST,status=201": 12
  }
}
```

---

## 3. Structured Logging & Sensitive Data Redaction

### Formats
Logging is configured via `LOG_FORMAT` in `backend/.env`:
- `LOG_FORMAT=text` (default): Human-readable formatted logs.
- `LOG_FORMAT=json`: Machine-readable single-line JSON with timestamps, logger name, log level, and request correlation IDs.

### Correlation ID
Every HTTP request generates or echoes an `X-Request-ID` UUID4 header. The Request ID is injected into request state, attached to all log records in that request context, and returned in the HTTP response headers.

### Sensitive Data Redaction
The `SensitiveDataFilter` automatically scans all log messages and redacts:
- Common API key patterns (`sk-...`, `tvly-...`)
- Credentials following keywords: `api_key`, `access_token`, `secret_key`, `password`, `bearer`, `authorization`
- Replaces matches with `[REDACTED]`.

---

## 4. Optional LangSmith Tracing

MAAR natively supports optional LangSmith tracing for LangGraph agent debugging. To enable:
```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=maar-research
```
If these variables are omitted, MAAR functions without error or performance penalty.
