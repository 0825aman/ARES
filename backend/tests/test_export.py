"""Tests for the Export and Report Versioning API — Phase 5 M5.6."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ResearchProject
from app.models.report import ResearchReport
from app.models.run import ResearchRun


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _create_project(db: AsyncSession) -> str:
    project = ResearchProject(
        id=str(uuid.uuid4()),
        title="Export Test Project",
        research_question="Does export work?",
        status="active",
    )
    db.add(project)
    await db.commit()
    return project.id


async def _create_run(db: AsyncSession, project_id: str) -> str:
    run = ResearchRun(
        id=str(uuid.uuid4()),
        project_id=project_id,
        research_question="Does export work?",
        status="completed",
        workflow_mode="sequential",
    )
    db.add(run)
    await db.commit()
    return run.id


async def _create_report(
    db: AsyncSession,
    run_id: str,
    version_number: int = 1,
    is_current: bool = True,
) -> ResearchReport:
    report = ResearchReport(
        id=str(uuid.uuid4()),
        run_id=run_id,
        research_question="Does export work?",
        executive_summary="This is a test summary.",
        key_findings=json.dumps(["Finding 1", "Finding 2"]),
        evidence_used=json.dumps([]),
        observations="Some observations.",
        contradictions=None,
        limitations="Limited test scope.",
        sources=json.dumps([{"title": "Source 1", "url": "https://example.com"}]),
        has_validated_citations=False,
        version_number=version_number,
        is_current=is_current,
        generated_at=datetime.now(timezone.utc),
    )
    db.add(report)
    await db.commit()
    return report


# ── Tests: POST /export ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_pdf(async_client: AsyncClient, db_session: AsyncSession):
    """PDF export returns a ready export record with download_url."""
    project_id = await _create_project(db_session)
    run_id = await _create_run(db_session, project_id)
    await _create_report(db_session, run_id)

    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/runs/{run_id}/export",
        json={"format": "pdf"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ready"
    assert body["format"] == "pdf"
    assert body["file_size_bytes"] > 0
    assert body["download_url"] is not None
    assert "/download" in body["download_url"]


@pytest.mark.asyncio
async def test_export_docx(async_client: AsyncClient, db_session: AsyncSession):
    """DOCX export returns a ready export record."""
    project_id = await _create_project(db_session)
    run_id = await _create_run(db_session, project_id)
    await _create_report(db_session, run_id)

    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/runs/{run_id}/export",
        json={"format": "docx"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ready"
    assert body["format"] == "docx"
    assert body["file_size_bytes"] > 0


@pytest.mark.asyncio
async def test_export_markdown(async_client: AsyncClient, db_session: AsyncSession):
    """Markdown export returns a ready export record."""
    project_id = await _create_project(db_session)
    run_id = await _create_run(db_session, project_id)
    await _create_report(db_session, run_id)

    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/runs/{run_id}/export",
        json={"format": "markdown"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ready"
    assert body["format"] == "markdown"
    assert body["file_size_bytes"] > 0


@pytest.mark.asyncio
async def test_export_invalid_format(async_client: AsyncClient, db_session: AsyncSession):
    """Invalid format returns 422."""
    project_id = await _create_project(db_session)
    run_id = await _create_run(db_session, project_id)
    await _create_report(db_session, run_id)

    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/runs/{run_id}/export",
        json={"format": "txt"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_export_no_report(async_client: AsyncClient, db_session: AsyncSession):
    """Export with no report returns 422 (no report found)."""
    project_id = await _create_project(db_session)
    run_id = await _create_run(db_session, project_id)
    # No report created

    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/runs/{run_id}/export",
        json={"format": "pdf"},
    )
    assert resp.status_code == 422


# ── Tests: GET /exports ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_exports_empty(async_client: AsyncClient, db_session: AsyncSession):
    """Returns empty list when no exports exist."""
    project_id = await _create_project(db_session)
    run_id = await _create_run(db_session, project_id)

    resp = await async_client.get(f"/api/v1/projects/{project_id}/runs/{run_id}/exports")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_list_exports_after_creation(async_client: AsyncClient, db_session: AsyncSession):
    """List exports includes all created exports."""
    project_id = await _create_project(db_session)
    run_id = await _create_run(db_session, project_id)
    await _create_report(db_session, run_id)

    # Create two exports
    for fmt in ("pdf", "markdown"):
        resp = await async_client.post(
            f"/api/v1/projects/{project_id}/runs/{run_id}/export",
            json={"format": fmt},
        )
        assert resp.status_code == 200

    resp = await async_client.get(f"/api/v1/projects/{project_id}/runs/{run_id}/exports")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    formats = {item["format"] for item in body["items"]}
    assert "pdf" in formats
    assert "markdown" in formats


# ── Tests: GET /export/{id}/download ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_download_export(async_client: AsyncClient, db_session: AsyncSession):
    """Download returns a binary file response."""
    project_id = await _create_project(db_session)
    run_id = await _create_run(db_session, project_id)
    await _create_report(db_session, run_id)

    # Create export
    create_resp = await async_client.post(
        f"/api/v1/projects/{project_id}/runs/{run_id}/export",
        json={"format": "markdown"},
    )
    assert create_resp.status_code == 200
    export_id = create_resp.json()["id"]

    # Download
    dl_resp = await async_client.get(
        f"/api/v1/projects/{project_id}/runs/{run_id}/export/{export_id}/download"
    )
    assert dl_resp.status_code == 200
    assert len(dl_resp.content) > 0
    # Markdown file should contain the research question
    content = dl_resp.content.decode("utf-8")
    assert "Does export work?" in content


@pytest.mark.asyncio
async def test_download_nonexistent_export(async_client: AsyncClient, db_session: AsyncSession):
    """Returns 404 when export_id does not exist."""
    project_id = await _create_project(db_session)
    run_id = await _create_run(db_session, project_id)

    resp = await async_client.get(
        f"/api/v1/projects/{project_id}/runs/{run_id}/export/{uuid.uuid4()}/download"
    )
    assert resp.status_code == 404


# ── Tests: GET /reports ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_reports_single_version(async_client: AsyncClient, db_session: AsyncSession):
    """Returns one report when only one version exists."""
    project_id = await _create_project(db_session)
    run_id = await _create_run(db_session, project_id)
    await _create_report(db_session, run_id, version_number=1, is_current=True)

    resp = await async_client.get(f"/api/v1/projects/{project_id}/runs/{run_id}/reports")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["version_number"] == 1
    assert body["items"][0]["is_current"] is True


@pytest.mark.asyncio
async def test_list_reports_multiple_versions(async_client: AsyncClient, db_session: AsyncSession):
    """Returns all versions when multiple exist."""
    project_id = await _create_project(db_session)
    run_id = await _create_run(db_session, project_id)
    await _create_report(db_session, run_id, version_number=1, is_current=False)
    await _create_report(db_session, run_id, version_number=2, is_current=True)

    resp = await async_client.get(f"/api/v1/projects/{project_id}/runs/{run_id}/reports")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    # Should be newest first
    versions = [item["version_number"] for item in body["items"]]
    assert versions[0] == 2  # newest first
    is_current_flags = [item["is_current"] for item in body["items"]]
    assert is_current_flags[0] is True
    assert is_current_flags[1] is False
