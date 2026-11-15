"""structural.py — Structural operational evaluation metrics."""
from __future__ import annotations
from typing import Any


def task_completion_rate(runs: list[dict[str, Any]]) -> float:
    """Return ratio of completed runs to total runs."""
    if not runs:
        return 0.0
    completed = sum(1 for r in runs if r.get("status") == "completed")
    return round(completed / len(runs), 4)


def mean_run_latency_seconds(runs: list[dict[str, Any]]) -> float:
    """Return average run duration in seconds across completed runs."""
    durations: list[float] = []
    for r in runs:
        duration = r.get("duration_seconds")
        if duration is not None and duration >= 0:
            durations.append(float(duration))
    if not durations:
        return 0.0
    return round(sum(durations) / len(durations), 2)


def mean_llm_cost_usd(runs: list[dict[str, Any]]) -> float:
    """Return average estimated LLM cost in USD across runs."""
    costs: list[float] = []
    for r in runs:
        cost = r.get("estimated_cost_usd")
        if cost is not None:
            costs.append(float(cost))
    if not costs:
        return 0.0
    return round(sum(costs) / len(costs), 4)


def source_collection_rate(runs: list[dict[str, Any]], min_expected: int = 3) -> float:
    """Return ratio of runs that collected at least min_expected sources."""
    if not runs:
        return 0.0
    satisfied = sum(1 for r in runs if r.get("source_count", 0) >= min_expected)
    return round(satisfied / len(runs), 4)
