"""Tests for the Token Tracking & Telemetry API."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ResearchProject
from app.models.run import ResearchRun
from app.services.token_service import get_token_summary


@pytest.mark.asyncio
async def test_token_summary_service_empty(db_session: AsyncSession):
    """Empty DB returns clean zero/default token metrics structure."""
    summary = await get_token_summary(db_session)
    assert summary["total_tokens"] == 0
    assert summary["total_llm_calls"] == 0
    assert "by_agent" in summary
    assert len(summary["by_agent"]) == 4
    assert "pictograph" in summary
    assert "equivalents" in summary


@pytest.mark.asyncio
async def test_token_summary_service_with_runs(db_session: AsyncSession):
    """DB with runs returns correct aggregated token counts."""
    project = ResearchProject(
        id="proj-tok-1",
        title="Test Project",
        research_question="What is the token usage?",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    run = ResearchRun(
        id="run-tok-1",
        project_id="proj-tok-1",
        research_question="What is the token usage?",
        status="completed",
        total_tokens_used=24000,
        llm_call_count=12,
        estimated_cost_usd=0.0036,
    )
    db_session.add(run)
    await db_session.commit()

    summary = await get_token_summary(db_session)
    assert summary["total_tokens"] == 24000
    assert summary["total_llm_calls"] == 12
    assert summary["total_runs"] == 1
    assert summary["prompt_tokens"] > 0
    assert summary["completion_tokens"] > 0
    assert len(summary["top_runs"]) == 1
    assert summary["top_runs"][0]["tokens"] == 24000


@pytest.mark.asyncio
async def test_tokens_api_endpoint(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/tokens/summary returns 200 with complete telemetry payload."""
    resp = await async_client.get("/api/v1/tokens/summary")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "total_tokens" in body
    assert "by_agent" in body
    assert "timeline" in body
    assert "pictograph" in body
    assert "equivalents" in body
