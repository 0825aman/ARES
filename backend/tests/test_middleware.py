from __future__ import annotations

"""test_middleware.py — Tests for RequestIDMiddleware and RequestLoggingMiddleware.

Verifies:
  - X-Request-ID is present on every response.
  - An X-Request-ID provided by the caller is echoed back (not replaced).
  - A new UUID is generated when no X-Request-ID is provided.
  - Request logging fires for non-health paths.
  - Health paths are skipped by the logging middleware.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def test_response_includes_request_id(async_client: AsyncClient):
    """Every response must include an X-Request-ID header."""
    response = await async_client.get("/health")
    assert "x-request-id" in response.headers


async def test_generated_request_id_is_uuid(async_client: AsyncClient):
    """When no X-Request-ID is sent, the generated value must be a valid UUID4."""
    response = await async_client.get("/health")
    request_id = response.headers.get("x-request-id", "")
    parsed = uuid.UUID(request_id, version=4)
    assert str(parsed) == request_id


async def test_caller_request_id_is_echoed(async_client: AsyncClient):
    """When the caller sends X-Request-ID, the same value is echoed back."""
    caller_id = "test-correlation-12345"
    response = await async_client.get("/health", headers={"X-Request-ID": caller_id})
    assert response.headers.get("x-request-id") == caller_id


async def test_different_requests_get_different_ids(async_client: AsyncClient):
    """Two requests without an X-Request-ID should receive different IDs."""
    r1 = await async_client.get("/health")
    r2 = await async_client.get("/health")
    id1 = r1.headers.get("x-request-id")
    id2 = r2.headers.get("x-request-id")
    assert id1 != id2


async def test_request_id_on_api_route(async_client: AsyncClient):
    """X-Request-ID must appear on API routes, not just health routes."""
    response = await async_client.get("/api/v1/projects")
    assert "x-request-id" in response.headers


async def test_request_logging_fires_for_api_route(async_client: AsyncClient):
    """RequestLoggingMiddleware must call logger.info for non-health paths."""
    with patch("app.core.middleware.logger") as mock_logger:
        await async_client.get("/api/v1/projects")
    mock_logger.info.assert_called_once()
    call_args = mock_logger.info.call_args
    # Positional args: format string, method, path, status, duration
    assert "/api/v1/projects" in str(call_args)


async def test_request_logging_skipped_for_health_path(async_client: AsyncClient):
    """RequestLoggingMiddleware must NOT log /health* paths."""
    with patch("app.core.middleware.logger") as mock_logger:
        await async_client.get("/health")
    mock_logger.info.assert_not_called()


async def test_global_exception_handler_response_shape():
    """The global exception handler in app/main.py must return a consistent JSON body.

    Tests the handler function directly (not via HTTP) to avoid the Starlette
    BaseHTTPMiddleware re-raise-before-response limitation in Python 3.14.
    """
    from unittest.mock import MagicMock
    from app.main import unhandled_exception_handler

    mock_request = MagicMock()
    mock_request.state.request_id = "test-req-id-abc123"
    mock_request.method = "GET"
    mock_request.url.path = "/api/v1/test"

    response = await unhandled_exception_handler(mock_request, RuntimeError("boom"))

    assert response.status_code == 500
    import json
    body = json.loads(response.body)
    assert body["detail"] == "Internal server error"
    assert body["request_id"] == "test-req-id-abc123"
    assert response.headers.get("x-request-id") == "test-req-id-abc123"
