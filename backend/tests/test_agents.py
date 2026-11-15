"""
tests/test_agents.py — Phase 3 Agent Unit Tests

PA-001 through PA-008: Planning Agent
RA-001 through RA-009: Research Agent
SA-001 through SA-009: Supervisor Agent
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import TestSessionLocal
from app.models.project import ResearchProject
from app.models.run import ResearchRun
from app.providers.llm import MockLLMProvider
from app.providers.web_search import MockWebSearchProvider, SearchResult
from app.graph.state import ResearchWorkflowState


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_state(**overrides) -> ResearchWorkflowState:
    """Build a minimal ResearchWorkflowState for testing."""
    base: ResearchWorkflowState = {
        "run_id": str(uuid.uuid4()),
        "project_id": str(uuid.uuid4()),
        "research_question": "What are the environmental impacts of lithium battery mining?",
        "workflow_mode": "multi_agent",
        "max_supervisor_cycles": 3,
        "research_plan": None,
        "research_tasks": [],
        "pending_task_ids": [],
        "current_task_id": None,
        "completed_task_ids": [],
        "failed_task_ids": [],
        "collected_evidence_ids": [],
        "task_results": {},
        "supervisor_decision": None,
        "revision_notes": None,
        "iteration_count": 0,
        "workflow_status": "initializing",
        "error_message": None,
        "final_report_id": None,
    }
    base.update(overrides)
    return base


def _make_valid_plan_json(num_tasks: int = 3) -> str:
    """Return valid JSON that the Planning Agent's LLM would produce."""
    tasks = [
        {
            "task_id": str(uuid.uuid4()),
            "objective": f"Investigate aspect {i} of the research question",
            "search_query": f"lithium mining environmental impact aspect {i}",
            "expected_evidence_type": "academic papers",
            "priority": min(i, 3),
        }
        for i in range(1, num_tasks + 1)
    ]
    return json.dumps({
        "plan_id": str(uuid.uuid4()),
        "objectives": ["Understand environmental impacts", "Assess scale of mining"],
        "tasks": tasks,
        "refinement_notes": None,
    })


async def _create_run_in_db(db: AsyncSession, workflow_mode: str = "multi_agent") -> ResearchRun:
    """Insert a minimal ResearchProject + ResearchRun for testing."""
    project = ResearchProject(
        id=str(uuid.uuid4()),
        title="Test Project",
        research_question="Test question?",
        status="in_progress",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(project)
    await db.flush()

    run = ResearchRun(
        id=str(uuid.uuid4()),
        project_id=project.id,
        research_question="What are the environmental impacts of lithium battery mining?",
        use_web=True,
        use_documents=False,
        status="running",
        workflow_mode=workflow_mode,
        created_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


# ── Planning Agent Tests (PA-001 through PA-008) ───────────────────────────────

@pytest.mark.asyncio
async def test_pa001_planning_node_produces_valid_plan():
    """PA-001: planning_node returns research_plan with 2-8 tasks."""
    from app.agents.planner import planning_node

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    state = _make_state(run_id=run.id)

    with patch("app.agents.planner.get_llm_provider") as mock_llm_factory, \
         patch("app.agents.planner.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_factory.return_value = MockLLMProvider(response=_make_valid_plan_json(3))
        result = await planning_node(state, {})

    assert result.get("workflow_status") == "researching"
    assert result.get("research_plan") is not None
    assert len(result.get("research_tasks", [])) == 3
    assert len(result.get("pending_task_ids", [])) == 3


@pytest.mark.asyncio
async def test_pa002_planning_node_persists_plan_to_db():
    """PA-002: plan and tasks are written to the database."""
    from app.agents.planner import planning_node
    from app.models.plan import ResearchPlan as ResearchPlanORM
    from app.models.task import ResearchTask as ResearchTaskORM
    from sqlalchemy import select

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    state = _make_state(run_id=run.id)

    with patch("app.agents.planner.get_llm_provider") as mock_llm_factory, \
         patch("app.agents.planner.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_factory.return_value = MockLLMProvider(response=_make_valid_plan_json(3))
        await planning_node(state, {})

    async with TestSessionLocal() as db:
        plans = (await db.execute(
            select(ResearchPlanORM).where(ResearchPlanORM.run_id == run.id)
        )).scalars().all()
        tasks = (await db.execute(
            select(ResearchTaskORM).where(ResearchTaskORM.run_id == run.id)
        )).scalars().all()

    assert len(plans) == 1
    assert len(tasks) == 3


@pytest.mark.asyncio
async def test_pa003_planning_node_retries_on_invalid_json():
    """PA-003: planning_node retries once on invalid LLM JSON."""
    from app.agents.planner import planning_node

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    state = _make_state(run_id=run.id)

    # First call returns invalid JSON; second call returns valid plan
    valid_json = _make_valid_plan_json(2)
    call_count = 0

    async def side_effect(system_prompt, user_prompt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "this is not valid json {"
        return valid_json

    mock_llm = MockLLMProvider()
    mock_llm.complete = side_effect

    with patch("app.agents.planner.get_llm_provider") as mock_llm_factory, \
         patch("app.agents.planner.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_factory.return_value = mock_llm
        result = await planning_node(state, {})

    assert result.get("workflow_status") == "researching"
    assert call_count == 2


@pytest.mark.asyncio
async def test_pa004_planning_node_fails_after_two_bad_responses():
    """PA-004: planning_node returns workflow_status=failed if both attempts fail."""
    from app.agents.planner import planning_node

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    state = _make_state(run_id=run.id)

    with patch("app.agents.planner.get_llm_provider") as mock_llm_factory, \
         patch("app.agents.planner.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_factory.return_value = MockLLMProvider(response='{"invalid": true}')
        result = await planning_node(state, {})

    assert result.get("workflow_status") == "failed"
    assert result.get("error_message") is not None


@pytest.mark.asyncio
async def test_pa005_planning_node_deduplicates_tasks():
    """PA-005: duplicate task objectives are removed."""
    from app.agents.planner import planning_node

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    state = _make_state(run_id=run.id)

    # Plan with 2 tasks but identical objectives
    task_id_1, task_id_2, task_id_3 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    dup_plan_json = json.dumps({
        "plan_id": str(uuid.uuid4()),
        "objectives": ["Objective A"],
        "tasks": [
            {"task_id": task_id_1, "objective": "Investigate lithium toxicity", "search_query": "q1", "expected_evidence_type": "papers", "priority": 1},
            {"task_id": task_id_2, "objective": "Investigate lithium toxicity", "search_query": "q2", "expected_evidence_type": "papers", "priority": 2},  # duplicate
            {"task_id": task_id_3, "objective": "Assess water usage", "search_query": "q3", "expected_evidence_type": "stats", "priority": 1},
        ],
        "refinement_notes": None,
    })

    with patch("app.agents.planner.get_llm_provider") as mock_llm_factory, \
         patch("app.agents.planner.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_factory.return_value = MockLLMProvider(response=dup_plan_json)
        result = await planning_node(state, {})

    # Should have 2 unique tasks (duplicate removed)
    assert len(result.get("research_tasks", [])) == 2


@pytest.mark.asyncio
async def test_pa006_planning_node_task_count_too_low_retries():
    """PA-006: task count below 2 triggers retry."""
    from app.agents.planner import planning_node

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    state = _make_state(run_id=run.id)

    one_task_json = json.dumps({
        "plan_id": str(uuid.uuid4()),
        "objectives": ["Obj"],
        "tasks": [
            {"task_id": str(uuid.uuid4()), "objective": "Only task", "search_query": "q", "expected_evidence_type": "papers", "priority": 1}
        ],
        "refinement_notes": None,
    })
    valid_json = _make_valid_plan_json(2)

    call_count = 0

    async def side_effect(system_prompt, user_prompt):
        nonlocal call_count
        call_count += 1
        return one_task_json if call_count == 1 else valid_json

    mock_llm = MockLLMProvider()
    mock_llm.complete = side_effect

    with patch("app.agents.planner.get_llm_provider") as mock_llm_factory, \
         patch("app.agents.planner.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_factory.return_value = mock_llm
        result = await planning_node(state, {})

    assert call_count == 2
    assert result.get("workflow_status") == "researching"


@pytest.mark.asyncio
async def test_pa007_planning_node_tasks_sorted_by_priority():
    """PA-007: pending_task_ids are sorted by priority ascending."""
    from app.agents.planner import planning_node

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    state = _make_state(run_id=run.id)

    unsorted_plan = json.dumps({
        "plan_id": str(uuid.uuid4()),
        "objectives": ["Obj"],
        "tasks": [
            {"task_id": "t3", "objective": "Low priority task", "search_query": "q3", "expected_evidence_type": "news", "priority": 3},
            {"task_id": "t1", "objective": "High priority task", "search_query": "q1", "expected_evidence_type": "papers", "priority": 1},
            {"task_id": "t2", "objective": "Medium priority task", "search_query": "q2", "expected_evidence_type": "stats", "priority": 2},
        ],
        "refinement_notes": None,
    })

    with patch("app.agents.planner.get_llm_provider") as mock_llm_factory, \
         patch("app.agents.planner.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_factory.return_value = MockLLMProvider(response=unsorted_plan)
        result = await planning_node(state, {})

    assert result["pending_task_ids"] == ["t1", "t2", "t3"]


@pytest.mark.asyncio
async def test_pa008_planning_node_refinement_uses_existing_plan():
    """PA-008: when existing_plan is set, user prompt includes refinement instructions."""
    from app.agents.planner import planning_node

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    existing_plan = {"plan_id": str(uuid.uuid4()), "objectives": ["Existing obj"], "tasks": [], "refinement_notes": None}
    state = _make_state(
        run_id=run.id,
        research_plan=existing_plan,
        revision_notes="Add tasks about water pollution.",
    )

    captured_prompts = []

    async def capture_complete(system_prompt, user_prompt):
        captured_prompts.append(user_prompt)
        return _make_valid_plan_json(2)

    mock_llm = MockLLMProvider()
    mock_llm.complete = capture_complete

    with patch("app.agents.planner.get_llm_provider") as mock_llm_factory, \
         patch("app.agents.planner.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_factory.return_value = mock_llm
        await planning_node(state, {})

    assert len(captured_prompts) == 1
    assert "Refine" in captured_prompts[0] or "revision" in captured_prompts[0].lower()
    assert "water pollution" in captured_prompts[0]


# ── Research Agent Tests (RA-001 through RA-009) ───────────────────────────────

def _make_task_state(run_id: str, task_id: str = None) -> ResearchWorkflowState:
    """State with a single pending task assigned to current_task_id."""
    if task_id is None:
        task_id = str(uuid.uuid4())
    return _make_state(
        run_id=run_id,
        current_task_id=task_id,
        research_tasks=[{
            "task_id": task_id,
            "objective": "Investigate lithium mining water usage",
            "search_query": "lithium mining water consumption statistics",
            "expected_evidence_type": "statistics",
            "priority": 1,
        }],
        pending_task_ids=[task_id],
        workflow_status="researching",
    )


@pytest.mark.asyncio
async def test_ra001_research_node_completes_task():
    """RA-001: research_node returns completed TaskResult with evidence."""
    from app.agents.researcher import research_node

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    task_id = str(uuid.uuid4())
    state = _make_task_state(run.id, task_id)

    with patch("app.agents.researcher.get_llm_provider") as mock_llm_fac, \
         patch("app.agents.researcher.get_search_provider") as mock_search_fac, \
         patch("app.agents.researcher.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_fac.return_value = MockLLMProvider(response="Evidence shows high water usage in mining regions.")
        mock_search_fac.return_value = MockWebSearchProvider()
        result = await research_node(state, {})

    assert task_id in result.get("completed_task_ids", [])
    assert task_id in result.get("task_results", {})
    task_result = result["task_results"][task_id]
    assert task_result["status"] in ("completed", "partial")
    assert task_result["evidence_count"] > 0


@pytest.mark.asyncio
async def test_ra002_research_node_persists_evidence_with_task_id():
    """RA-002: EvidenceRecord rows have task_id FK set."""
    from app.agents.researcher import research_node
    from app.models.evidence import EvidenceRecord
    from sqlalchemy import select

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    task_id = str(uuid.uuid4())
    state = _make_task_state(run.id, task_id)

    with patch("app.agents.researcher.get_llm_provider") as mock_llm_fac, \
         patch("app.agents.researcher.get_search_provider") as mock_search_fac, \
         patch("app.agents.researcher.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_fac.return_value = MockLLMProvider(response="Findings summary.")
        mock_search_fac.return_value = MockWebSearchProvider()
        await research_node(state, {})

    async with TestSessionLocal() as db:
        ev_result = await db.execute(
            select(EvidenceRecord).where(EvidenceRecord.run_id == run.id)
        )
        records = ev_result.scalars().all()

    assert len(records) > 0
    for record in records:
        assert record.task_id == task_id


@pytest.mark.asyncio
async def test_ra003_research_node_removes_task_from_pending():
    """RA-003: executed task_id is removed from pending_task_ids."""
    from app.agents.researcher import research_node

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    task_id = str(uuid.uuid4())
    state = _make_task_state(run.id, task_id)

    with patch("app.agents.researcher.get_llm_provider") as mock_llm_fac, \
         patch("app.agents.researcher.get_search_provider") as mock_search_fac, \
         patch("app.agents.researcher.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_fac.return_value = MockLLMProvider(response="Summary.")
        mock_search_fac.return_value = MockWebSearchProvider()
        result = await research_node(state, {})

    assert task_id not in result.get("pending_task_ids", [])
    assert result.get("current_task_id") is None


@pytest.mark.asyncio
async def test_ra004_research_node_web_search_failure_returns_failed_task():
    """RA-004: web search failure → status=failed, workflow not set to failed."""
    from app.agents.researcher import research_node

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    task_id = str(uuid.uuid4())
    state = _make_task_state(run.id, task_id)

    with patch("app.agents.researcher.get_llm_provider") as mock_llm_fac, \
         patch("app.agents.researcher.get_search_provider") as mock_search_fac, \
         patch("app.agents.researcher.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_fac.return_value = MockLLMProvider(response="Summary.")
        mock_search_fac.return_value = MockWebSearchProvider(fail=True)
        result = await research_node(state, {})

    task_result = result.get("task_results", {}).get(task_id, {})
    assert task_result.get("status") == "failed"
    # Workflow should NOT be set to failed from this
    assert result.get("workflow_status") != "failed"


@pytest.mark.asyncio
async def test_ra005_research_node_llm_failure_returns_partial():
    """RA-005: LLM synthesis failure → status=partial (evidence still collected)."""
    from app.agents.researcher import research_node

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    task_id = str(uuid.uuid4())
    state = _make_task_state(run.id, task_id)

    with patch("app.agents.researcher.get_llm_provider") as mock_llm_fac, \
         patch("app.agents.researcher.get_search_provider") as mock_search_fac, \
         patch("app.agents.researcher.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_fac.return_value = MockLLMProvider(fail=True)
        mock_search_fac.return_value = MockWebSearchProvider()
        result = await research_node(state, {})

    task_result = result.get("task_results", {}).get(task_id, {})
    assert task_result.get("status") == "partial"
    assert task_result.get("evidence_count", 0) > 0


@pytest.mark.asyncio
async def test_ra006_research_node_no_current_task_returns_failed():
    """RA-006: research_node called with no task assigned returns workflow_status=failed."""
    from app.agents.researcher import research_node

    state = _make_state(
        run_id=str(uuid.uuid4()),
        current_task_id=None,
        pending_task_ids=[],
        workflow_status="researching",
    )

    result = await research_node(state, {})
    assert result.get("workflow_status") == "failed"


@pytest.mark.asyncio
async def test_ra007_research_node_appends_to_collected_evidence_ids():
    """RA-007: collected_evidence_ids in return contains the new IDs."""
    from app.agents.researcher import research_node

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    task_id = str(uuid.uuid4())
    state = _make_task_state(run.id, task_id)

    with patch("app.agents.researcher.get_llm_provider") as mock_llm_fac, \
         patch("app.agents.researcher.get_search_provider") as mock_search_fac, \
         patch("app.agents.researcher.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_fac.return_value = MockLLMProvider(response="Summary.")
        mock_search_fac.return_value = MockWebSearchProvider()
        result = await research_node(state, {})

    assert len(result.get("collected_evidence_ids", [])) > 0


@pytest.mark.asyncio
async def test_ra008_research_node_deduplicates_evidence():
    """RA-008: duplicate URLs are not inserted as separate evidence records."""
    from app.agents.researcher import research_node
    from app.models.evidence import EvidenceRecord
    from sqlalchemy import select

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    task_id = str(uuid.uuid4())
    state = _make_task_state(run.id, task_id)

    # Return 3 results where 2 share the same URL
    dup_results = [
        SearchResult(url="https://example.com/same", title="Same", snippet="", content="Content A" * 20),
        SearchResult(url="https://example.com/same", title="Same Dup", snippet="", content="Content B" * 20),
        SearchResult(url="https://example.com/unique", title="Unique", snippet="", content="Content C" * 20),
    ]

    with patch("app.agents.researcher.get_llm_provider") as mock_llm_fac, \
         patch("app.agents.researcher.get_search_provider") as mock_search_fac, \
         patch("app.agents.researcher.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_fac.return_value = MockLLMProvider(response="Summary.")
        mock_search_fac.return_value = MockWebSearchProvider(results=dup_results)
        result = await research_node(state, {})

    # Should only have 2 unique evidence records (not 3)
    evidence_ids = result.get("collected_evidence_ids", [])
    assert len(evidence_ids) == 2


@pytest.mark.asyncio
async def test_ra009_research_node_task_status_updated_in_db():
    """RA-009: ResearchTask.status updated to 'completed' or 'partial' in DB."""
    from app.agents.researcher import research_node
    from app.models.task import ResearchTask as ResearchTaskORM
    from app.services.plan_service import save_plan
    from app.schemas.plan import ResearchPlan, ResearchTask
    from sqlalchemy import select

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)
        # Create a real task in DB
        task_id = str(uuid.uuid4())
        plan = ResearchPlan(
            plan_id=str(uuid.uuid4()),
            objectives=["Investigate"],
            tasks=[
                ResearchTask(
                    task_id=task_id,
                    objective="Investigate water usage",
                    search_query="lithium water",
                    expected_evidence_type="stats",
                    priority=1,
                ),
                ResearchTask(
                    task_id=str(uuid.uuid4()),
                    objective="Investigate soil degradation",
                    search_query="lithium mining soil",
                    expected_evidence_type="papers",
                    priority=2,
                ),
            ],
        )
        await save_plan(db, run.id, plan)
        await db.commit()

    state = _make_task_state(run.id, task_id)

    with patch("app.agents.researcher.get_llm_provider") as mock_llm_fac, \
         patch("app.agents.researcher.get_search_provider") as mock_search_fac, \
         patch("app.agents.researcher.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_fac.return_value = MockLLMProvider(response="Summary.")
        mock_search_fac.return_value = MockWebSearchProvider()
        await research_node(state, {})

    async with TestSessionLocal() as db:
        task_result = await db.execute(
            select(ResearchTaskORM).where(ResearchTaskORM.id == task_id)
        )
        task = task_result.scalar_one_or_none()

    assert task is not None
    assert task.status in ("completed", "partial")
    assert task.evidence_count > 0


# ── Supervisor Agent Tests (SA-001 through SA-009) ─────────────────────────────

def _make_supervisor_decision_json(decision: str, next_task_id: str | None = None, revision_notes: str | None = None) -> str:
    return json.dumps({
        "decision": decision,
        "reasoning": "Test reasoning",
        "revision_notes": revision_notes,
        "next_task_id": next_task_id,
    })


@pytest.mark.asyncio
async def test_sa001_supervisor_requests_plan_when_none_exists():
    """SA-001: supervisor returns request_plan when research_plan is None."""
    from app.agents.supervisor import supervisor_node

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    state = _make_state(run_id=run.id, research_plan=None, iteration_count=0)

    with patch("app.agents.supervisor.get_llm_provider") as mock_llm_fac, \
         patch("app.agents.supervisor.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_fac.return_value = MockLLMProvider(
            response=_make_supervisor_decision_json("request_plan")
        )
        result = await supervisor_node(state, {})

    assert result["supervisor_decision"] == "request_plan"
    assert result["iteration_count"] == 1


@pytest.mark.asyncio
async def test_sa002_supervisor_forces_completion_at_max_iterations():
    """SA-002: at iteration_count >= max_supervisor_cycles, forces complete_research without LLM call."""
    from app.agents.supervisor import supervisor_node

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    state = _make_state(run_id=run.id, iteration_count=3, max_supervisor_cycles=3)

    llm_called = False

    async def should_not_be_called(system_prompt, user_prompt):
        nonlocal llm_called
        llm_called = True
        return _make_supervisor_decision_json("fail_workflow")

    mock_llm = MockLLMProvider()
    mock_llm.complete = should_not_be_called

    with patch("app.agents.supervisor.get_llm_provider") as mock_llm_fac, \
         patch("app.agents.supervisor.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_fac.return_value = mock_llm
        result = await supervisor_node(state, {})

    assert result["supervisor_decision"] == "complete_research"
    assert not llm_called


@pytest.mark.asyncio
async def test_sa003_supervisor_execute_next_task_with_valid_task_id():
    """SA-003: execute_next_task with valid next_task_id assigns current_task_id."""
    from app.agents.supervisor import supervisor_node

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    task_id = str(uuid.uuid4())
    state = _make_state(
        run_id=run.id,
        pending_task_ids=[task_id],
        research_tasks=[{"task_id": task_id, "objective": "Obj", "search_query": "q", "expected_evidence_type": "papers", "priority": 1}],
        iteration_count=0,
    )

    with patch("app.agents.supervisor.get_llm_provider") as mock_llm_fac, \
         patch("app.agents.supervisor.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_fac.return_value = MockLLMProvider(
            response=_make_supervisor_decision_json("execute_next_task", next_task_id=task_id)
        )
        result = await supervisor_node(state, {})

    assert result["supervisor_decision"] == "execute_next_task"
    assert result["current_task_id"] == task_id


@pytest.mark.asyncio
async def test_sa004_supervisor_fallback_on_invalid_task_id():
    """SA-004: invalid next_task_id falls back to first pending task."""
    from app.agents.supervisor import supervisor_node

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    real_task_id = str(uuid.uuid4())
    state = _make_state(
        run_id=run.id,
        pending_task_ids=[real_task_id],
        research_tasks=[{"task_id": real_task_id, "objective": "Obj", "search_query": "q", "expected_evidence_type": "papers", "priority": 1}],
        iteration_count=0,
    )

    with patch("app.agents.supervisor.get_llm_provider") as mock_llm_fac, \
         patch("app.agents.supervisor.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_fac.return_value = MockLLMProvider(
            response=_make_supervisor_decision_json("execute_next_task", next_task_id="non-existent-id")
        )
        result = await supervisor_node(state, {})

    assert result["current_task_id"] == real_task_id


@pytest.mark.asyncio
async def test_sa005_supervisor_fallback_on_invalid_llm_json():
    """SA-005: invalid LLM JSON → fallback complete_research."""
    from app.agents.supervisor import supervisor_node

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    state = _make_state(run_id=run.id, iteration_count=0)

    with patch("app.agents.supervisor.get_llm_provider") as mock_llm_fac, \
         patch("app.agents.supervisor.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_fac.return_value = MockLLMProvider(response="This is not JSON at all!")
        result = await supervisor_node(state, {})

    assert result["supervisor_decision"] == "complete_research"


@pytest.mark.asyncio
async def test_sa006_supervisor_increments_iteration_count():
    """SA-006: iteration_count is incremented by 1 each call."""
    from app.agents.supervisor import supervisor_node

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    state = _make_state(run_id=run.id, iteration_count=1)

    with patch("app.agents.supervisor.get_llm_provider") as mock_llm_fac, \
         patch("app.agents.supervisor.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_fac.return_value = MockLLMProvider(
            response=_make_supervisor_decision_json("complete_research")
        )
        result = await supervisor_node(state, {})

    assert result["iteration_count"] == 2


@pytest.mark.asyncio
async def test_sa007_supervisor_complete_research_sets_finalizing():
    """SA-007: complete_research decision sets workflow_status=finalizing."""
    from app.agents.supervisor import supervisor_node

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    state = _make_state(run_id=run.id, iteration_count=0)

    with patch("app.agents.supervisor.get_llm_provider") as mock_llm_fac, \
         patch("app.agents.supervisor.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_fac.return_value = MockLLMProvider(
            response=_make_supervisor_decision_json("complete_research")
        )
        result = await supervisor_node(state, {})

    assert result["workflow_status"] == "finalizing"


@pytest.mark.asyncio
async def test_sa008_supervisor_continue_research_auto_assigns_next_task():
    """SA-008: continue_research auto-assigns first pending task via execute_next_task."""
    from app.agents.supervisor import supervisor_node

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    task_id = str(uuid.uuid4())
    state = _make_state(
        run_id=run.id,
        pending_task_ids=[task_id],
        research_tasks=[{"task_id": task_id, "objective": "Obj", "search_query": "q", "expected_evidence_type": "papers", "priority": 1}],
        iteration_count=0,
    )

    with patch("app.agents.supervisor.get_llm_provider") as mock_llm_fac, \
         patch("app.agents.supervisor.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_fac.return_value = MockLLMProvider(
            response=_make_supervisor_decision_json("continue_research")
        )
        result = await supervisor_node(state, {})

    # continue_research with pending tasks should be promoted to execute_next_task
    assert result["supervisor_decision"] == "execute_next_task"
    assert result["current_task_id"] == task_id


@pytest.mark.asyncio
async def test_sa009_supervisor_logs_event_to_db():
    """SA-009: supervisor_node writes an AgentExecutionEvent for each call."""
    from app.agents.supervisor import supervisor_node
    from app.models.event import AgentExecutionEvent
    from sqlalchemy import select

    async with TestSessionLocal() as db:
        run = await _create_run_in_db(db)

    state = _make_state(run_id=run.id, iteration_count=0)

    with patch("app.agents.supervisor.get_llm_provider") as mock_llm_fac, \
         patch("app.agents.supervisor.AsyncSessionLocal", new=TestSessionLocal):
        mock_llm_fac.return_value = MockLLMProvider(
            response=_make_supervisor_decision_json("complete_research")
        )
        await supervisor_node(state, {})

    async with TestSessionLocal() as db:
        events = (await db.execute(
            select(AgentExecutionEvent)
            .where(AgentExecutionEvent.run_id == run.id)
            .where(AgentExecutionEvent.agent_name == "supervisor")
        )).scalars().all()

    assert len(events) == 1
    assert events[0].event_type == "decision"
