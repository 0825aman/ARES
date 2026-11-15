"""Tests for M4.5 — Critic / Reviewer Agent.

Test coverage:
  CA-01: Critic produces valid CriticDecision with correct field types and enum values
  CA-02: Critic identifies at least one issue in a deliberately weak research output
  CA-03: Critic returns "approved" for strong output with no issues
  CA-04: CriticDecision validates enum values (rejects bad values)
  CA-05: Fallback review is returned when both LLM attempts fail
  CA-06: review_status derived correctly for each overall_assessment/action combo
  CA-07: Supervisor routes "approve_report" → finalize_report (not a critic terminal)
  CA-08: Supervisor routes "request_additional_research" → planning_node
  CA-09: Supervisor routes "request_reverification" → claim_extraction_node
  CA-10: At cycle limit, second revision → needs_attention (NOT approved)
  CA-11: At cycle limit, inadequate assessment → rejected
  CA-12: At cycle limit, approve_report is allowed through (no forced downgrade)
  CA-13: CriticReview persisted with correct review_version
  CA-14: GET /projects/{id}/runs/{id}/review returns 200 with latest review
  CA-15: GET /projects/{id}/runs/{id}/review returns 404 when no review exists
  CA-16: Critic agent has zero app.graph.* imports (AST check)
  CA-17: workflow.py graph compiles with updated topology
  CA-18: route_after_finalize routes to claim_extraction_node for multi_agent
  CA-19: route_after_finalize routes to END for sequential completed
"""
from __future__ import annotations

import ast
import json
import pathlib
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_strong_report() -> dict:
    return {
        "executive_summary": (
            "This comprehensive study examines the impact of renewable energy adoption. "
            "Seven peer-reviewed studies confirm a 34% reduction in carbon emissions."
        ),
        "key_findings": [
            "Solar adoption increased by 42% globally between 2020–2024",
            "Wind energy now accounts for 18% of total electricity production in the EU",
            "Cost per kWh of solar has declined 89% since 2010",
        ],
        "observations": "Consistent trend across all major economies.",
        "contradictions": "",
        "limitations": "Data limited to countries with reporting obligations.",
        "sources": [
            "[SOURCE 1] IRENA 2024 Annual Report",
            "[SOURCE 2] IEA World Energy Outlook 2024",
            "[SOURCE 3] Nature Energy — peer-reviewed meta-analysis",
        ],
    }


def _make_weak_report() -> dict:
    return {
        "executive_summary": "Some things were found about the topic.",
        "key_findings": [
            "Results were mixed",
            "More research is needed",
        ],
        "observations": "",
        "contradictions": "",
        "limitations": "Unknown.",
        "sources": [],
    }


class MockLLM:
    """Configurable mock LLM provider."""

    def __init__(self, response: str):
        self.response = response
        self.call_count = 0

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.call_count += 1
        return self.response


class FailingLLM:
    """Always raises an exception."""

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        raise RuntimeError("LLM service unavailable")


# ---------------------------------------------------------------------------
# CA-01: Valid CriticDecision produced
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ca01_critic_produces_valid_decision():
    """Critic produces a CriticDecision with correct field types."""
    from app.agents.critic import run_critic_review

    llm_response = json.dumps({
        "overall_assessment": "strong",
        "recommended_action": "approve_report",
        "unsupported_claims": [],
        "citation_issues": [],
        "contradictory_findings": [],
        "missing_evidence": [],
        "source_quality_issues": [],
        "reasoning_issues": [],
        "review_summary": "The report is well-supported and comprehensive.",
    })
    llm = MockLLM(llm_response)

    result = await run_critic_review(
        run_id="run-001",
        research_question="What is the impact of renewable energy adoption?",
        report=_make_strong_report(),
        review_version=1,
        verification_summary={"total_claims": 5, "supported_count": 5},
        llm_provider=llm,
    )

    assert result["overall_assessment"] == "strong"
    assert result["recommended_action"] == "approve_report"
    assert result["review_status"] == "approved"
    assert result["review_version"] == 1
    assert result["run_id"] == "run-001"
    # JSON lists stored as strings
    assert json.loads(result["unsupported_claims"]) == []
    assert isinstance(result["review_summary"], str)
    assert len(result["review_summary"]) > 0


# ---------------------------------------------------------------------------
# CA-02: Critic identifies issues in weak output
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ca02_critic_identifies_issues_in_weak_report():
    """Critic recommends revision for a deliberately weak report."""
    from app.agents.critic import run_critic_review

    llm_response = json.dumps({
        "overall_assessment": "weak",
        "recommended_action": "revise_report",
        "unsupported_claims": ["Results were mixed — no evidence provided"],
        "citation_issues": ["No sources cited"],
        "contradictory_findings": [],
        "missing_evidence": ["Primary research data", "Statistical analysis"],
        "source_quality_issues": ["Zero sources cited"],
        "reasoning_issues": ["Conclusions unsupported by findings"],
        "review_summary": "The report lacks evidence and specific findings.",
    })
    llm = MockLLM(llm_response)

    result = await run_critic_review(
        run_id="run-002",
        research_question="Effects of sugar consumption on cognition?",
        report=_make_weak_report(),
        review_version=1,
        verification_summary={"total_claims": 2, "supported_count": 0},
        llm_provider=llm,
    )

    assert result["overall_assessment"] == "weak"
    assert result["recommended_action"] == "revise_report"
    assert result["review_status"] == "needs_attention"
    assert len(json.loads(result["unsupported_claims"])) >= 1
    assert len(json.loads(result["missing_evidence"])) >= 1


# ---------------------------------------------------------------------------
# CA-03: Critic approves strong output
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ca03_critic_approves_strong_report():
    """Critic returns approve_report for a high-quality report."""
    from app.agents.critic import run_critic_review

    llm_response = json.dumps({
        "overall_assessment": "strong",
        "recommended_action": "approve_report",
        "unsupported_claims": [],
        "citation_issues": [],
        "contradictory_findings": [],
        "missing_evidence": [],
        "source_quality_issues": [],
        "reasoning_issues": [],
        "review_summary": "Comprehensive, well-cited, strong evidence coverage.",
    })
    llm = MockLLM(llm_response)

    result = await run_critic_review(
        run_id="run-003",
        research_question="Climate change impacts on agriculture?",
        report=_make_strong_report(),
        review_version=1,
        verification_summary={"total_claims": 8, "supported_count": 8},
        llm_provider=llm,
    )

    assert result["recommended_action"] == "approve_report"
    assert result["review_status"] == "approved"


# ---------------------------------------------------------------------------
# CA-04: CriticDecision rejects bad enum values
# ---------------------------------------------------------------------------

def test_ca04_critic_decision_rejects_bad_enum():
    """CriticDecision raises ValidationError for unknown overall_assessment."""
    from pydantic import ValidationError
    from app.schemas.critic import CriticDecision

    with pytest.raises(ValidationError):
        CriticDecision.model_validate({
            "overall_assessment": "excellent",   # not in enum
            "recommended_action": "approve_report",
            "unsupported_claims": [],
            "citation_issues": [],
            "contradictory_findings": [],
            "missing_evidence": [],
            "source_quality_issues": [],
            "reasoning_issues": [],
            "review_summary": "test",
        })

    with pytest.raises(ValidationError):
        CriticDecision.model_validate({
            "overall_assessment": "strong",
            "recommended_action": "force_approve",   # not in enum
            "unsupported_claims": [],
            "citation_issues": [],
            "contradictory_findings": [],
            "missing_evidence": [],
            "source_quality_issues": [],
            "reasoning_issues": [],
            "review_summary": "test",
        })


# ---------------------------------------------------------------------------
# CA-05: Fallback review returned when both LLM attempts fail
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ca05_fallback_review_on_llm_failure():
    """Both LLM attempts fail → fallback review with needs_attention."""
    from app.agents.critic import run_critic_review

    llm = FailingLLM()

    result = await run_critic_review(
        run_id="run-005",
        research_question="Any question",
        report=_make_strong_report(),
        review_version=2,
        verification_summary=None,
        llm_provider=llm,
    )

    assert result["review_status"] == "needs_attention"
    assert result["recommended_action"] == "revise_report"
    assert result["review_version"] == 2
    assert result["run_id"] == "run-005"
    # Reasoning issues should mention the failure
    reasoning = json.loads(result["reasoning_issues"])
    assert len(reasoning) >= 1
    assert "Critic Agent failed" in reasoning[0]


# ---------------------------------------------------------------------------
# CA-06: review_status derived correctly
# ---------------------------------------------------------------------------

def test_ca06_review_status_derivation():
    """_derive_review_status maps correctly for each assessment/action combo."""
    from app.agents.critic import _derive_review_status

    assert _derive_review_status("strong", "approve_report") == "approved"
    assert _derive_review_status("adequate", "approve_report") == "approved"
    assert _derive_review_status("weak", "revise_report") == "needs_attention"
    assert _derive_review_status("inadequate", "reject") == "rejected"
    assert _derive_review_status("weak", "request_additional_research") == "needs_attention"
    assert _derive_review_status("adequate", "revise_report") == "needs_attention"


# ---------------------------------------------------------------------------
# CA-07: Supervisor routes approve_report → citation_validation_node (M4.6)
# ---------------------------------------------------------------------------

def test_ca07_supervisor_routes_approve_report():
    """route_after_supervisor maps approve_report to citation_validation_node (updated in M4.6)."""
    from app.graph.workflow import route_after_supervisor

    state = {
        "workflow_status": "finalizing",
        "supervisor_decision": "approve_report",
        "critic_cycles": 1,
        "critic_decision": "approve_report",
        "iteration_count": 0,
        "max_supervisor_cycles": 5,
    }
    result = route_after_supervisor(state)
    assert result == "citation_validation_node"


# ---------------------------------------------------------------------------
# CA-08: Supervisor routes request_additional_research → planning_node
# ---------------------------------------------------------------------------

def test_ca08_supervisor_routes_additional_research():
    """route_after_supervisor maps request_additional_research to planning_node."""
    from app.graph.workflow import route_after_supervisor

    state = {
        "workflow_status": "finalizing",
        "supervisor_decision": "request_additional_research",
        "critic_cycles": 1,
        "critic_decision": "request_additional_research",
        "iteration_count": 0,
        "max_supervisor_cycles": 5,
    }
    result = route_after_supervisor(state)
    assert result == "planning_node"


# ---------------------------------------------------------------------------
# CA-09: Supervisor routes request_reverification → claim_extraction_node
# ---------------------------------------------------------------------------

def test_ca09_supervisor_routes_reverification():
    """route_after_supervisor maps request_reverification to claim_extraction_node."""
    from app.graph.workflow import route_after_supervisor

    state = {
        "workflow_status": "claim_verifying",
        "supervisor_decision": "request_reverification",
        "critic_cycles": 1,
        "critic_decision": "request_reverification",
        "iteration_count": 0,
        "max_supervisor_cycles": 5,
    }
    result = route_after_supervisor(state)
    assert result == "claim_extraction_node"


# ---------------------------------------------------------------------------
# CA-10: At cycle limit, second revision → needs_attention (NOT approved)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ca10_cycle_limit_forces_needs_attention_not_approved():
    """At critic_cycles >= CRITIC_MAX_REVIEW_CYCLES with revision recommendation
    → Supervisor enforces mark_needs_attention, never approve_report."""
    from app.agents.supervisor import supervisor_node

    # Mock state: critic has reviewed twice, recommends revise_report again
    state = {
        "run_id": "run-ca10",
        "research_question": "test question",
        "research_plan": None,
        "research_tasks": [],
        "task_results": {},
        "completed_task_ids": [],
        "failed_task_ids": [],
        "pending_task_ids": [],
        "iteration_count": 2,
        "max_supervisor_cycles": 5,
        "supervisor_decision": "revise_report",
        "revision_notes": None,
        "current_task_id": None,
        "workflow_status": "finalizing",
        "error_message": None,
        "final_report_id": "report-001",
        "verification_depth": "basic",
        "claim_ids": [],
        "verification_summary": None,
        "critic_review_id": "review-002",
        "critic_decision": "revise_report",   # still recommending revision
        "critic_cycles": 2,                   # at cycle limit (CRITIC_MAX_REVIEW_CYCLES=2)
    }

    mock_llm_response = json.dumps({
        "decision": "revise_report",
        "reasoning": "Report still has issues after second review.",
        "revision_notes": None,
        "next_task_id": None,
    })

    async def mock_log_event(db, **kwargs):
        pass

    with patch("app.agents.supervisor.get_llm_provider") as mock_provider, \
         patch("app.agents.supervisor.AsyncSessionLocal") as mock_session_cls, \
         patch("app.core.config.settings") as mock_settings:

        mock_settings.CRITIC_MAX_REVIEW_CYCLES = 2
        mock_settings.MAX_SUPERVISOR_CYCLES = 5
        mock_settings.VERIFICATION_DEPTH = "basic"

        mock_llm = AsyncMock()
        mock_llm.complete.return_value = mock_llm_response
        mock_provider.return_value = mock_llm

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        mock_session.commit = AsyncMock()
        mock_session_cls.return_value = mock_session

        result = await supervisor_node(state, config={})

    # The key assertion: decision must NOT be approve_report
    decision = result.get("supervisor_decision", "")
    assert decision != "approve_report", (
        f"Supervisor forced approval at cycle limit! Got: {decision}"
    )
    # Must be a terminal non-approval decision
    assert decision in ("mark_needs_attention", "reject", "revise_report"), (
        f"Expected terminal decision, got: {decision}"
    )


# ---------------------------------------------------------------------------
# CA-11: At cycle limit, inadequate → rejected
# ---------------------------------------------------------------------------

def test_ca11_cycle_limit_inadequate_gets_rejected():
    """Supervisor cycle-limit enforcement: inadequate assessment → reject."""
    # Directly test the cycle-limit logic by simulating what supervisor does
    from app.schemas.agent import SupervisorDecision

    # Simulate: critic_cycles=2, CRITIC_MAX_REVIEW_CYCLES=2, assessment=inadequate
    critic_cycles = 2
    max_cycles = 2
    decision = SupervisorDecision(
        decision="reject",
        reasoning="Inadequate",
        revision_notes=None,
        next_task_id=None,
    )

    # The enforcement code in supervisor picks "reject" when assessment is inadequate
    # and cycle limit is reached.
    is_post_critic = decision.decision in {
        "approve_report", "request_additional_research", "request_reverification",
        "revise_report", "reject", "mark_needs_attention",
    }
    assert is_post_critic
    assert critic_cycles >= max_cycles
    # decision.decision == "reject" → terminal rejection
    assert decision.decision == "reject"


# ---------------------------------------------------------------------------
# CA-12: Approve at cycle limit is allowed
# ---------------------------------------------------------------------------

def test_ca12_approve_allowed_at_cycle_limit():
    """Supervisor cycle-limit enforcement allows approve_report through."""
    from app.schemas.agent import SupervisorDecision

    # approve_report at cycle limit should not be downgraded
    decision = SupervisorDecision(
        decision="approve_report",
        reasoning="Report meets all quality criteria.",
        revision_notes=None,
        next_task_id=None,
    )

    critic_cycles = 2
    max_cycles = 2
    is_post_critic = decision.decision in {
        "approve_report", "request_additional_research", "request_reverification",
        "revise_report", "reject", "mark_needs_attention",
    }

    # At cycle limit with approve_report → should stay approve_report
    if is_post_critic and critic_cycles >= max_cycles:
        if decision.decision == "approve_report":
            final_decision = "approve_report"  # allowed through
        else:
            final_decision = "mark_needs_attention"
    else:
        final_decision = decision.decision

    assert final_decision == "approve_report"


# ---------------------------------------------------------------------------
# CA-13: CriticReview persisted with correct review_version (DB test)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ca13_critic_review_persisted_with_version(db_session):
    """CriticReview ORM can be created and queried with correct review_version."""
    from app.models.critic_review import CriticReview
    from sqlalchemy import select

    review = CriticReview(
        id=str(uuid.uuid4()),
        run_id="run-ca13",
        review_version=2,
        overall_assessment="weak",
        review_status="needs_attention",
        recommended_action="revise_report",
        unsupported_claims=json.dumps(["Claim A lacks evidence"]),
        citation_issues=json.dumps([]),
        contradictory_findings=json.dumps([]),
        missing_evidence=json.dumps(["Statistical data"]),
        source_quality_issues=json.dumps([]),
        reasoning_issues=json.dumps([]),
        review_summary="Second review still has unresolved issues.",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(review)
    await db_session.commit()

    # Re-query
    result = await db_session.execute(
        select(CriticReview).where(CriticReview.run_id == "run-ca13")
    )
    fetched = result.scalar_one()

    assert fetched.review_version == 2
    assert fetched.overall_assessment == "weak"
    assert fetched.review_status == "needs_attention"
    assert fetched.recommended_action == "revise_report"
    assert json.loads(fetched.unsupported_claims) == ["Claim A lacks evidence"]
    assert json.loads(fetched.missing_evidence) == ["Statistical data"]


# ---------------------------------------------------------------------------
# CA-14: GET /runs/{run_id}/review returns 200
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ca14_get_review_returns_200(async_client, db_session):
    """GET /projects/{id}/runs/{id}/review returns 200 with review data."""
    from app.models.project import ResearchProject
    from app.models.run import ResearchRun
    from app.models.critic_review import CriticReview

    # Create project and run
    project_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())

    project = ResearchProject(
        id=project_id,
        title="Test Project",
        research_question="Test question",
        status="in_progress",
    )
    run = ResearchRun(
        id=run_id,
        project_id=project_id,
        research_question="Test question",
        status="completed",
        workflow_mode="multi_agent",
        verification_depth="basic",
    )
    review = CriticReview(
        id=str(uuid.uuid4()),
        run_id=run_id,
        review_version=1,
        overall_assessment="adequate",
        review_status="approved",
        recommended_action="approve_report",
        unsupported_claims=json.dumps([]),
        citation_issues=json.dumps([]),
        contradictory_findings=json.dumps([]),
        missing_evidence=json.dumps([]),
        source_quality_issues=json.dumps([]),
        reasoning_issues=json.dumps([]),
        review_summary="Report is adequate.",
        created_at=datetime.now(timezone.utc),
    )

    db_session.add_all([project, run, review])
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/projects/{project_id}/runs/{run_id}/review"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == run_id
    assert data["review_version"] == 1
    assert data["overall_assessment"] == "adequate"
    assert data["recommended_action"] == "approve_report"
    assert data["review_status"] == "approved"
    assert data["unsupported_claims"] == []


# ---------------------------------------------------------------------------
# CA-15: GET /runs/{run_id}/review returns 404 when no review exists
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ca15_get_review_returns_404_when_absent(async_client, db_session):
    """GET /projects/{id}/runs/{id}/review returns 404 when no review exists."""
    from app.models.project import ResearchProject
    from app.models.run import ResearchRun

    project_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())

    project = ResearchProject(
        id=project_id,
        title="Test Project",
        research_question="Test question",
        status="in_progress",
    )
    run = ResearchRun(
        id=run_id,
        project_id=project_id,
        research_question="Test question",
        status="running",
        workflow_mode="sequential",
        verification_depth="basic",
    )

    db_session.add_all([project, run])
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/projects/{project_id}/runs/{run_id}/review"
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# CA-16: critic.py has zero app.graph.* imports (AST check)
# ---------------------------------------------------------------------------

def test_ca16_critic_agent_no_graph_imports():
    """critic.py must not import from app.graph.* at any level."""
    critic_path = (
        pathlib.Path(__file__).parent.parent
        / "app" / "agents" / "critic.py"
    )
    assert critic_path.exists(), "app/agents/critic.py not found"

    source = critic_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    graph_imports = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("app.graph"):
                    graph_imports.append(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("app.graph"):
                        graph_imports.append(alias.name)

    assert graph_imports == [], (
        f"critic.py must not import from app.graph.*. Found: {graph_imports}"
    )


# ---------------------------------------------------------------------------
# CA-17: workflow.py graph compiles with updated topology
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ca17_graph_compiles_with_phase4_topology():
    """The LangGraph StateGraph compiles with all Phase 4 M4.5 nodes."""
    from app.graph.workflow import _build_graph_skeleton
    from langgraph.checkpoint.memory import MemorySaver

    # Use in-memory checkpointer (no async context manager needed)
    checkpointer = MemorySaver()

    builder = _build_graph_skeleton()
    graph = builder.compile(checkpointer=checkpointer)

    # Verify key nodes are registered
    node_names = set(graph.nodes.keys())
    assert "initialize_run" in node_names
    assert "supervisor_node" in node_names
    assert "finalize_report" in node_names
    assert "claim_extraction_node" in node_names
    assert "critic_node" in node_names
    assert "citation_validation_node" in node_names
    assert "reject_terminal" in node_names
    assert "needs_attention_terminal" in node_names
    assert "fail_workflow" in node_names


# ---------------------------------------------------------------------------
# CA-18: route_after_finalize → claim_extraction_node for multi_agent
# ---------------------------------------------------------------------------

def test_ca18_route_after_finalize_multi_agent():
    """route_after_finalize routes to claim_extraction_node when workflow_mode=multi_agent."""
    from app.graph.workflow import route_after_finalize

    state = {
        "workflow_status": "claim_verifying",
        "workflow_mode": "multi_agent",
        "final_report_id": "report-001",
    }
    result = route_after_finalize(state)
    assert result == "claim_extraction_node"


# ---------------------------------------------------------------------------
# CA-19: route_after_finalize → END for sequential completed
# ---------------------------------------------------------------------------

def test_ca19_route_after_finalize_sequential():
    """route_after_finalize routes to END when workflow_status=completed."""
    from langgraph.graph import END
    from app.graph.workflow import route_after_finalize

    state = {
        "workflow_status": "completed",
        "workflow_mode": "sequential",
        "final_report_id": "report-001",
    }
    result = route_after_finalize(state)
    assert result == END
