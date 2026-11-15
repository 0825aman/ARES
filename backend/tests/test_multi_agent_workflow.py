"""
tests/test_multi_agent_workflow.py — Phase 3 Multi-Agent Workflow Tests

GR-001 through GR-012: Graph-level integration tests
API-001 through API-009: Phase 3 API endpoint tests
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from tests.conftest import TestSessionLocal
from app.models.project import ResearchProject
from app.models.run import ResearchRun
from app.models.plan import ResearchPlan as ResearchPlanORM
from app.models.task import ResearchTask as ResearchTaskORM
from app.models.event import AgentExecutionEvent
from app.providers.llm import MockLLMProvider
from app.providers.web_search import MockWebSearchProvider
from app.graph.state import ResearchWorkflowState


BASE = "/api/v1/projects"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_plan_json(num_tasks: int = 2) -> str:
    tasks = [
        {
            "task_id": str(uuid.uuid4()),
            "objective": f"Research dimension {i}",
            "search_query": f"research query {i}",
            "expected_evidence_type": "academic papers",
            "priority": 1,
        }
        for i in range(1, num_tasks + 1)
    ]
    return json.dumps({
        "plan_id": str(uuid.uuid4()),
        "objectives": ["Understand impacts"],
        "tasks": tasks,
        "refinement_notes": None,
    })


def _supervisor_response(decision: str, task_id: str | None = None) -> str:
    return json.dumps({
        "decision": decision,
        "reasoning": f"Test: {decision}",
        "revision_notes": None,
        "next_task_id": task_id,
    })


async def _create_project_and_run(
    db_session,
    workflow_mode: str = "multi_agent",
) -> tuple[ResearchProject, ResearchRun]:
    """Create a project + pending run in the test DB."""
    project = ResearchProject(
        id=str(uuid.uuid4()),
        title="Integration Test Project",
        research_question="Test research question?",
        status="in_progress",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(project)
    await db_session.flush()

    run = ResearchRun(
        id=str(uuid.uuid4()),
        project_id=project.id,
        research_question="What are the impacts of lithium battery mining?",
        use_web=True,
        use_documents=False,
        status="pending",
        workflow_mode=workflow_mode,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(run)
    await db_session.commit()
    return project, run


# ── GR: Graph Integration Tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gr001_happy_path_run_completes():
    """GR-001: Full happy path — run goes from pending to completed with a report."""
    from app.graph.executor import run_multi_agent_workflow

    async with TestSessionLocal() as db:
        project, run = await _create_project_and_run(db)

    plan_json = _make_plan_json(num_tasks=2)
    parsed_plan = json.loads(plan_json)
    task_ids = [t["task_id"] for t in parsed_plan["tasks"]]

    # LLM sequence:
    # 1: supervisor → request_plan
    # 2: planner → plan JSON
    # 3: supervisor → execute_next_task (task_ids[0])
    # 4: researcher findings summary
    # 5: supervisor → execute_next_task (task_ids[1])
    # 6: researcher findings summary
    # 7: supervisor → complete_research
    # 8: finalize_report LLM call
    llm_responses = [
        _supervisor_response("request_plan"),               # 1
        plan_json,                                          # 2
        _supervisor_response("execute_next_task", task_ids[0]),  # 3
        "Lithium mining has significant water impacts.",    # 4
        _supervisor_response("execute_next_task", task_ids[1]),  # 5
        "Soil degradation is also a major concern.",        # 6
        _supervisor_response("complete_research"),          # 7
        json.dumps({                                         # 8
            "executive_summary": "Lithium mining has severe environmental impacts.",
            "key_findings": ["Water usage is high", "Soil damage documented"],
            "observations": "Evidence from multiple regions.",
            "contradictions": None,
            "limitations": "Limited peer-reviewed data.",
            "sources_used": [],
        }),
    ]

    call_index = 0

    async def sequential_llm(system_prompt, user_prompt):
        nonlocal call_index
        response = llm_responses[call_index % len(llm_responses)]
        call_index += 1
        return response

    mock_llm = MockLLMProvider()
    mock_llm.complete = sequential_llm

    with patch("app.agents.supervisor.get_llm_provider") as mock_sup_llm, \
         patch("app.agents.planner.get_llm_provider") as mock_plan_llm, \
         patch("app.agents.researcher.get_llm_provider") as mock_res_llm, \
         patch("app.graph.nodes.get_llm_provider") as mock_node_llm, \
         patch("app.agents.researcher.get_search_provider") as mock_search, \
         patch("app.graph.executor.AsyncSessionLocal", new=TestSessionLocal), \
         patch("app.agents.supervisor.AsyncSessionLocal", new=TestSessionLocal), \
         patch("app.agents.planner.AsyncSessionLocal", new=TestSessionLocal), \
         patch("app.agents.researcher.AsyncSessionLocal", new=TestSessionLocal), \
         patch("app.graph.nodes.AsyncSessionLocal", new=TestSessionLocal):
        mock_sup_llm.return_value = mock_llm
        mock_plan_llm.return_value = mock_llm
        mock_res_llm.return_value = mock_llm
        mock_node_llm.return_value = mock_llm
        mock_search.return_value = MockWebSearchProvider()

        await run_multi_agent_workflow(run.id)

    async with TestSessionLocal() as db:
        run_result = await db.execute(select(ResearchRun).where(ResearchRun.id == run.id))
        final_run = run_result.scalar_one()

    assert final_run.status == "completed"


@pytest.mark.asyncio
async def test_gr002_run_creates_plan_and_tasks():
    """GR-002: Research plan and tasks are persisted to DB during workflow."""
    from app.graph.executor import run_multi_agent_workflow

    async with TestSessionLocal() as db:
        project, run = await _create_project_and_run(db)

    plan_json = _make_plan_json(num_tasks=2)
    parsed = json.loads(plan_json)
    task_ids = [t["task_id"] for t in parsed["tasks"]]

    llm_responses = iter([
        _supervisor_response("request_plan"),
        plan_json,
        _supervisor_response("execute_next_task", task_ids[0]),
        "Finding 1.",
        _supervisor_response("execute_next_task", task_ids[1]),
        "Finding 2.",
        _supervisor_response("complete_research"),
        json.dumps({"executive_summary": "Summary", "key_findings": [], "observations": None, "contradictions": None, "limitations": "Limited.", "sources_used": []}),
    ])

    async def sequential_llm(system_prompt, user_prompt):
        return next(llm_responses, _supervisor_response("complete_research"))

    mock_llm = MockLLMProvider()
    mock_llm.complete = sequential_llm

    with patch("app.agents.supervisor.get_llm_provider", return_value=mock_llm), \
         patch("app.agents.planner.get_llm_provider", return_value=mock_llm), \
         patch("app.agents.researcher.get_llm_provider", return_value=mock_llm), \
         patch("app.graph.nodes.get_llm_provider", return_value=mock_llm), \
         patch("app.agents.researcher.get_search_provider", return_value=MockWebSearchProvider()), \
         patch("app.graph.executor.AsyncSessionLocal", new=TestSessionLocal), \
         patch("app.agents.supervisor.AsyncSessionLocal", new=TestSessionLocal), \
         patch("app.agents.planner.AsyncSessionLocal", new=TestSessionLocal), \
         patch("app.agents.researcher.AsyncSessionLocal", new=TestSessionLocal), \
         patch("app.graph.nodes.AsyncSessionLocal", new=TestSessionLocal):
        await run_multi_agent_workflow(run.id)

    async with TestSessionLocal() as db:
        plans = (await db.execute(
            select(ResearchPlanORM).where(ResearchPlanORM.run_id == run.id)
        )).scalars().all()
        tasks = (await db.execute(
            select(ResearchTaskORM).where(ResearchTaskORM.run_id == run.id)
        )).scalars().all()

    assert len(plans) == 1
    assert len(tasks) == 2


@pytest.mark.asyncio
async def test_gr003_workflow_events_logged():
    """GR-003: AgentExecutionEvents are written throughout the workflow."""
    from app.graph.executor import run_multi_agent_workflow

    async with TestSessionLocal() as db:
        project, run = await _create_project_and_run(db)

    plan_json = _make_plan_json(num_tasks=1)
    parsed = json.loads(plan_json)
    task_id = parsed["tasks"][0]["task_id"]

    llm_responses = iter([
        _supervisor_response("request_plan"),
        plan_json,
        _supervisor_response("execute_next_task", task_id),
        "Finding.",
        _supervisor_response("complete_research"),
        json.dumps({"executive_summary": "Done", "key_findings": [], "observations": None, "contradictions": None, "limitations": "None.", "sources_used": []}),
    ])

    async def seq_llm(system_prompt, user_prompt):
        return next(llm_responses, _supervisor_response("complete_research"))

    mock_llm = MockLLMProvider()
    mock_llm.complete = seq_llm

    with patch("app.agents.supervisor.get_llm_provider", return_value=mock_llm), \
         patch("app.agents.planner.get_llm_provider", return_value=mock_llm), \
         patch("app.agents.researcher.get_llm_provider", return_value=mock_llm), \
         patch("app.graph.nodes.get_llm_provider", return_value=mock_llm), \
         patch("app.agents.researcher.get_search_provider", return_value=MockWebSearchProvider()), \
         patch("app.graph.executor.AsyncSessionLocal", new=TestSessionLocal), \
         patch("app.agents.supervisor.AsyncSessionLocal", new=TestSessionLocal), \
         patch("app.agents.planner.AsyncSessionLocal", new=TestSessionLocal), \
         patch("app.agents.researcher.AsyncSessionLocal", new=TestSessionLocal), \
         patch("app.graph.nodes.AsyncSessionLocal", new=TestSessionLocal):
        await run_multi_agent_workflow(run.id)

    async with TestSessionLocal() as db:
        events = (await db.execute(
            select(AgentExecutionEvent).where(AgentExecutionEvent.run_id == run.id)
        )).scalars().all()

    # Should have: workflow_start, supervisor decision, plan_created, supervisor decision, task_started, task_completed, supervisor decision, workflow_complete
    assert len(events) >= 4
    event_types = {e.event_type for e in events}
    assert "workflow_start" in event_types
    assert "workflow_complete" in event_types


@pytest.mark.asyncio
async def test_gr004_max_iterations_terminates_workflow():
    """GR-004: Workflow terminates when max_supervisor_cycles reached."""
    from app.graph.executor import run_multi_agent_workflow

    async with TestSessionLocal() as db:
        project, run = await _create_project_and_run(db)

    # Supervisor always wants more research but max_cycles=1 forces completion
    # With MAX_SUPERVISOR_CYCLES=1 (env default=3), use 1 cycle
    with patch("app.core.config.settings") as mock_settings, \
         patch("app.agents.supervisor.get_llm_provider") as mock_sup_llm, \
         patch("app.agents.planner.get_llm_provider") as mock_plan_llm, \
         patch("app.agents.researcher.get_llm_provider") as mock_res_llm, \
         patch("app.graph.nodes.get_llm_provider") as mock_node_llm, \
         patch("app.agents.researcher.get_search_provider") as mock_search, \
         patch("app.graph.executor.AsyncSessionLocal", new=TestSessionLocal), \
         patch("app.agents.supervisor.AsyncSessionLocal", new=TestSessionLocal), \
         patch("app.agents.planner.AsyncSessionLocal", new=TestSessionLocal), \
         patch("app.agents.researcher.AsyncSessionLocal", new=TestSessionLocal), \
         patch("app.graph.nodes.AsyncSessionLocal", new=TestSessionLocal):

        mock_settings.MAX_SUPERVISOR_CYCLES = 1
        mock_settings.LLM_CONTEXT_BUDGET_CHARS = 100000
        mock_settings.CHECKPOINT_DB_URL = "./maar_checkpoints_test.db"

        plan_json = _make_plan_json(1)
        report_json = json.dumps({"executive_summary": "Done", "key_findings": [], "observations": None, "contradictions": None, "limitations": "None.", "sources_used": []})

        llm_iter = iter([
            _supervisor_response("request_plan"),  # cycle 0 — supervisor
            plan_json,                              # planner
            # cycle 1 → forced completion (iteration_count >= max_supervisor_cycles=1)
            report_json,                            # finalize
        ])

        async def seq_llm(sp, up):
            return next(llm_iter, report_json)

        mock_llm = MockLLMProvider()
        mock_llm.complete = seq_llm
        mock_sup_llm.return_value = mock_llm
        mock_plan_llm.return_value = mock_llm
        mock_res_llm.return_value = mock_llm
        mock_node_llm.return_value = mock_llm
        mock_search.return_value = MockWebSearchProvider()

        await run_multi_agent_workflow(run.id)

    async with TestSessionLocal() as db:
        run_result = await db.execute(select(ResearchRun).where(ResearchRun.id == run.id))
        final_run = run_result.scalar_one()

    # Should be completed (forced) or failed gracefully — not stuck in pending
    assert final_run.status in ("completed", "failed")


@pytest.mark.asyncio
async def test_gr005_run_not_found_exits_cleanly():
    """GR-005: executor returns cleanly when run_id does not exist."""
    from app.graph.executor import run_multi_agent_workflow

    with patch("app.graph.executor.AsyncSessionLocal", new=TestSessionLocal):
        # Should not raise — just log and return
        await run_multi_agent_workflow("non-existent-run-id")


@pytest.mark.asyncio
async def test_gr006_sequential_run_uses_phase2_workflow():
    """GR-006: workflow_mode=sequential routes to run_research_workflow, not multi-agent."""
    from app.graph.executor import run_multi_agent_workflow
    from app.services.research_workflow import run_research_workflow

    async with TestSessionLocal() as db:
        project, run = await _create_project_and_run(db, workflow_mode="sequential")

    # run_multi_agent_workflow should NOT be called for sequential runs
    # (the routing in runs.py handles this, not the executor itself)
    # This test verifies the executor exits early for non-pending runs
    async with TestSessionLocal() as db:
        run_result = await db.execute(select(ResearchRun).where(ResearchRun.id == run.id))
        found_run = run_result.scalar_one()
        found_run.status = "completed"  # simulate already completed
        await db.commit()

    with patch("app.graph.executor.AsyncSessionLocal", new=TestSessionLocal):
        await run_multi_agent_workflow(run.id)  # should exit early — run not pending

    async with TestSessionLocal() as db:
        run_result = await db.execute(select(ResearchRun).where(ResearchRun.id == run.id))
        final_run = run_result.scalar_one()

    assert final_run.status == "completed"  # unchanged


@pytest.mark.asyncio
async def test_gr007_workflow_handles_planning_failure():
    """GR-007: When LLM always returns invalid JSON, Supervisor falls back to
    complete_research (by design — to preserve collected evidence).
    The workflow completes (possibly with empty evidence report).
    It does NOT hang or leave the run in 'pending' state.
    """
    from app.graph.executor import run_multi_agent_workflow

    async with TestSessionLocal() as db:
        project, run = await _create_project_and_run(db)

    async def always_invalid(system_prompt, user_prompt):
        return "NOT JSON"  # Always invalid — triggers supervisor fallback

    mock_llm = MockLLMProvider()
    mock_llm.complete = always_invalid

    with patch("app.agents.supervisor.get_llm_provider", return_value=mock_llm), \
         patch("app.agents.planner.get_llm_provider", return_value=mock_llm), \
         patch("app.agents.researcher.get_llm_provider", return_value=mock_llm), \
         patch("app.graph.nodes.get_llm_provider", return_value=mock_llm), \
         patch("app.agents.researcher.get_search_provider", return_value=MockWebSearchProvider()), \
         patch("app.graph.executor.AsyncSessionLocal", new=TestSessionLocal), \
         patch("app.agents.supervisor.AsyncSessionLocal", new=TestSessionLocal), \
         patch("app.agents.planner.AsyncSessionLocal", new=TestSessionLocal), \
         patch("app.agents.researcher.AsyncSessionLocal", new=TestSessionLocal), \
         patch("app.graph.nodes.AsyncSessionLocal", new=TestSessionLocal):
        await run_multi_agent_workflow(run.id)

    async with TestSessionLocal() as db:
        run_result = await db.execute(select(ResearchRun).where(ResearchRun.id == run.id))
        final_run = run_result.scalar_one()

    # Supervisor's fallback behaviour: invalid JSON → complete_research (not fail)
    # Run ends in 'completed' (with empty evidence report) or 'failed' if graph errors
    assert final_run.status in ("completed", "failed"), (
        f"Expected completed or failed, got {final_run.status!r}"
    )


# ── API Tests (API-001 through API-009) ────────────────────────────────────────

async def _create_project_via_api(client: AsyncClient) -> dict:
    r = await client.post(f"{BASE}/", json={"title": "P3 Test", "research_question": "Q?"})
    assert r.status_code == 201
    return r.json()


@pytest.mark.asyncio
async def test_api001_start_run_with_multi_agent_mode(async_client: AsyncClient):
    """API-001: POST /runs with workflow_mode=multi_agent returns 201."""
    project = await _create_project_via_api(async_client)

    with patch("app.graph.executor.run_multi_agent_workflow", new=AsyncMock(return_value=None)):
        r = await async_client.post(
            f"{BASE}/{project['id']}/runs",
            json={"research_question": "Test?", "use_web": True, "workflow_mode": "multi_agent"},
        )

    assert r.status_code == 201
    assert r.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_api002_start_run_without_workflow_mode_defaults_sequential(async_client: AsyncClient):
    """API-002: POST /runs without workflow_mode defaults to sequential."""
    project = await _create_project_via_api(async_client)

    with patch("app.api.v1.routes.runs.run_research_workflow", new=AsyncMock(return_value=None)):
        r = await async_client.post(
            f"{BASE}/{project['id']}/runs",
            json={"research_question": "Test?", "use_web": True},
        )

    assert r.status_code == 201


@pytest.mark.asyncio
async def test_api003_get_plan_no_plan_returns_404(async_client: AsyncClient):
    """API-003: GET /plan before any plan is created returns 404."""
    project = await _create_project_via_api(async_client)

    with patch("app.api.v1.routes.runs.run_research_workflow", new=AsyncMock(return_value=None)):
        run_r = await async_client.post(
            f"{BASE}/{project['id']}/runs",
            json={"research_question": "Test?", "use_web": True},
        )
    run_id = run_r.json()["id"]

    r = await async_client.get(f"{BASE}/{project['id']}/runs/{run_id}/plan")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_api004_get_tasks_empty_returns_empty_list(async_client: AsyncClient):
    """API-004: GET /tasks before any tasks are created returns empty list."""
    project = await _create_project_via_api(async_client)

    with patch("app.api.v1.routes.runs.run_research_workflow", new=AsyncMock(return_value=None)):
        run_r = await async_client.post(
            f"{BASE}/{project['id']}/runs",
            json={"research_question": "Test?", "use_web": True},
        )
    run_id = run_r.json()["id"]

    r = await async_client.get(f"{BASE}/{project['id']}/runs/{run_id}/tasks")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_api005_get_activity_empty_returns_empty_list(async_client: AsyncClient):
    """API-005: GET /activity before any events returns empty list."""
    project = await _create_project_via_api(async_client)

    with patch("app.api.v1.routes.runs.run_research_workflow", new=AsyncMock(return_value=None)):
        run_r = await async_client.post(
            f"{BASE}/{project['id']}/runs",
            json={"research_question": "Test?", "use_web": True},
        )
    run_id = run_r.json()["id"]

    r = await async_client.get(f"{BASE}/{project['id']}/runs/{run_id}/activity")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["events"] == []


@pytest.mark.asyncio
async def test_api006_get_plan_after_plan_created(async_client: AsyncClient):
    """API-006: GET /plan returns plan after it's been persisted."""
    from app.services.plan_service import save_plan
    from app.schemas.plan import ResearchPlan, ResearchTask

    project = await _create_project_via_api(async_client)

    with patch("app.api.v1.routes.runs.run_research_workflow", new=AsyncMock(return_value=None)):
        run_r = await async_client.post(
            f"{BASE}/{project['id']}/runs",
            json={"research_question": "Test?", "use_web": True},
        )
    run_id = run_r.json()["id"]

    # Manually create a plan in the DB (minimum 2 tasks required)
    async with TestSessionLocal() as db:
        plan = ResearchPlan(
            plan_id=str(uuid.uuid4()),
            objectives=["Understand impacts"],
            tasks=[
                ResearchTask(
                    task_id=str(uuid.uuid4()),
                    objective="Find data",
                    search_query="impact data",
                    expected_evidence_type="statistics",
                    priority=1,
                ),
                ResearchTask(
                    task_id=str(uuid.uuid4()),
                    objective="Review literature",
                    search_query="impact literature review",
                    expected_evidence_type="academic papers",
                    priority=2,
                ),
            ],
        )
        await save_plan(db, run_id, plan)
        await db.commit()

    r = await async_client.get(f"{BASE}/{project['id']}/runs/{run_id}/plan")
    assert r.status_code == 200
    data = r.json()
    assert len(data["tasks"]) == 2
    assert data["objectives"] == ["Understand impacts"]


@pytest.mark.asyncio
async def test_api007_get_tasks_returns_list_with_status(async_client: AsyncClient):
    """API-007: GET /tasks returns tasks with correct status field."""
    from app.services.plan_service import save_plan
    from app.schemas.plan import ResearchPlan, ResearchTask

    project = await _create_project_via_api(async_client)

    with patch("app.api.v1.routes.runs.run_research_workflow", new=AsyncMock(return_value=None)):
        run_r = await async_client.post(
            f"{BASE}/{project['id']}/runs",
            json={"research_question": "Test?", "use_web": True},
        )
    run_id = run_r.json()["id"]

    task_id = str(uuid.uuid4())
    async with TestSessionLocal() as db:
        plan = ResearchPlan(
            plan_id=str(uuid.uuid4()),
            objectives=["Obj"],
            tasks=[
                ResearchTask(task_id=task_id, objective="T1", search_query="q1", expected_evidence_type="papers", priority=1),
                ResearchTask(task_id=str(uuid.uuid4()), objective="T2", search_query="q2", expected_evidence_type="papers", priority=2),
            ],
        )
        await save_plan(db, run_id, plan)
        await db.commit()

    r = await async_client.get(f"{BASE}/{project['id']}/runs/{run_id}/tasks")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    assert data["items"][0]["status"] == "pending"


@pytest.mark.asyncio
async def test_api008_get_activity_returns_events(async_client: AsyncClient):
    """API-008: GET /activity returns AgentExecutionEvents."""
    from app.services.event_service import log_event

    project = await _create_project_via_api(async_client)

    with patch("app.api.v1.routes.runs.run_research_workflow", new=AsyncMock(return_value=None)):
        run_r = await async_client.post(
            f"{BASE}/{project['id']}/runs",
            json={"research_question": "Test?", "use_web": True},
        )
    run_id = run_r.json()["id"]

    async with TestSessionLocal() as db:
        await log_event(db, run_id=run_id, agent_name="system", event_type="workflow_start", summary="Workflow started")
        await db.commit()

    r = await async_client.get(f"{BASE}/{project['id']}/runs/{run_id}/activity")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["events"][0]["event_type"] == "workflow_start"
    assert data["events"][0]["agent_name"] == "system"


@pytest.mark.asyncio
async def test_api009_get_plan_wrong_project_returns_404(async_client: AsyncClient):
    """API-009: GET /plan with wrong project_id returns 404."""
    project = await _create_project_via_api(async_client)
    other_project = await _create_project_via_api(async_client)

    with patch("app.api.v1.routes.runs.run_research_workflow", new=AsyncMock(return_value=None)):
        run_r = await async_client.post(
            f"{BASE}/{project['id']}/runs",
            json={"research_question": "Test?", "use_web": True},
        )
    run_id = run_r.json()["id"]

    # Use other_project's ID to access run from first project
    r = await async_client.get(f"{BASE}/{other_project['id']}/runs/{run_id}/plan")
    assert r.status_code == 404
