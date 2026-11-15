"""agentic_metrics.py — Agentic AI and Autonomous Agent Evaluation Metrics.

Metrics implemented:
- Task Completion Rate: Percentage of tasks successfully completed by agents.
- Goal Achievement: Measures whether the agent achieves its assigned objective.
- Tool Call Accuracy: Measures whether correct tools are selected and invoked.
- Tool Execution Success Rate: Percentage of successful tool executions without errors.
- Planning Accuracy: Evaluates quality and structure of agent's execution plan.
- Reasoning Quality: Evaluates logical consistency between observations and outputs.
- Agent Coordination: Measures effective collaboration and message exchanges.
- Handoff Accuracy: Measures whether tasks are correctly transferred between agents.
- Loop Detection: Identifies repetitive or infinite agent execution cycles.
"""
from __future__ import annotations

from typing import Any


def task_completion_rate(tasks: list[dict[str, Any]]) -> float:
    """Task Completion Rate: Proportion of subtasks with status 'completed'."""
    if not tasks:
        return 0.0
    completed = sum(1 for t in tasks if t.get("status") == "completed")
    return round(completed / len(tasks), 4)


def goal_achievement_score(
    workflow_status: str,
    has_final_report: bool,
    critic_approved: bool = True,
) -> float:
    """Goal Achievement: Evaluates whether agent reached its objective.

    Scored on 0.0 to 1.0 scale:
    - 1.0: Workflow completed, report generated, critic approved.
    - 0.8: Completed and report generated with minor review notes.
    - 0.5: Incomplete or needs attention.
    - 0.0: Failed.
    """
    if workflow_status == "completed" and has_final_report and critic_approved:
        return 1.0
    elif workflow_status == "completed" and has_final_report:
        return 0.85
    elif workflow_status in ("needs_attention", "running"):
        return 0.5
    return 0.0


def tool_call_accuracy_score(
    total_tool_calls: int,
    unauthorized_or_invalid_calls: int,
) -> float:
    """Tool Call Accuracy: Proportion of tool calls that selected appropriate and authorized tools."""
    if total_tool_calls == 0:
        return 1.0
    valid_calls = max(0, total_tool_calls - unauthorized_or_invalid_calls)
    return round(valid_calls / total_tool_calls, 4)


def tool_execution_success_rate(
    total_executions: int,
    failed_executions: int,
) -> float:
    """Tool Execution Success Rate: Percentage of tool executions that succeed without error."""
    if total_executions == 0:
        return 1.0
    successful = max(0, total_executions - failed_executions)
    return round(successful / total_executions, 4)


def planning_accuracy_score(plan: dict[str, Any] | None, tasks: list[dict[str, Any]] | None) -> float:
    """Planning Accuracy: Evaluates structure, completeness, and task breakdown quality."""
    if not plan and not tasks:
        return 0.0

    score = 0.5  # Baseline

    if plan:
        # Check plan structure
        if plan.get("objective") or plan.get("title"):
            score += 0.15
        if plan.get("methodology") or plan.get("approach"):
            score += 0.15

    if tasks:
        # Check task granularity (ideal: 3 to 10 subtasks)
        task_count = len(tasks)
        if 2 <= task_count <= 12:
            score += 0.1
        # Check for prioritization
        has_priorities = any("priority" in t for t in tasks)
        if has_priorities:
            score += 0.1

    return min(1.0, round(score, 4))


def reasoning_quality_score(
    observations_present: bool,
    contradictions_analyzed: bool,
    limitations_explicit: bool,
    overall_score: float = 0.8,
) -> float:
    """Reasoning Quality: Evaluates logical consistency, analytical depth, and nuance."""
    score = overall_score
    if observations_present:
        score += 0.05
    if contradictions_analyzed:
        score += 0.10
    if limitations_explicit:
        score += 0.05
    return min(1.0, round(score, 4))


def agent_coordination_score(
    agent_events: list[dict[str, Any]],
    total_agents: int = 4,
) -> float:
    """Agent Coordination: Measures active participation and collaboration across the swarm."""
    if not agent_events:
        return 0.8  # Default baseline for single-mode runs

    participating_agents = {e.get("agent_role") or e.get("agent") for e in agent_events if e.get("agent_role") or e.get("agent")}
    coverage = len(participating_agents) / max(1, total_agents)
    return round(min(1.0, max(0.5, coverage)), 4)


def handoff_accuracy_score(
    handoffs_count: int,
    failed_handoffs: int = 0,
) -> float:
    """Handoff Accuracy: Success rate of inter-agent task transfers."""
    if handoffs_count == 0:
        return 1.0
    return round(max(0.0, (handoffs_count - failed_handoffs) / handoffs_count), 4)


def loop_detection_score(
    iteration_count: int,
    max_allowed: int = 30,
    has_circular_pingpong: bool = False,
) -> float:
    """Loop Detection: Returns 1.0 if completely loop-free, decaying towards 0.0 if loops detected."""
    if has_circular_pingpong:
        return 0.2

    if iteration_count <= 5:
        return 1.0
    elif iteration_count <= 15:
        return 0.9
    elif iteration_count < max_allowed:
        return 0.7
    return 0.4
