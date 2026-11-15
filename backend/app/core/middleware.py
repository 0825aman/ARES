"""middleware.py — Request ID and Request Logging middleware for ARES.

Provides:
  - RequestIDMiddleware: assigns a UUID4 X-Request-ID to every request/response.
  - RequestLoggingMiddleware: logs method, path, status_code, duration_ms per request.

Both are Starlette BaseHTTPMiddleware implementations compatible with FastAPI.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.metrics import metrics

logger = logging.getLogger(__name__)

# Paths whose access logs are suppressed to reduce noise in operational environments.
# Health checks fire frequently and add little diagnostic value.
_SKIP_LOG_PREFIXES = ("/health",)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a correlation ID to every request and echo it in the response.

    Behaviour:
    - If the incoming request already carries an ``X-Request-ID`` header, that
      value is used (allows tracing across service hops).
    - Otherwise a fresh UUID4 is generated.
    - The ID is stored on ``request.state.request_id`` so handlers and
      downstream middleware can reference it.
    - The ID is added to every response as ``X-Request-ID``.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log each HTTP request with method, path, status code, and duration.

    Skips logging for paths in ``_SKIP_LOG_PREFIXES`` (health check routes)
    to avoid flooding logs with routine liveness/readiness probe traffic.

    Requires ``RequestIDMiddleware`` to run first so that
    ``request.state.request_id`` is available.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        # Record operational request metric
        metrics.increment(
            "http_requests_total",
            labels={"method": request.method, "status": response.status_code},
        )

        path = request.url.path
        if any(path.startswith(prefix) for prefix in _SKIP_LOG_PREFIXES):
            return response

        request_id = getattr(request.state, "request_id", "-")

        logger.info(
            "%s %s %d %.1fms",
            request.method,
            path,
            response.status_code,
            duration_ms,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
