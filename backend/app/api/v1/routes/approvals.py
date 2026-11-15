"""Approval Workflow API — Phase 5 M5.5.

Endpoints:
  GET  /projects/{project_id}/runs/{run_id}/approval          → pending approval or null
  POST /projects/{project_id}/runs/{run_id}/approval/{id}/decide → submit decision
  GET  /projects/{project_id}/runs/{run_id}/approvals         → full history
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.approval_service import (
    get_approval_by_id,
    get_pending_approval,
    list_approvals,
    process_decision,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────

class ApprovalResponse(BaseModel):
    id: str
    run_id: str
    checkpoint_name: str
    node_name: str
    context_snapshot: Any        # decoded JSON
    status: str
    decision: Optional[str]
    decision_notes: Optional[str]
    created_at: str
    decided_at: Optional[str]
    expires_at: str

    model_config = {"from_attributes": True}


class DecisionInput(BaseModel):
    decision: str = Field(
        ...,
        description="One of: approved | rejected | revision_requested",
    )
    notes: Optional[str] = Field(
        None,
        description="Optional notes from the reviewer (required for revision_requested)",
    )


class DecisionResponse(BaseModel):
    approval_id: str
    decision: str
    run_status: str


class ApprovalListResponse(BaseModel):
    items: list[ApprovalResponse]
    total: int


# ── Helpers ────────────────────────────────────────────────────────────────────

def _serialize_approval(approval) -> ApprovalResponse:
    import json as _json
    try:
        snapshot = _json.loads(approval.context_snapshot)
    except Exception:
        snapshot = approval.context_snapshot

    return ApprovalResponse(
        id=approval.id,
        run_id=approval.run_id,
        checkpoint_name=approval.checkpoint_name,
        node_name=approval.node_name,
        context_snapshot=snapshot,
        status=approval.status,
        decision=approval.decision,
        decision_notes=approval.decision_notes,
        created_at=approval.created_at.isoformat(),
        decided_at=approval.decided_at.isoformat() if approval.decided_at else None,
        expires_at=approval.expires_at.isoformat(),
    )


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get(
    "/{project_id}/runs/{run_id}/approval",
    response_model=Optional[ApprovalResponse],
    summary="Get pending approval for a run",
    tags=["approvals"],
)
async def get_pending_approval_route(
    project_id: str = Path(..., description="Project ID"),
    run_id: str = Path(..., description="Run ID"),
    db: AsyncSession = Depends(get_db),
) -> Optional[ApprovalResponse]:
    """Return the current pending ApprovalRequest for the run, or null if none."""
    approval = await get_pending_approval(db, run_id=run_id)
    if approval is None:
        return None
    return _serialize_approval(approval)


@router.post(
    "/{project_id}/runs/{run_id}/approval/{approval_id}/decide",
    response_model=DecisionResponse,
    summary="Submit an approval decision",
    tags=["approvals"],
)
async def decide_approval_route(
    body: DecisionInput,
    project_id: str = Path(..., description="Project ID"),
    run_id: str = Path(..., description="Run ID"),
    approval_id: str = Path(..., description="Approval ID"),
    db: AsyncSession = Depends(get_db),
) -> DecisionResponse:
    """Submit approve / reject / revision_requested for a pending approval."""
    valid_decisions = {"approved", "rejected", "revision_requested"}
    if body.decision not in valid_decisions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"decision must be one of: {', '.join(sorted(valid_decisions))}",
        )

    if body.decision == "revision_requested" and not body.notes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="notes is required when decision is revision_requested",
        )

    approval = await get_approval_by_id(db, approval_id=approval_id, run_id=run_id)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval {approval_id} not found for run {run_id}",
        )

    if approval.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Approval is not pending (status={approval.status})",
        )

    try:
        result = await process_decision(
            db,
            approval=approval,
            decision=body.decision,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    return DecisionResponse(
        approval_id=approval_id,
        decision=body.decision,
        run_status=result["run_status"],
    )


@router.get(
    "/{project_id}/runs/{run_id}/approvals",
    response_model=ApprovalListResponse,
    summary="List all approval requests for a run",
    tags=["approvals"],
)
async def list_approvals_route(
    project_id: str = Path(..., description="Project ID"),
    run_id: str = Path(..., description="Run ID"),
    db: AsyncSession = Depends(get_db),
) -> ApprovalListResponse:
    """Return all ApprovalRequests for the run, newest first."""
    approvals = await list_approvals(db, run_id=run_id)
    return ApprovalListResponse(
        items=[_serialize_approval(a) for a in approvals],
        total=len(approvals),
    )
