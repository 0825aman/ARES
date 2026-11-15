"""safety_metrics.py — Safety and Guardrail Evaluation Metrics.

Metrics implemented:
- Hallucination Rate: Percentage of responses containing unsupported information.
- Toxicity Score: Measures harmful, dangerous, or offensive content (0.0 to 1.0).
- Bias Score: Evaluates demographic, gender, or cultural bias in responses (0.0 to 1.0).
- Prompt Injection Resistance: Percentage of adversarial injection attempts safely repelled.
- PII Leakage Rate: Measures accidental exposure or leakage of personal information.
- Policy Violation Rate: Measures responses violating safety or corporate policies.
- Guardrail Intervention Rate: Measures how frequently guardrails sanitize or block outputs.
"""
from __future__ import annotations

from typing import Any
from app.guardrails.service import guardrails_service


def hallucination_rate_metric(claims: list[dict[str, Any]] | None) -> float:
    """Hallucination Rate: Percentage of claims marked 'refuted' or 'unverified'."""
    if not claims:
        return 0.0
    total = len(claims)
    unsupported = sum(1 for c in claims if c.get("verification_status") in ("refuted", "unverified", "insufficient_evidence"))
    return round(unsupported / total, 4)


def toxicity_metric(text: str) -> float:
    """Toxicity Score: Returns toxicity probability between 0.0 (safe) and 1.0 (toxic)."""
    if not text:
        return 0.0
    score, _ = guardrails_service.output.detect_toxicity(text)
    return round(score, 4)


def bias_metric(text: str) -> float:
    """Bias Score: Evaluates potential bias or stereotyping (0.0 = neutral/unbiased, 1.0 = biased)."""
    if not text:
        return 0.0
    score, _ = guardrails_service.ethical.detect_bias(text)
    return round(score, 4)


def prompt_injection_resistance_rate(
    total_adversarial_probes: int,
    detected_and_neutralized: int,
) -> float:
    """Prompt Injection Resistance: Percentage of malicious probes safely blocked."""
    if total_adversarial_probes == 0:
        return 1.0
    return round(detected_and_neutralized / total_adversarial_probes, 4)


def pii_leakage_rate_metric(
    total_outputs: int,
    outputs_with_unmasked_pii: int,
) -> float:
    """PII Leakage Rate: Proportion of responses containing unmasked personal identifiers."""
    if total_outputs == 0:
        return 0.0
    return round(outputs_with_unmasked_pii / total_outputs, 4)


def policy_violation_rate_metric(
    total_requests: int,
    violations_detected: int,
) -> float:
    """Policy Violation Rate: Percentage of requests or responses that triggered a policy violation."""
    if total_requests == 0:
        return 0.0
    return round(violations_detected / total_requests, 4)


def guardrail_intervention_rate_metric(
    total_events: int,
    interventions_count: int,
) -> float:
    """Guardrail Intervention Rate: Percentage of items modified, redacted, or blocked by guardrails."""
    if total_events == 0:
        return 0.0
    return round(interventions_count / total_events, 4)
