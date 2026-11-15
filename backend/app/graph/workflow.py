"""LangGraph StateGraph construction and compilation.

The graph is compiled once at module level (singleton pattern).

Graph topology (Phase 4 M4.5):
  START → initialize_run → supervisor_node
  planning_node → supervisor_node
  supervisor_node --route_after_supervisor-->
    planning_node | research_node | finalize_report |
    claim_extraction_node | reject_terminal | needs_attention_terminal | fail_workflow
  research_node --route_after_research--> supervisor_node | fail_workflow
  finalize_report --route_after_finalize--> claim_extraction_node (multi-agent) | END (sequential)
  claim_extraction_node → critic_node
  critic_node → supervisor_node
  reject_terminal → END
  needs_attention_terminal → END
  fail_workflow → END
"""
from __future__ import annotations

import logging

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END

from app.graph.state import ResearchWorkflowState
from app.graph.checkpointer import get_checkpointer

logger = logging.getLogger(__name__)


# ── Routing functions ──────────────────────────────────────────────────────────

def route_after_supervisor(state: ResearchWorkflowState) -> str:
    """Conditional edge from supervisor_node.

    Handles both Phase 3 research decisions and Phase 4 critic decisions.
    """
    # Detect if a node set the workflow to failed (e.g. LLM crash)
    if state.get("workflow_status") == "failed":
        return "fail_workflow"

    decision = state.get("supervisor_decision", "")

    # Phase 3 decisions
    if decision in ("request_plan", "revise_plan"):
        return "planning_node"

    if decision in ("execute_next_task", "continue_research"):
        return "research_node"

    if decision == "complete_research":
        return "finalize_report"

    if decision == "fail_workflow":
        return "fail_workflow"

    # Phase 4 M4.5 critic decisions
    if decision == "approve_report":
        return "citation_validation_node"

    if decision == "request_additional_research":
        return "planning_node"

    if decision == "request_reverification":
        return "claim_extraction_node"

    if decision == "revise_report":
        return "finalize_report"

    if decision == "reject":
        return "reject_terminal"

    if decision == "mark_needs_attention":
        return "needs_attention_terminal"

    # Safe default — should not occur with a well-behaved Supervisor
    logger.warning(
        "route_after_supervisor: unrecognised decision %r, routing to finalize_report",
        decision,
    )
    return "finalize_report"


def route_after_research(state: ResearchWorkflowState) -> str:
    """Conditional edge from research_node.

    Only routes to fail_workflow when the task encountered a *fatal* error
    (e.g. DB unavailable).  Normal task failures are handled by the Supervisor.
    """
    if state.get("workflow_status") == "failed":
        return "fail_workflow"

    completed_ids = state.get("completed_task_ids", [])
    if not completed_ids:
        # research_node should always append a task_id; if it didn't, treat as fatal
        return "fail_workflow"

    latest_task_id = completed_ids[-1]
    task_result = state.get("task_results", {}).get(latest_task_id, {})

    if task_result.get("status") == "fatal_error":
        return "fail_workflow"

    return "supervisor_node"


def route_after_finalize(state: ResearchWorkflowState) -> str:
    """Conditional edge from finalize_report_node.

    Multi-agent runs: routes to claim_extraction_node (workflow_status=="claim_verifying").
    Sequential runs: workflow_status=="completed" → END.
    """
    if state.get("workflow_status") == "failed":
        return "fail_workflow"

    if state.get("workflow_status") == "claim_verifying":
        return "claim_extraction_node"

    # Sequential completed or any other status → END
    return END


# ── Stub nodes (replaced in M4–M6) ────────────────────────────────────────────

async def _stub_initialize_run(state: ResearchWorkflowState, config: RunnableConfig) -> dict:
    """Stub — replaced by initialize_run_node in M6."""
    return {"workflow_status": "planning"}


async def _stub_supervisor_node(state: ResearchWorkflowState, config: RunnableConfig) -> dict:
    """Stub — replaced by supervisor_node in M6."""
    return {
        "supervisor_decision": "complete_research",
        "reasoning": "stub",
        "iteration_count": state.get("iteration_count", 0) + 1,
        "workflow_status": "finalizing",
    }


async def _stub_planning_node(state: ResearchWorkflowState, config: RunnableConfig) -> dict:
    """Stub — replaced by planning_node in M4."""
    return {"workflow_status": "researching"}


async def _stub_research_node(state: ResearchWorkflowState, config: RunnableConfig) -> dict:
    """Stub — replaced by research_node in M5."""
    return {"workflow_status": "researching"}


async def _stub_finalize_report(state: ResearchWorkflowState, config: RunnableConfig) -> dict:
    """Stub — replaced by finalize_report_node in M6."""
    return {"workflow_status": "completed"}


async def _stub_fail_workflow(state: ResearchWorkflowState, config: RunnableConfig) -> dict:
    """Stub — replaced by fail_workflow_node in M6."""
    return {"workflow_status": "failed"}


# ── Terminal nodes for Phase 4 critic decisions ────────────────────────────────

async def _reject_terminal_node(
    state: ResearchWorkflowState,
    config: RunnableConfig,
) -> dict:
    """Terminal node: mark run as rejected and update report status."""
    run_id = state["run_id"]
    report_id = state.get("final_report_id")
    iteration = state.get("iteration_count", 0)

    try:
        from app.models.run import ResearchRun
        from app.services.event_service import log_event, publish_event
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import select
        from datetime import datetime, timezone

        async with AsyncSessionLocal() as db:
            run_result = await db.execute(select(ResearchRun).where(ResearchRun.id == run_id))
            run = run_result.scalar_one_or_none()
            if run:
                run.status = "completed"
                run.current_stage = "Rejected"
                run.completed_at = datetime.now(timezone.utc)

            _ev_rej = await log_event(
                db,
                run_id=run_id,
                agent_name="system",
                event_type="workflow_complete",
                summary="Run terminated: report rejected after critic review cycle limit",
                output_ref=f"report_id:{report_id}" if report_id else None,
                iteration=iteration,
            )
            await db.commit()
            await publish_event(_ev_rej)

        logger.info("_reject_terminal_node: run %s marked rejected", run_id)

    except Exception as exc:
        logger.error("_reject_terminal_node: error for run %s: %s", run_id, exc)

    return {"workflow_status": "completed"}


async def _needs_attention_terminal_node(
    state: ResearchWorkflowState,
    config: RunnableConfig,
) -> dict:
    """Terminal node: mark run completed with needs_attention status."""
    run_id = state["run_id"]
    report_id = state.get("final_report_id")
    iteration = state.get("iteration_count", 0)

    try:
        from app.models.run import ResearchRun
        from app.services.event_service import log_event, publish_event
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import select
        from datetime import datetime, timezone

        async with AsyncSessionLocal() as db:
            run_result = await db.execute(select(ResearchRun).where(ResearchRun.id == run_id))
            run = run_result.scalar_one_or_none()
            if run:
                run.status = "completed"
                run.current_stage = "Needs Attention"
                run.completed_at = datetime.now(timezone.utc)

            _ev_na = await log_event(
                db,
                run_id=run_id,
                agent_name="system",
                event_type="workflow_complete",
                summary="Run completed with unresolved issues (needs_attention) after critic cycle limit",
                output_ref=f"report_id:{report_id}" if report_id else None,
                iteration=iteration,
            )
            await db.commit()
            await publish_event(_ev_na)

        logger.info("_needs_attention_terminal_node: run %s marked needs_attention", run_id)

    except Exception as exc:
        logger.error("_needs_attention_terminal_node: error for run %s: %s", run_id, exc)

    return {"workflow_status": "completed"}


# ── Graph construction ─────────────────────────────────────────────────────────

def _build_graph_skeleton():
    """Build the StateGraph WITHOUT a checkpointer (sync, called once at import).

    The checkpointer is injected asynchronously in ``get_research_graph()``.
    """
    from app.graph.nodes import (
        initialize_run_node,
        finalize_report_node,
        fail_workflow_node,
        claim_extraction_node,
        critic_node,
        citation_validation_node,
        planning_complete_node,
        critic_review_approval_node,
    )
    from app.agents.supervisor import supervisor_node
    from app.agents.planner import planning_node
    from app.agents.researcher import research_node

    builder = StateGraph(ResearchWorkflowState)

    # Register nodes
    builder.add_node("initialize_run", initialize_run_node)
    builder.add_node("supervisor_node", supervisor_node)
    builder.add_node("planning_node", planning_node)
    builder.add_node("planning_complete_node", planning_complete_node)
    builder.add_node("research_node", research_node)
    builder.add_node("finalize_report", finalize_report_node)
    builder.add_node("claim_extraction_node", claim_extraction_node)
    builder.add_node("critic_node", critic_node)
    builder.add_node("critic_review_approval_node", critic_review_approval_node)
    builder.add_node("citation_validation_node", citation_validation_node)
    builder.add_node("reject_terminal", _reject_terminal_node)
    builder.add_node("needs_attention_terminal", _needs_attention_terminal_node)
    builder.add_node("fail_workflow", fail_workflow_node)

    # Entry point
    builder.set_entry_point("initialize_run")

    # Fixed edges
    builder.add_edge("initialize_run", "supervisor_node")
    # planning_node → planning_complete_node (approval checkpoint) → supervisor_node
    builder.add_edge("planning_node", "planning_complete_node")
    builder.add_edge("planning_complete_node", "supervisor_node")
    builder.add_edge("claim_extraction_node", "critic_node")
    # critic_node → critic_review_approval_node (approval checkpoint) → supervisor_node
    builder.add_edge("critic_node", "critic_review_approval_node")
    builder.add_edge("critic_review_approval_node", "supervisor_node")
    builder.add_edge("citation_validation_node", END)
    builder.add_edge("reject_terminal", END)
    builder.add_edge("needs_attention_terminal", END)
    builder.add_edge("fail_workflow", END)

    # Conditional edges
    builder.add_conditional_edges(
        "supervisor_node",
        route_after_supervisor,
        {
            "planning_node": "planning_node",
            "research_node": "research_node",
            "finalize_report": "finalize_report",
            "claim_extraction_node": "claim_extraction_node",
            "citation_validation_node": "citation_validation_node",
            "reject_terminal": "reject_terminal",
            "needs_attention_terminal": "needs_attention_terminal",
            "fail_workflow": "fail_workflow",
        },
    )
    builder.add_conditional_edges(
        "research_node",
        route_after_research,
        {
            "supervisor_node": "supervisor_node",
            "fail_workflow": "fail_workflow",
        },
    )
    builder.add_conditional_edges(
        "finalize_report",
        route_after_finalize,
        {
            "claim_extraction_node": "claim_extraction_node",
            "fail_workflow": "fail_workflow",
            END: END,
        },
    )
    return builder


# ── Module-level singleton ────────────────────────────────────────────────────

_graph = None


async def get_research_graph():
    """Return the compiled graph singleton (async — initialises checkpointer).

    The graph is compiled once per process on the first async call.
    Subsequent calls return the cached instance.
    """
    global _graph
    if _graph is None:
        from app.core.config import settings
        from app.graph.checkpointer import get_checkpointer
        checkpointer = await get_checkpointer()
        builder = _build_graph_skeleton()
        interrupt_nodes = (
            ["planning_complete_node", "critic_review_approval_node"]
            if settings.REQUIRE_HUMAN_APPROVAL
            else []
        )
        _graph = builder.compile(
            checkpointer=checkpointer,
            interrupt_before=interrupt_nodes,
        )
        logger.info(
            "Research graph compiled successfully (interrupt_before=%s)",
            interrupt_nodes,
        )
    return _graph
