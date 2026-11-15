"""workflow.py — Workflow and process metrics."""
from __future__ import annotations
from typing import Any


def approval_success_rate(approvals: list[dict[str, Any]]) -> float:
    """Return proportion of decisions that resulted in approval."""
    decisions = [a for a in approvals if a.get("decision") in ("approved", "rejected")]
    if not decisions:
        return 0.0
    approved = sum(1 for a in decisions if a.get("decision") == "approved")
    return round(approved / len(decisions), 4)


def export_success_rate(exports: list[dict[str, Any]]) -> float:
    """Return proportion of exports that completed in ready status."""
    if not exports:
        return 0.0
    ready = sum(1 for e in exports if e.get("status") == "ready")
    return round(ready / len(exports), 4)
