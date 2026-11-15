from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import SQLAlchemyError


# ---------------------------------------------------------------------------
# GET /health — full health check
# ---------------------------------------------------------------------------


async def test_health_returns_200(async_client: AsyncClient):
    response = await async_client.get("/health")
    assert response.status_code == 200


async def test_health_response_shape(async_client: AsyncClient):
    response = await async_client.get("/health")
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "environment" in data
    assert "database" in data


async def test_health_status_is_ok(async_client: AsyncClient):
    response = await async_client.get("/health")
    assert response.json()["status"] == "ok"


async def test_health_database_ok(async_client: AsyncClient):
    response = await async_client.get("/health")
    assert response.json()["database"] == "ok"


async def test_health_database_error_returns_503(async_client: AsyncClient):
    """When the DB execute raises, /health must return HTTP 503 with database='error'."""
    with patch(
        "app.api.v1.routes.health.AsyncSession.execute",
        new_callable=AsyncMock,
        side_effect=SQLAlchemyError("DB connection failed"),
    ):
        response = await async_client.get("/health")

    assert response.status_code == 503
    assert response.json()["database"] == "error"


# ---------------------------------------------------------------------------
# GET /health/live — liveness probe
# ---------------------------------------------------------------------------


async def test_health_live_returns_200(async_client: AsyncClient):
    """Liveness probe must always return 200."""
    response = await async_client.get("/health/live")
    assert response.status_code == 200


async def test_health_live_response_shape(async_client: AsyncClient):
    response = await async_client.get("/health/live")
    data = response.json()
    assert data.get("status") == "alive"


async def test_health_live_does_not_hit_db(async_client: AsyncClient):
    """Liveness probe must return 200 even when the DB is down."""
    with patch(
        "app.api.v1.routes.health.AsyncSession.execute",
        new_callable=AsyncMock,
        side_effect=SQLAlchemyError("DB connection failed"),
    ):
        response = await async_client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"


# ---------------------------------------------------------------------------
# GET /health/ready — readiness probe
# ---------------------------------------------------------------------------


async def test_health_ready_returns_200(async_client: AsyncClient):
    """Readiness probe returns 200 when DB is accessible."""
    response = await async_client.get("/health/ready")
    assert response.status_code == 200


async def test_health_ready_response_shape(async_client: AsyncClient):
    response = await async_client.get("/health/ready")
    data = response.json()
    assert data.get("status") == "ready"
    assert data.get("database") == "ok"


async def test_health_ready_returns_503_when_db_fails(async_client: AsyncClient):
    """Readiness probe must return 503 when DB execute raises."""
    with patch(
        "app.api.v1.routes.health.AsyncSession.execute",
        new_callable=AsyncMock,
        side_effect=SQLAlchemyError("DB connection failed"),
    ):
        response = await async_client.get("/health/ready")

    assert response.status_code == 503
    data = response.json()
    assert data.get("database") == "error"
