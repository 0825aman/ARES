"""security_guardrails.py — Security & Threat Protection Guardrails.

Protects the Agentic AI application against security threats:
1. Prompt injection protection & Jailbreak detection.
2. SQL injection prevention across user parameters and document tags.
3. Cross-agent communication security (state poisoning defense, schema integrity).
4. Credential and secret management (sanitizing checkpoints and event traces).
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Known jailbreak strategies and prompt injection techniques
ADVANCED_JAILBREAK_PATTERNS = [
    re.compile(r"you\s+must\s+now\s+act\s+as\s+(an\s+unfiltered|an\s+evil|an\s+unaligned|a\s+rogue)\s+ai", re.IGNORECASE),
    re.compile(r"in\s+this\s+hypothetical\s+world\s+all\s+safety\s+filters\s+are\s+removed", re.IGNORECASE),
    re.compile(r"pretend\s+you\s+have\s+no\s+ethical\s+guidelines", re.IGNORECASE),
    re.compile(r"for\s+research\s+purposes\s+only,\s+explain\s+how\s+to\s+(create|synthesize|hack)", re.IGNORECASE),
    re.compile(r"base64\s+decode\s+and\s+execute", re.IGNORECASE),
    re.compile(r"rot13\s+encoded\s+command", re.IGNORECASE),
    re.compile(r"system\s*:\s*you\s*are\s*now", re.IGNORECASE),
]

# SQL injection patterns
SQLI_PATTERNS = [
    re.compile(r"(\bUNION\s+ALL\s+SELECT\b|\bUNION\s+SELECT\b)", re.IGNORECASE),
    re.compile(r"('\s*OR\s*'\d+'\s*=\s*'\d+)", re.IGNORECASE),
    re.compile(r"('\s*OR\s*1\s*=\s*1\b)", re.IGNORECASE),
    re.compile(r"(\bSELECT\s+.*\s+FROM\s+(?:users|sqlite_master|information_schema)\b)", re.IGNORECASE),
    re.compile(r"(;\s*DROP\s+TABLE\b|;\s*DELETE\s+FROM\b)", re.IGNORECASE),
]

# Permitted top-level keys for cross-agent LangGraph workflow state
VALID_STATE_KEYS = {
    "run_id",
    "project_id",
    "research_question",
    "workflow_mode",
    "max_supervisor_cycles",
    "research_plan",
    "research_tasks",
    "pending_task_ids",
    "current_task_id",
    "completed_task_ids",
    "failed_task_ids",
    "collected_evidence_ids",
    "task_results",
    "supervisor_decision",
    "revision_notes",
    "iteration_count",
    "workflow_status",
    "error_message",
    "report",
    "raw_llm_response",
    "generated_claims",
    "claim_verification_results",
    "overall_verification_status",
    "critic_cycles",
    "critic_decision",
    "critic_review_id",
    "citation_validation_passed",
    "citation_issues",
    "approval_status",
    "approval_id",
    "approval_decision",
    "approval_notes",
}


class SecurityGuardrails:
    """Security threats detector and cross-agent communication validator."""

    def detect_jailbreak(self, text: str) -> tuple[bool, list[str]]:
        """Identify multi-pattern jailbreak and system override techniques."""
        matches: list[str] = []
        for pat in ADVANCED_JAILBREAK_PATTERNS:
            if pat.search(text):
                matches.append(pat.pattern)
        return len(matches) > 0, matches

    def detect_sql_injection(self, text: str) -> tuple[bool, list[str]]:
        """Detect SQL injection payload fragments."""
        matches: list[str] = []
        for pat in SQLI_PATTERNS:
            if pat.search(text):
                matches.append(pat.pattern)
        return len(matches) > 0, matches

    def validate_cross_agent_state(self, state_update: dict[str, Any]) -> dict[str, Any]:
        """Validate and sanitize state updates passed between agents.

        Guards against state poisoning:
        - Drops any unrecognized state keys injected by untrusted input or prompt leaks.
        - Verifies iteration count and cycle numbers are positive integers.
        """
        if not isinstance(state_update, dict):
            raise ValueError("Cross-agent state update must be a dictionary")

        sanitized_update: dict[str, Any] = {}
        for key, val in state_update.items():
            if key not in VALID_STATE_KEYS:
                logger.warning("CROSS-AGENT SECURITY: Dropped unauthorized state key '%s'", key)
                continue

            # Verify iteration counters are integers
            if key in ("iteration_count", "critic_cycles", "max_supervisor_cycles"):
                if not isinstance(val, int) or val < 0:
                    logger.warning("CROSS-AGENT SECURITY: Invalid integer for %s=%r; defaulting to 0", key, val)
                    val = 0

            sanitized_update[key] = val

        return sanitized_update

    def sanitize_credentials_from_object(self, obj: Any) -> Any:
        """Deeply scrub potential secrets from logging dictionaries or error dumps."""
        from app.guardrails.output_guardrails import output_guardrails

        if isinstance(obj, str):
            clean_str, _ = output_guardrails.redact_secrets(obj)
            return clean_str
        elif isinstance(obj, dict):
            clean_dict = {}
            for k, v in obj.items():
                if any(secret_kw in k.lower() for secret_kw in ("password", "secret", "token", "api_key")):
                    clean_dict[k] = "[REDACTED_CREDENTIAL]"
                else:
                    clean_dict[k] = self.sanitize_credentials_from_object(v)
            return clean_dict
        elif isinstance(obj, list):
            return [self.sanitize_credentials_from_object(item) for item in obj]
        return obj


security_guardrails = SecurityGuardrails()
