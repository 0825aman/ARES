"""ResearchWorkflowState — the single shared state for all LangGraph nodes.

All fields are JSON-serialisable (str, int, list, dict, None only).
Evidence content is NOT stored here — only IDs and metadata.
Reducer-annotated fields are append-only or merge-only to allow
safe parallel/sequential accumulation.
"""
from __future__ import annotations

from typing import Annotated
from typing_extensions import TypedDict


# ── Reducer functions ──────────────────────────────────────────────────────────

def append_unique(existing: list[str], new: list[str]) -> list[str]:
    """Append new string items that are not already in the list.

    Prevents duplicate IDs if a node is retried by LangGraph.
    """
    seen = set(existing)
    return existing + [x for x in new if x not in seen]


def merge_task_results(
    existing: dict[str, dict],
    new: dict[str, dict],
) -> dict[str, dict]:
    """Merge task result dicts; existing results are never overwritten.

    ``{**new, **existing}`` means existing wins on key conflict — a task
    result written once cannot be silently overwritten by a retry.
    """
    return {**new, **existing}


# ── State definition ───────────────────────────────────────────────────────────

class ResearchWorkflowState(TypedDict):
    # ── Immutable context (set once by executor.py) ──────────────────────────
    run_id: str
    project_id: str
    research_question: str
    workflow_mode: str
    max_supervisor_cycles: int

    # ── Research plan (set/replaced by planning_node) ─────────────────────────
    research_plan: dict | None          # serialised ResearchPlan
    research_tasks: list[dict]          # serialised ResearchTask list (ordered by priority)
    pending_task_ids: list[str]         # task_ids not yet executed (mutable)
    current_task_id: str | None         # task currently being executed

    # ── Accumulated results (append-only reducers) ────────────────────────────
    completed_task_ids: Annotated[list[str], append_unique]
    failed_task_ids: Annotated[list[str], append_unique]
    collected_evidence_ids: Annotated[list[str], append_unique]  # EvidenceRecord IDs

    # ── Task results (merge reducer — existing results protected) ─────────────
    task_results: Annotated[dict[str, dict], merge_task_results]

    # ── Supervisor control ────────────────────────────────────────────────────
    supervisor_decision: str | None     # latest routing decision
    revision_notes: str | None          # notes to Planning Agent (if revising)
    iteration_count: int                # supervisor cycle count

    # ── Workflow lifecycle ────────────────────────────────────────────────────
    workflow_status: str                # initializing|planning|researching|finalizing|completed|failed
    error_message: str | None

    # ── Final output ──────────────────────────────────────────────────────────
    final_report_id: str | None         # ResearchReport.id after finalization

    # ── Phase 4 M4.4: Claim verification ──────────────────────────────────────
    verification_depth: str             # "basic" or "thorough"
    claim_ids: Annotated[list[str], append_unique]   # Claim IDs from claim_verifier
    verification_summary: dict | None   # summary dict from verify_claims_for_run

    # ── Phase 4 M4.5: Critic review ───────────────────────────────────────────
    critic_review_id: str | None        # CriticReview.id after critic_node runs
    critic_decision: str | None         # latest recommended_action from Critic
    critic_cycles: int                  # number of completed review cycles (0-based counter)

    # ── Phase 4 M4.6: Citation validation ─────────────────────────────────────
    citation_validation_passed: bool    # True when all 7 validator checks passed
