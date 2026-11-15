"""
tests/test_sequential_claim_verification.py — Phase 4 M4.4: Sequential workflow integration

Test IDs:
  SCV-01  Sequential workflow runs with verification_depth in StartRunRequest
  SCV-02  RunResponse includes verification_depth field
  SCV-03  ResearchRun DB record has verification_depth column
  SCV-04  StartRunRequest defaults verification_depth to "basic"
  SCV-05  StartRunRequest accepts "thorough" as verification_depth value
  SCV-06  GET /runs/{run_id}/claims returns 200 (endpoint works after run created)
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_project(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/projects/",
        json={"title": "SCV Test", "research_question": "What is claim verification?"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scv01_start_run_accepts_verification_depth(async_client: AsyncClient):
    """SCV-01: POST /runs with verification_depth='thorough' → 201."""
    project_id = await _create_project(async_client)
    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/runs",
        json={
            "research_question": "What is claim verification?",
            "workflow_mode": "sequential",
            "verification_depth": "thorough",
        },
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_scv02_run_response_includes_verification_depth(async_client: AsyncClient):
    """SCV-02: RunResponse includes verification_depth field."""
    project_id = await _create_project(async_client)
    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/runs",
        json={
            "research_question": "Q?",
            "workflow_mode": "sequential",
            "verification_depth": "basic",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "verification_depth" in body
    assert body["verification_depth"] == "basic"


@pytest.mark.asyncio
async def test_scv03_run_record_has_verification_depth(async_client: AsyncClient):
    """SCV-03: ResearchRun DB record has verification_depth stored correctly."""
    project_id = await _create_project(async_client)
    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/runs",
        json={
            "research_question": "Q?",
            "workflow_mode": "sequential",
            "verification_depth": "thorough",
        },
    )
    run_id = resp.json()["id"]

    # Re-fetch the run to verify persisted value
    get_resp = await async_client.get(f"/api/v1/projects/{project_id}/runs/{run_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["verification_depth"] == "thorough"


@pytest.mark.asyncio
async def test_scv04_default_verification_depth_is_basic(async_client: AsyncClient):
    """SCV-04: verification_depth defaults to 'basic' when not specified."""
    project_id = await _create_project(async_client)
    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/runs",
        json={"research_question": "Q?", "workflow_mode": "sequential"},
    )
    assert resp.status_code == 201
    assert resp.json()["verification_depth"] == "basic"


@pytest.mark.asyncio
async def test_scv05_thorough_depth_accepted(async_client: AsyncClient):
    """SCV-05: verification_depth='thorough' is accepted and stored."""
    project_id = await _create_project(async_client)
    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/runs",
        json={
            "research_question": "Q?",
            "workflow_mode": "sequential",
            "verification_depth": "thorough",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["verification_depth"] == "thorough"


@pytest.mark.asyncio
async def test_scv06_get_claims_endpoint_works(async_client: AsyncClient):
    """SCV-06: GET /runs/{run_id}/claims returns 200."""
    project_id = await _create_project(async_client)
    run_resp = await async_client.post(
        f"/api/v1/projects/{project_id}/runs",
        json={"research_question": "Q?", "workflow_mode": "sequential"},
    )
    run_id = run_resp.json()["id"]

    resp = await async_client.get(f"/api/v1/projects/{project_id}/runs/{run_id}/claims")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0  # No claims yet — run hasn't executed
    assert body["items"] == []
