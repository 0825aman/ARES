"""guardrails.py — API endpoints for ARES Guardrails System.

Exposes endpoints to query guardrail status, validate inputs/outputs, and inspect audit logs.
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.guardrails.service import guardrails_service

router = APIRouter()


class ValidateInputRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Input text to validate")
    mask_pii: bool = Field(True, description="Whether to mask detected PII in sanitized output")


class ValidateOutputRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000, description="Generated output to validate")
    expected_format: str = Field("text", description="Expected format: 'text', 'json', or 'report'")
    citations: list[dict[str, Any]] | None = Field(None, description="Optional citations list for grounding check")
    claims: list[dict[str, Any]] | None = Field(None, description="Optional claims list for factual accuracy check")


@router.get("/status")
async def get_guardrails_status() -> dict[str, Any]:
    """Retrieve operational status and active feature set for all 9 guardrails."""
    return guardrails_service.get_guardrails_status()


@router.get("/policies")
async def get_guardrails_policies() -> dict[str, Any]:
    """Retrieve detailed policy matrices and boundaries."""
    from app.guardrails.tool_guardrails import ROLE_TOOL_PERMISSIONS, RESTRICTED_SYSTEM_TOOLS
    from app.guardrails.data_guardrails import USER_ROLES
    from app.guardrails.hitl_guardrails import ACTIONS_REQUIRING_APPROVAL

    return {
        "role_tool_permissions": {role: sorted(list(tools)) for role, tools in ROLE_TOOL_PERMISSIONS.items()},
        "restricted_system_tools": sorted(list(RESTRICTED_SYSTEM_TOOLS)),
        "user_roles_rbac": {role: sorted(list(perms)) for role, perms in USER_ROLES.items()},
        "actions_requiring_human_approval": {action: risk.value for action, risk in ACTIONS_REQUIRING_APPROVAL.items()},
        "operational_budgets": {
            "max_execution_time_seconds": guardrails_service.operational.limits.max_execution_time_seconds,
            "max_tokens_per_run": guardrails_service.operational.limits.max_tokens_per_run,
            "max_cost_budget_usd": guardrails_service.operational.limits.max_cost_budget_usd,
            "max_supervisor_iterations": guardrails_service.operational.limits.max_supervisor_iterations,
            "max_critic_cycles": guardrails_service.operational.limits.max_critic_cycles,
        },
    }


@router.get("/audit-trail")
async def get_audit_trail(limit: int = 50) -> list[dict[str, Any]]:
    """Retrieve the recent immutable audit trail of guardrail decisions."""
    return guardrails_service.ethical.get_audit_trail(limit=limit)


@router.post("/validate-input")
async def validate_input_endpoint(request: ValidateInputRequest) -> dict[str, Any]:
    """Validate an input string against prompt injections, PII, and malicious payloads."""
    result = guardrails_service.validate_input(request.text, mask_pii=request.mask_pii)
    return result.to_dict()


@router.post("/validate-output")
async def validate_output_endpoint(request: ValidateOutputRequest) -> dict[str, Any]:
    """Validate a generated response against secret leaks, toxicity, and hallucinations."""
    result = guardrails_service.validate_output(
        request.text,
        expected_format=request.expected_format,
        citations=request.citations,
        claims=request.claims,
    )
    return result.to_dict()
