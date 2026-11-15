"""test_e2e_workflow.py — End-to-end acceptance testing for MAAR research platform."""
import json
import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import ResearchReport
from app.providers.llm import CANNED_REPORT_JSON, MockLLMProvider


@pytest.mark.asyncio
async def test_full_project_lifecycle_and_cascade(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch,
):
    # Mock LLM provider so no live external API is needed
    mock_provider = MockLLMProvider(response=CANNED_REPORT_JSON)
    monkeypatch.setattr("app.providers.llm.get_llm_provider", lambda: mock_provider)
    monkeypatch.setattr("app.services.research_workflow.get_llm_provider", lambda: mock_provider)

    from app.providers.web_search import SearchResult
    class MockSearch:
        async def search(self, query: str, max_results: int = 5):
            return [
                SearchResult(
                    url="https://example.com/multi-agent",
                    title="Multi-Agent Systems",
                    snippet="Recent advances in autonomous multi-agent systems.",
                    raw_content="Recent advances in autonomous multi-agent systems.",
                )
            ]
    monkeypatch.setattr("app.services.research_workflow.get_search_provider", lambda: MockSearch())

    client = authenticated_client

    # 1. Create a new research project
    create_proj_resp = await client.post(
        "/api/v1/projects/",
        json={
            "title": "E2E Test Research Project",
            "research_question": "What are the latest advances in multi-agent autonomous research systems?",
            "description": "Testing full lifecycle cascade",
            "category": "Technology",
        },
    )
    assert create_proj_resp.status_code == 201
    project = create_proj_resp.json()
    project_id = project["id"]
    assert project["title"] == "E2E Test Research Project"

    # 2. Start a research run
    start_run_resp = await client.post(
        f"/api/v1/projects/{project_id}/runs",
        json={
            "research_question": "What are the latest advances in multi-agent autonomous research systems?",
            "use_web": True,
            "use_documents": False,
            "workflow_mode": "sequential",
            "verification_depth": "basic",
        },
    )
    assert start_run_resp.status_code == 201
    run = start_run_resp.json()
    run_id = run["id"]
    assert run["status"] == "pending"

    # 3. Simulate completion and create an associated report record
    report = ResearchReport(
        id=str(uuid.uuid4()),
        run_id=run_id,
        research_question=run["research_question"],
        executive_summary="Executive summary for multi-agent autonomous systems.",
        key_findings=json.dumps(["Finding 1: High coordination efficiency.", "Finding 2: Traceable evidence."]),
        evidence_used=json.dumps([]),
        observations="System exhibits strong emergent collaboration.",
        contradictions=None,
        limitations="Evaluation conducted in simulated environments.",
        sources=json.dumps([{"title": "Multi-Agent Systems", "url": "https://example.com/multi-agent"}]),
        has_validated_citations=True,
        version_number=1,
        is_current=True,
        generated_at=datetime.now(timezone.utc),
    )
    db_session.add(report)
    await db_session.commit()

    # 4. Trigger exports for all three formats (markdown, docx, pdf)
    for fmt in ["markdown", "docx", "pdf"]:
        export_resp = await client.post(
            f"/api/v1/projects/{project_id}/runs/{run_id}/export",
            json={"format": fmt},
        )
        assert export_resp.status_code == 200
        export_data = export_resp.json()
        assert export_data["status"] == "ready"
        assert export_data["format"] == fmt
        assert export_data["file_size_bytes"] > 0

    # 5. List exports
    list_exports_resp = await client.get(f"/api/v1/projects/{project_id}/runs/{run_id}/exports")
    assert list_exports_resp.status_code == 200
    exports_list = list_exports_resp.json()
    assert len(exports_list["items"]) == 3

    # 6. Check project listing includes created project
    list_resp = await client.get("/api/v1/projects/")
    assert list_resp.status_code == 200
    projects_data = list_resp.json()
    assert any(p["id"] == project_id for p in projects_data["items"])

    # 7. Delete project and verify cascade
    del_resp = await client.delete(f"/api/v1/projects/{project_id}")
    assert del_resp.status_code == 204

    # 8. Verify project is gone
    get_proj_resp = await client.get(f"/api/v1/projects/{project_id}")
    assert get_proj_resp.status_code == 404
