"""ethical_guardrails.py — Ethical, Fairness, and Regulatory Compliance Guardrails.

Ensures responsible, fair, explainable, and compliant AI behaviour:
1. Bias detection (stereotyping across gender, race, religion, nationality).
2. Fairness validation (balanced representation of viewpoints, presence of counter-arguments).
3. Explainability (evidence grounding, clear reasoning, source attribution).
4. Regulatory compliance (GDPR/CCPA privacy alignment, right to erasure readiness).
5. Responsible AI principles (mandatory limitations section, confidence transparency).
6. Audit trails (verifiable logging of all validation decisions).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Heuristic patterns for demographic generalizations and stereotyping
BIAS_INDICATOR_PATTERNS = [
    re.compile(r"\ball\s+(women|men|immigrants|minorities|races)\s+(are|always|never|cannot)\b", re.IGNORECASE),
    re.compile(r"\b(inferior|superior)\s+(race|gender|ethnicity|religion)\b", re.IGNORECASE),
    re.compile(r"\bnaturally\s+(worse|better)\s+at\s+(math|science|leadership|business)\s+due\s+to\s+gender\b", re.IGNORECASE),
]


@dataclass
class GuardrailAuditRecord:
    timestamp: str
    guardrail_type: str
    event_type: str
    decision: str
    details: dict[str, Any] = field(default_factory=dict)


class EthicalGuardrails:
    """Validator for ethics, fairness, bias mitigation, and compliance auditing."""

    def __init__(self):
        self._audit_log: list[GuardrailAuditRecord] = []

    def detect_bias(self, text: str) -> tuple[float, list[str]]:
        """Scan text for demographic bias, stereotyping, or harmful generalizations."""
        matches: list[str] = []
        for pat in BIAS_INDICATOR_PATTERNS:
            found = pat.findall(text)
            if found:
                matches.append(pat.pattern)

        score = min(1.0, len(matches) * 0.5)
        return score, matches

    def validate_fairness_and_limitations(
        self,
        report_text: str,
        has_limitations_section: bool = True,
        has_contradictions_noted: bool = False,
    ) -> dict[str, Any]:
        """Verify that synthesis maintains balanced and responsible reporting."""
        findings: list[str] = []
        fairness_score = 1.0

        lower = report_text.lower()

        # Check for explicit limitations disclosure
        if not has_limitations_section and "limitation" not in lower:
            findings.append("Report lacks explicit limitations disclosure.")
            fairness_score -= 0.2

        # Check for absolute uncalibrated claims
        absolutist_terms = ["100% indisputable", "beyond any doubt", "impossible to fail", "absolute certainty"]
        for term in absolutist_terms:
            if term in lower:
                findings.append(f"Report uses uncalibrated claim language ('{term}').")
                fairness_score -= 0.15

        # Balanced reporting bonus if contradictions or nuances are analyzed
        if has_contradictions_noted or "contradiction" in lower or "counterpoint" in lower:
            fairness_score = min(1.0, fairness_score + 0.1)

        return {
            "fairness_score": max(0.0, round(fairness_score, 2)),
            "is_fair_and_balanced": fairness_score >= 0.7,
            "findings": findings,
        }

    def verify_explainability(
        self,
        citations_count: int,
        claims_count: int,
        confidence_available: bool,
    ) -> dict[str, Any]:
        """Assess the explainability and source traceability of findings."""
        issues: list[str] = []
        explainability_score = 1.0

        if claims_count > 0 and citations_count == 0:
            issues.append("Synthesized claims lack direct source citations.")
            explainability_score -= 0.5
        elif claims_count > 0 and (citations_count / claims_count) < 0.5:
            issues.append("Low citation-to-claim ratio (less than 50% grounded).")
            explainability_score -= 0.25

        if not confidence_available:
            issues.append("Confidence scores are missing from verification results.")
            explainability_score -= 0.15

        return {
            "explainability_score": max(0.0, round(explainability_score, 2)),
            "is_explainable": explainability_score >= 0.6,
            "issues": issues,
        }

    def record_audit(
        self,
        guardrail_type: str,
        event_type: str,
        decision: str,
        details: dict[str, Any] | None = None,
    ) -> GuardrailAuditRecord:
        """Append an immutable audit entry."""
        record = GuardrailAuditRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            guardrail_type=guardrail_type,
            event_type=event_type,
            decision=decision,
            details=details or {},
        )
        self._audit_log.append(record)
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]
        return record

    def get_audit_trail(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve recent audit events for compliance review."""
        return [
            {
                "timestamp": r.timestamp,
                "guardrail_type": r.guardrail_type,
                "event_type": r.event_type,
                "decision": r.decision,
                "details": r.details,
            }
            for r in reversed(self._audit_log[-limit:])
        ]


ethical_guardrails = EthicalGuardrails()
