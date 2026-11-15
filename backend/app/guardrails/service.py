"""service.py — Unified Guardrails Service for ARES.

Orchestrates all 9 Guardrail categories into a unified service interface:
1. Input Guardrails
2. Output Guardrails
3. Tool Execution Guardrails
4. Data Guardrails
5. Security Guardrails
6. Operational Guardrails
7. Human-in-the-Loop Guardrails
8. Multi-Agent Guardrails
9. Ethical & Compliance Guardrails
"""
from __future__ import annotations

import logging
from typing import Any

from app.guardrails.input_guardrails import input_guardrails, InputValidationResult
from app.guardrails.output_guardrails import output_guardrails, OutputValidationResult
from app.guardrails.tool_guardrails import tool_guardrails, ToolExecutionPolicy
from app.guardrails.data_guardrails import data_guardrails
from app.guardrails.security_guardrails import security_guardrails
from app.guardrails.operational_guardrails import operational_guardrails
from app.guardrails.hitl_guardrails import hitl_guardrails, HumanApprovalCheck
from app.guardrails.multi_agent_guardrails import multi_agent_guardrails
from app.guardrails.ethical_guardrails import ethical_guardrails

logger = logging.getLogger(__name__)


class GuardrailsService:
    """Unified facade orchestrating all 9 safety, security, and compliance guardrails."""

    def __init__(self):
        self.input = input_guardrails
        self.output = output_guardrails
        self.tool = tool_guardrails
        self.data = data_guardrails
        self.security = security_guardrails
        self.operational = operational_guardrails
        self.hitl = hitl_guardrails
        self.multi_agent = multi_agent_guardrails
        self.ethical = ethical_guardrails

    # ── Category 1 & 5: Input & Security Guardrails ───────────────────────────
    def validate_input(self, text: str, mask_pii: bool = True) -> InputValidationResult:
        """Validate, sanitize, and scan input against injections, PII, and threats."""
        result = self.input.validate(text, mask_pii_enabled=mask_pii)

        # Audit decision
        decision = "PASS" if result.is_valid else "BLOCK"
        self.ethical.record_audit(
            guardrail_type="input",
            event_type="user_input_validation",
            decision=decision,
            details={
                "risk_score": result.risk_score,
                "injections": result.detected_injections,
                "pii_count": len(result.detected_pii),
                "violations": result.violations,
            },
        )
        return result

    # ── Category 2 & 9: Output & Factual Guardrails ───────────────────────────
    def validate_output(
        self,
        output_text: str,
        expected_format: str = "text",
        citations: list[dict] | None = None,
        claims: list[dict] | None = None,
    ) -> OutputValidationResult:
        """Validate AI response against secrets leakage, hallucinations, and toxicity."""
        result = self.output.validate(
            output_text,
            expected_format=expected_format,
            citations=citations,
            claims=claims,
        )

        decision = "PASS" if result.is_valid else "FLAG"
        self.ethical.record_audit(
            guardrail_type="output",
            event_type="agent_output_validation",
            decision=decision,
            details={
                "hallucination_score": result.hallucination_score,
                "toxicity_score": result.toxicity_score,
                "redacted_secrets": result.redacted_secrets,
                "violations": result.violations,
            },
        )
        return result

    # ── Category 3: Tool Execution Guardrails ─────────────────────────────────
    def authorize_tool(
        self,
        agent_role: str,
        tool_name: str,
        args: dict[str, Any] | None = None,
    ) -> ToolExecutionPolicy:
        """Verify tool execution permissions and argument validity."""
        policy = self.tool.check_tool_permission(agent_role, tool_name)
        if not policy.is_allowed:
            self.ethical.record_audit(
                guardrail_type="tool",
                event_type="tool_execution_attempt",
                decision="DENIED",
                details={"agent_role": agent_role, "tool_name": tool_name, "reason": policy.reason},
            )
            return policy

        if args:
            try:
                self.tool.validate_tool_arguments(tool_name, args)
            except Exception as exc:
                self.ethical.record_audit(
                    guardrail_type="tool",
                    event_type="argument_validation",
                    decision="INVALID",
                    details={"agent_role": agent_role, "tool_name": tool_name, "error": str(exc)},
                )
                return ToolExecutionPolicy(
                    agent_role=agent_role,
                    tool_name=tool_name,
                    is_allowed=False,
                    reason=str(exc),
                )

        return policy

    # ── Category 4: Data Guardrails ───────────────────────────────────────────
    def mask_data(self, data: Any) -> Any:
        """Mask sensitive PII in data structures."""
        return self.data.mask_sensitive_data(data)

    def verify_project_isolation(self, request_project_id: str, resource_project_id: str, resource_type: str = "resource") -> None:
        """Enforce multi-tenant and project-level boundary isolation."""
        self.data.validate_project_data_access(request_project_id, resource_project_id, resource_type)

    # ── Category 6: Operational Guardrails ────────────────────────────────────
    def check_operational_limits(
        self,
        start_time: float,
        current_iteration: int,
        critic_cycles: int = 0,
        tokens_used: int = 0,
        estimated_cost: float = 0.0,
    ) -> tuple[bool, str | None]:
        """Check execution time, loop counters, tokens, and budget."""
        time_ok, _, time_err = self.operational.check_execution_time(start_time)
        if not time_ok:
            return False, time_err

        loop_ok, loop_err = self.operational.check_iteration_loop(current_iteration, critic_cycles)
        if not loop_ok:
            return False, loop_err

        tok_ok, tok_err = self.operational.check_token_budget(tokens_used)
        if not tok_ok:
            return False, tok_err

        cost_ok, cost_err = self.operational.check_cost_budget(estimated_cost)
        if not cost_ok:
            return False, cost_err

        return True, None

    # ── Category 7: Human-in-the-Loop Guardrails ──────────────────────────────
    def check_action_approval(self, action_type: str, context: dict[str, Any] | None = None) -> HumanApprovalCheck:
        """Determine if an action requires human administrator sign-off."""
        return self.hitl.evaluate_action(action_type, context)

    # ── Category 8: Multi-Agent Guardrails ────────────────────────────────────
    def validate_task_dispatch(self, agent_role: str, task: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate task dictionary before assigning to an agent."""
        return self.multi_agent.validate_task_assignment(agent_role, task)

    # ── Category 9: Ethical & Compliance Overview ─────────────────────────────
    def get_guardrails_status(self) -> dict[str, Any]:
        """Return status, active rules, and audit telemetry for all 9 guardrails."""
        return {
            "status": "active",
            "system_name": "ARES Guardrails System",
            "version": "1.0.0",
            "categories": {
                "1_input_guardrails": {
                    "status": "enabled",
                    "features": [
                        "Prompt injection detection",
                        "Jailbreak persona blocking",
                        "Malicious payload filtering",
                        "PII detection and masking",
                        "ASCII control character stripping",
                        "Inappropriate content filtering",
                    ],
                },
                "2_output_guardrails": {
                    "status": "enabled",
                    "features": [
                        "Hallucination detection",
                        "Factual accuracy validation",
                        "Credential & secret redaction",
                        "Toxicity filtering",
                        "Response format validation",
                    ],
                },
                "3_tool_guardrails": {
                    "status": "enabled",
                    "features": [
                        "Role-Based Tool Matrix (RBAC per agent)",
                        "SSRF protection on web fetches",
                        "Tool argument constraint validation",
                        "Tool call rate limiting",
                        "Restricted system command execution ban",
                    ],
                },
                "4_data_guardrails": {
                    "status": "enabled",
                    "features": [
                        "Data privacy protection",
                        "Automated PII data masking",
                        "Project boundary isolation",
                        "Role-based data access (RBAC)",
                        "SQL safety validation",
                    ],
                },
                "5_security_guardrails": {
                    "status": "enabled",
                    "features": [
                        "Jailbreak pattern detection",
                        "SQL injection defense",
                        "Cross-agent state poisoning protection",
                        "Credential sanitization in traces",
                    ],
                },
                "6_operational_guardrails": {
                    "status": "enabled",
                    "features": [
                        "Max execution time limits (300s)",
                        "Token budget caps (50k tokens)",
                        "Cost budget caps ($1.00)",
                        "Loop prevention (max 30 iterations, 3 critic cycles)",
                        "Circuit breaker and retry with backoff",
                    ],
                },
                "7_human_in_the_loop": {
                    "status": "enabled",
                    "features": [
                        "Financial transaction gatekeeper",
                        "External email/alert approvals",
                        "Critical data modification/deletion gatekeeper",
                        "Low-confidence output escalation to human experts",
                    ],
                },
                "8_multi_agent_guardrails": {
                    "status": "enabled",
                    "features": [
                        "Agent-level access control",
                        "Task assignment validation",
                        "Cross-agent output verification",
                        "Communication audit trails",
                        "Deterministic conflict resolution",
                        "Ping-pong circular loop detection",
                    ],
                },
                "9_ethical_and_compliance": {
                    "status": "enabled",
                    "features": [
                        "Demographic bias detection",
                        "Fairness & balanced reporting validation",
                        "Explainability & source attribution verification",
                        "GDPR/CCPA privacy alignment",
                        "Tamper-evident audit trail logging",
                    ],
                },
            },
            "recent_audit_events_count": len(self.ethical.get_audit_trail(limit=100)),
        }


guardrails_service = GuardrailsService()
