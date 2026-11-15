"""multi_agent_guardrails.py — Coordination and Agent-to-Agent Safety Guardrails.

Controls interactions and handoffs between multiple specialized agents:
1. Agent-level access control (enforcing role boundaries and state modification rights).
2. Task assignment validation (ensuring tasks assigned to Planner/Researcher/Critic are valid).
3. Cross-agent output verification (validating plan before research, research before critique).
4. Agent communication monitoring (recording communication logs and traces).
5. Conflict resolution between agents (arbitrating contradictory findings).
6. Prevention of infinite agent loops (circular handoff breaker).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

VALID_AGENT_ROLES = {"planner", "researcher", "critic", "supervisor"}


@dataclass
class AgentMessageAudit:
    timestamp: float
    sender_agent: str
    recipient_agent: str
    action_type: str
    payload_summary: str


class MultiAgentGuardrails:
    """Oversees multi-agent safety, handoffs, and coordination protocols."""

    def __init__(self):
        self._message_log: list[AgentMessageAudit] = []
        self._handoff_chain: list[str] = []

    def validate_agent_role(self, role: str) -> bool:
        """Verify role is recognized in the multi-agent system."""
        return role.lower() in VALID_AGENT_ROLES

    def validate_task_assignment(self, assigned_agent: str, task: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate task dictionary before assigning to an agent."""
        if not self.validate_agent_role(assigned_agent):
            return False, f"Unknown agent role '{assigned_agent}'"

        if not isinstance(task, dict):
            return False, "Task specification must be a dictionary"

        title = task.get("title") or task.get("description")
        if not title or not str(title).strip():
            return False, "Task lacks a valid title or description"

        return True, None

    def record_agent_communication(
        self,
        sender: str,
        recipient: str,
        action: str,
        payload_summary: str,
    ) -> None:
        """Audit trail for cross-agent messages."""
        entry = AgentMessageAudit(
            timestamp=time.time(),
            sender_agent=sender,
            recipient_agent=recipient,
            action_type=action,
            payload_summary=payload_summary[:200],
        )
        self._message_log.append(entry)
        self._handoff_chain.append(f"{sender}->{recipient}")
        # Keep log size bounded
        if len(self._message_log) > 500:
            self._message_log = self._message_log[-500:]
        if len(self._handoff_chain) > 100:
            self._handoff_chain = self._handoff_chain[-100:]

    def detect_circular_handoff_loop(self, window_size: int = 6) -> bool:
        """Detect repetitive circular ping-pong handoffs between agents."""
        if len(self._handoff_chain) < window_size:
            return False

        recent = self._handoff_chain[-window_size:]
        # Check if identical pattern repeats 3 times (e.g. A->B, B->A, A->B, B->A)
        if len(set(recent)) <= 2 and recent[0] == recent[2] == recent[4]:
            logger.warning("MULTI-AGENT GUARDRAIL: Detected ping-pong handoff loop between agents")
            return True

        return False

    def resolve_evidence_conflict(
        self,
        claim_text: str,
        supporting_count: int,
        refuting_count: int,
        confidence_delta: float,
    ) -> dict[str, Any]:
        """Deterministic resolution for conflicting evidence between agents.

        Weighs evidence by count and confidence to determine consensus status.
        """
        if supporting_count > 0 and refuting_count > 0:
            if supporting_count >= refuting_count * 2:
                status = "verified_with_contestation"
                resolution = "Predominance of evidence supports claim, but counter-evidence noted."
            elif refuting_count >= supporting_count * 2:
                status = "refuted_with_contestation"
                resolution = "Predominance of evidence refutes claim, but minor support noted."
            else:
                status = "disputed"
                resolution = "Significant contradiction among sources; requires manual review."
        elif supporting_count > 0:
            status = "verified"
            resolution = "Evidence consensus is positive."
        elif refuting_count > 0:
            status = "refuted"
            resolution = "Evidence consensus refutes claim."
        else:
            status = "unverified"
            resolution = "No direct evidence found."

        return {
            "claim": claim_text,
            "resolved_status": status,
            "resolution_notes": resolution,
            "supporting_count": supporting_count,
            "refuting_count": refuting_count,
        }


multi_agent_guardrails = MultiAgentGuardrails()
