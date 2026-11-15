"""hitl_guardrails.py — Human-in-the-Loop (HITL) Guardrails.

Ensures human oversight and approval for critical actions:
1. Human approval before financial/budget commitments.
2. Approval before sending external communications or alerts.
3. Manual verification of critical outputs (flagged low-confidence or high-risk claims).
4. Escalation to human experts when critic review flags unresolved contradictions.
5. Approval before modifying or deleting critical project or run data.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ActionRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Actions that strictly require human authorization before execution
ACTIONS_REQUIRING_APPROVAL = {
    "financial_transaction": ActionRiskLevel.CRITICAL,
    "send_external_email": ActionRiskLevel.HIGH,
    "delete_project_data": ActionRiskLevel.HIGH,
    "bulk_document_purge": ActionRiskLevel.HIGH,
    "publish_unverified_report": ActionRiskLevel.MEDIUM,
    "escalate_to_human_expert": ActionRiskLevel.MEDIUM,
}


@dataclass
class HumanApprovalCheck:
    requires_approval: bool
    risk_level: ActionRiskLevel
    action_type: str
    reason: str
    context: dict[str, Any] = field(default_factory=dict)


class HumanInTheLoopGuardrails:
    """Enforces human sign-off gates for high-risk operations."""

    def evaluate_action(
        self,
        action_type: str,
        context: dict[str, Any] | None = None,
    ) -> HumanApprovalCheck:
        """Determine if an action necessitates human authorization."""
        ctx = context or {}
        risk = ACTIONS_REQUIRING_APPROVAL.get(action_type, ActionRiskLevel.LOW)

        if action_type == "financial_transaction":
            return HumanApprovalCheck(
                requires_approval=True,
                risk_level=risk,
                action_type=action_type,
                reason="Financial transactions and paid credit charges require explicit human confirmation.",
                context=ctx,
            )

        elif action_type == "send_external_email":
            return HumanApprovalCheck(
                requires_approval=True,
                risk_level=risk,
                action_type=action_type,
                reason="Outbound communications to external parties require human review.",
                context=ctx,
            )

        elif action_type in ("delete_project_data", "bulk_document_purge"):
            return HumanApprovalCheck(
                requires_approval=True,
                risk_level=risk,
                action_type=action_type,
                reason="Irreversible data destruction requires administrator confirmation.",
                context=ctx,
            )

        elif action_type == "publish_unverified_report":
            return HumanApprovalCheck(
                requires_approval=True,
                risk_level=risk,
                action_type=action_type,
                reason="Report contains unverified or contested claims and requires human verification.",
                context=ctx,
            )

        return HumanApprovalCheck(
            requires_approval=False,
            risk_level=risk,
            action_type=action_type,
            reason="Action is within standard autonomous operational boundaries.",
            context=ctx,
        )

    def should_escalate_critic_review(
        self,
        critic_decision: str,
        overall_score: float,
        unverified_claims_count: int,
    ) -> tuple[bool, str]:
        """Determine if a report's quality requires escalation to human expert."""
        if critic_decision in ("needs_attention", "reject"):
            return True, f"Critic agent issued decision '{critic_decision}' with score {overall_score:.2f}."

        if overall_score < 0.65:
            return True, f"Quality score {overall_score:.2f} is below autonomous approval threshold (0.65)."

        if unverified_claims_count > 3:
            return True, f"Report contains {unverified_claims_count} unverified claims requiring human audit."

        return False, "Quality metrics meet autonomous standards."


hitl_guardrails = HumanInTheLoopGuardrails()
