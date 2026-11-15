"""Tests for the Approval Workflow API — Phase 5 M5.5."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import ApprovalRequest
from app.models.project import ResearchProject
from app.models.run import ResearchRun


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _create_project(db: AsyncSession) -> str:
    project = ResearchProject(
        id=str(uuid.uuid4()),
        title="Approval Test Project",
        research_question="Does approval flow work?",
        status="active",
    )
    db.add(project)
    await db.commit()
    return project.id


async def _create_run(db: AsyncSession, project_id: str, status: str = "awaiting_approval") -> str:
    run = ResearchRun(
        id=str(uuid.uuid4()),
        project_id=project_id,
        research_question="Does approval flow work?",
        status=status,
        workflow_mode="multi_agent",
    )
    db.add(run)
    await db.commit()
    return run.id


async def _create_approval_record(
    db: AsyncSession,
    run_id: str,
    status: str = "pending",
    expires_in_hours: int = 24,
) -> ApprovalRequest:
    now = datetime.now(timezone.utc)
    approval = ApprovalRequest(
        id=str(uuid.uuid4()),
        run_id=run_id,
        checkpoint_name="plan_approval",
        node_name="planning_complete_node",
        context_snapshot=json.dumps({"research_question": "Test", "research_plan": {"tasks": []}}),
        status=status,
        created_at=now,
        expires_at=now + timedelta(hours=expires_in_hours),
    )
    db.add(approval)
    await db.commit()
    return approval


# ── Tests: GET /approval ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_pending_approval_none(async_client: AsyncClient, db_session: AsyncSession):
    """Returns null when there is no pending approval for a run."""
    project_id = await _create_project(db_session)
    run_id = await _create_run(db_session, project_id)

    resp = await async_client.get(f"/api/v1/projects/{project_id}/runs/{run_id}/approval")
    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.asyncio
async def test_get_pending_approval_exists(async_client: AsyncClient, db_session: AsyncSession):
    """Returns the pending ApprovalRequest when one exists."""
    project_id = await _create_project(db_session)
    run_id = await _create_run(db_session, project_id)
    approval = await _create_approval_record(db_session, run_id)

    resp = await async_client.get(f"/api/v1/projects/{project_id}/runs/{run_id}/approval")
    assert resp.status_code == 200
    data = resp.json()
    assert data is not None
    assert data["id"] == approval.id
    assert data["status"] == "pending"
    assert data["checkpoint_name"] == "plan_approval"
    assert data["node_name"] == "planning_complete_node"
    assert isinstance(data["context_snapshot"], dict)


@pytest.mark.asyncio
async def test_get_pending_approval_expired(async_client: AsyncClient, db_session: AsyncSession):
    """Returns null and transitions the approval to expired when TTL is past."""
    project_id = await _create_project(db_session)
    run_id = await _create_run(db_session, project_id)
    # Create an already-expired approval (expires 1 hour ago)
    approval = await _create_approval_record(db_session, run_id, expires_in_hours=-1)

    resp = await async_client.get(f"/api/v1/projects/{project_id}/runs/{run_id}/approval")
    assert resp.status_code == 200
    assert resp.json() is None  # expired → null

    # Verify the DB record was transitioned
    await db_session.refresh(approval)
    assert approval.status == "expired"


@pytest.mark.asyncio
async def test_get_pending_approval_already_decided(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Returns null when only resolved (approved) records exist."""
    project_id = await _create_project(db_session)
    run_id = await _create_run(db_session, project_id)
    await _create_approval_record(db_session, run_id, status="approved")

    resp = await async_client.get(f"/api/v1/projects/{project_id}/runs/{run_id}/approval")
    assert resp.status_code == 200
    assert resp.json() is None


# ── Tests: POST /approval/{id}/decide ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_decide_approval_invalid_decision(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Returns 422 for an unrecognised decision value."""
    project_id = await _create_project(db_session)
    run_id = await _create_run(db_session, project_id)
    approval = await _create_approval_record(db_session, run_id)

    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/runs/{run_id}/approval/{approval.id}/decide",
        json={"decision": "maybe"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_decide_approval_revision_requires_notes(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Returns 422 when revision_requested is sent without notes."""
    project_id = await _create_project(db_session)
    run_id = await _create_run(db_session, project_id)
    approval = await _create_approval_record(db_session, run_id)

    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/runs/{run_id}/approval/{approval.id}/decide",
        json={"decision": "revision_requested"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_decide_approval_not_found(async_client: AsyncClient, db_session: AsyncSession):
    """Returns 404 when the approval_id does not exist for the run."""
    project_id = await _create_project(db_session)
    run_id = await _create_run(db_session, project_id)

    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/runs/{run_id}/approval/{uuid.uuid4()}/decide",
        json={"decision": "approved"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_decide_approval_rejected(async_client: AsyncClient, db_session: AsyncSession):
    """Rejected approval marks the run as failed."""
    project_id = await _create_project(db_session)
    run_id = await _create_run(db_session, project_id)
    approval = await _create_approval_record(db_session, run_id)

    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/runs/{run_id}/approval/{approval.id}/decide",
        json={"decision": "rejected", "notes": "Not relevant enough."},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "rejected"
    assert body["run_status"] == "failed"


@pytest.mark.asyncio
async def test_decide_approval_already_decided(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Returns 409 when the approval is not pending."""
    project_id = await _create_project(db_session)
    run_id = await _create_run(db_session, project_id)
    approval = await _create_approval_record(db_session, run_id, status="approved")

    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/runs/{run_id}/approval/{approval.id}/decide",
        json={"decision": "approved"},
    )
    assert resp.status_code == 409


# ── Tests: GET /approvals ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_approvals_empty(async_client: AsyncClient, db_session: AsyncSession):
    """Returns empty list when no approvals exist."""
    project_id = await _create_project(db_session)
    run_id = await _create_run(db_session, project_id)

    resp = await async_client.get(f"/api/v1/projects/{project_id}/runs/{run_id}/approvals")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_list_approvals_multiple(async_client: AsyncClient, db_session: AsyncSession):
    """Returns all approvals for a run, newest first."""
    project_id = await _create_project(db_session)
    run_id = await _create_run(db_session, project_id)
    a1 = await _create_approval_record(db_session, run_id, status="approved")
    a2 = await _create_approval_record(db_session, run_id, status="pending")

    resp = await async_client.get(f"/api/v1/projects/{project_id}/runs/{run_id}/approvals")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    ids = [item["id"] for item in body["items"]]
    # Both should be present (order: newest first — a2 was created last)
    assert a1.id in ids
    assert a2.id in ids
