"""
tests/test_run_api.py — Milestone 5: Run and Report API Endpoint tests

Test IDs:
  R-01  POST /runs web-only → 201, status=pending
  R-02  POST /runs both sources disabled → 422
  R-03  POST /runs use_documents=True with empty document_ids → 422
  R-04  POST /runs to non-existent project → 404
  R-05  POST /runs when a run is already active → 409
  R-06  GET /runs returns list → 200
  R-07  GET /runs/{id} returns single run → 200
  R-08  GET /runs/{id} wrong project → 404
  R-09  GET /runs/{id}/report while pending → 404
  R-10  GET /runs/{id}/report after mock workflow completes → 200, full report structure
  R-11  GET /runs/{id}/report after run failed → 404
  R-12  Invalid UUID project_id → 422
"""
from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from tests.conftest import TestSessionLocal
from app.models.run import ResearchRun
from app.providers.llm import MockLLMProvider
from app.providers.web_search import MockWebSearchProvider
from app.services.research_workflow import run_research_workflow

BASE = "/api/v1/projects"

# Patch target: the background task function as imported in the routes module.
# We replace it with a no-op so tests don't attempt real API calls.
_WORKFLOW_PATCH = "app.api.v1.routes.runs.run_research_workflow"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_project(client: AsyncClient, title: str = "T", question: str = "Q?") -> dict:
    r = await client.post(f"{BASE}/", json={"title": title, "research_question": question})
    assert r.status_code == 201
    return r.json()


async def _start_run(client: AsyncClient, project_id: str, **kwargs) -> object:
    """POST /runs with the workflow patched to a no-op."""
    payload = {"research_question": "What is the impact?", "use_web": True, "use_documents": False}
    payload.update(kwargs)
    with patch(_WORKFLOW_PATCH, new=AsyncMock(return_value=None)):
        return await client.post(f"{BASE}/{project_id}/runs", json=payload)


def _patch_workflow_db():
    """Redirect AsyncSessionLocal in the workflow module to the test in-memory DB."""
    return patch(
        "app.services.research_workflow.AsyncSessionLocal",
        new=TestSessionLocal,
    )


# ---------------------------------------------------------------------------
# R-01: POST /runs web-only → 201, status=pending
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_r01_start_run_web_only_returns_201(async_client: AsyncClient):
    project = await _create_project(async_client)
    r = await _start_run(async_client, project["id"])

    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "pending"
    assert data["project_id"] == project["id"]
    assert data["use_web"] is True
    assert data["use_documents"] is False
    assert data["started_at"] is None
    assert data["completed_at"] is None
    assert data["current_stage"] is None
    assert data["error_message"] is None


# ---------------------------------------------------------------------------
# R-02: POST /runs both sources disabled → 422
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_r02_both_sources_disabled_returns_422(async_client: AsyncClient):
    project = await _create_project(async_client)
    r = await _start_run(async_client, project["id"], use_web=False, use_documents=False)

    assert r.status_code == 422


# ---------------------------------------------------------------------------
# R-03: POST /runs use_documents=True with empty document_ids → 422
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_r03_use_documents_no_ids_returns_422(async_client: AsyncClient):
    project = await _create_project(async_client)
    r = await _start_run(
        async_client,
        project["id"],
        use_web=False,
        use_documents=True,
        document_ids=[],
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# R-04: POST /runs to non-existent project → 404
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_r04_nonexistent_project_returns_404(async_client: AsyncClient):
    fake_id = str(uuid.uuid4())
    r = await _start_run(async_client, fake_id)
    assert r.status_code == 404
    assert "not found" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# R-05: POST /runs when a run is already active → 409
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_r05_already_active_run_returns_409(async_client: AsyncClient):
    project = await _create_project(async_client)
    project_id = project["id"]

    # Manually insert an active (running) run into the test DB
    async with TestSessionLocal() as session:
        active_run = ResearchRun(
            id=str(uuid.uuid4()),
            project_id=project_id,
            research_question="Existing question",
            use_web=True,
            use_documents=False,
            status="running",
        )
        session.add(active_run)
        await session.commit()

    r = await _start_run(async_client, project_id)
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# R-06: GET /runs returns list → 200
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_r06_list_runs_returns_200(async_client: AsyncClient):
    project = await _create_project(async_client)
    r1 = await _start_run(async_client, project["id"])
    assert r1.status_code == 201

    r = await async_client.get(f"{BASE}/{project['id']}/runs")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["limit"] == 20
    assert data["offset"] == 0


# ---------------------------------------------------------------------------
# R-07: GET /runs/{id} returns run → 200
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_r07_get_run_returns_200(async_client: AsyncClient):
    project = await _create_project(async_client)
    start_r = await _start_run(async_client, project["id"])
    assert start_r.status_code == 201
    run_id = start_r.json()["id"]

    r = await async_client.get(f"{BASE}/{project['id']}/runs/{run_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == run_id
    assert data["project_id"] == project["id"]


# ---------------------------------------------------------------------------
# R-08: GET /runs/{id} wrong project → 404
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_r08_get_run_wrong_project_returns_404(async_client: AsyncClient):
    project1 = await _create_project(async_client, title="P1", question="Q1?")
    project2 = await _create_project(async_client, title="P2", question="Q2?")

    start_r = await _start_run(async_client, project1["id"])
    assert start_r.status_code == 201
    run_id = start_r.json()["id"]

    # Access run under wrong project
    r = await async_client.get(f"{BASE}/{project2['id']}/runs/{run_id}")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# R-09: GET /runs/{id}/report while pending → 404
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_r09_report_while_pending_returns_404(async_client: AsyncClient):
    project = await _create_project(async_client)
    start_r = await _start_run(async_client, project["id"])
    assert start_r.status_code == 201
    run_id = start_r.json()["id"]

    r = await async_client.get(f"{BASE}/{project['id']}/runs/{run_id}/report")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# R-10: GET /runs/{id}/report after mock workflow completes → 200, full report
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_r10_report_after_completion_returns_200(async_client: AsyncClient):
    project = await _create_project(async_client)
    start_r = await _start_run(async_client, project["id"])
    assert start_r.status_code == 201
    run_id = start_r.json()["id"]

    # Run the actual workflow against the test DB using mock providers
    with _patch_workflow_db():
        await run_research_workflow(
            run_id,
            llm_provider=MockLLMProvider(),
            search_provider=MockWebSearchProvider(),
        )

    r = await async_client.get(f"{BASE}/{project['id']}/runs/{run_id}/report")
    assert r.status_code == 200
    data = r.json()

    assert data["run_id"] == run_id
    assert "executive_summary" in data
    assert isinstance(data["key_findings"], list)
    assert isinstance(data["evidence_used"], list)
    assert isinstance(data["sources"], list)
    assert "limitations" in data
    assert "generated_at" in data


# ---------------------------------------------------------------------------
# R-11: GET /runs/{id}/report after run failed → 404
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_r11_report_after_failure_returns_404(async_client: AsyncClient):
    project = await _create_project(async_client)
    start_r = await _start_run(async_client, project["id"])
    assert start_r.status_code == 201
    run_id = start_r.json()["id"]

    # Run workflow with failing web search (no docs) → run enters failed state
    with _patch_workflow_db():
        await run_research_workflow(
            run_id,
            llm_provider=MockLLMProvider(),
            search_provider=MockWebSearchProvider(fail=True),
        )

    r = await async_client.get(f"{BASE}/{project['id']}/runs/{run_id}/report")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# R-12: Invalid UUID project_id → 422
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_r12_invalid_uuid_project_id_returns_422(async_client: AsyncClient):
    with patch(_WORKFLOW_PATCH, new=AsyncMock(return_value=None)):
        r = await async_client.post(
            f"{BASE}/not-a-uuid/runs",
            json={"research_question": "Test?", "use_web": True, "use_documents": False},
        )
    assert r.status_code == 422
