"""output_guardrails.py — Output Validation and Safety Verification Guardrails.

Validates AI-generated responses before displaying them to users or saving:
1. Hallucination detection & factual accuracy validation (citation grounding, unsupported claims).
2. Toxicity and harmful content filtering (abusive, dangerous, or illegal advice).
3. Sensitive information filtering (redacting leaked API keys, tokens, DB URLs, system paths).
4. Response format validation (JSON schema, markdown headings, empty response checks).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OutputValidationResult:
    is_valid: bool
    sanitized_output: str
    original_output: str
    hallucination_score: float  # 0.0 (grounded) to 1.0 (hallucinatory)
    toxicity_score: float       # 0.0 (safe) to 1.0 (toxic)
    violations: list[str] = field(default_factory=list)
    redacted_secrets: list[str] = field(default_factory=list)
    format_errors: list[str] = field(default_factory=list)
    unsupported_claims: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "hallucination_score": round(self.hallucination_score, 2),
            "toxicity_score": round(self.toxicity_score, 2),
            "violations": self.violations,
            "redacted_secrets": self.redacted_secrets,
            "format_errors": self.format_errors,
            "unsupported_claims_count": len(self.unsupported_claims),
        }


# ── 1. Sensitive Information / Leaked Credential Patterns ─────────────────────
SECRET_PATTERNS = [
    ("OPENAI_KEY", re.compile(r"\b(sk-[a-zA-Z0-9]{20,})\b")),
    ("BEARER_TOKEN", re.compile(r"\b(Bearer\s+[a-zA-Z0-9_\-\.]{25,})\b", re.IGNORECASE)),
    ("DATABASE_URL", re.compile(r"((?:sqlite\+aiosqlite|postgresql|mysql|mongodb)(?::\/\/|\+).*?:.*?@.*?)", re.IGNORECASE)),
    ("AWS_KEY", re.compile(r"\b(AKIA[0-9A-Z]{16})\b")),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----.*?-----END\s+(?:RSA\s+)?PRIVATE\s+KEY-----", re.DOTALL)),
    ("JWT_TOKEN", re.compile(r"\b(ey[A-Za-z0-9_-]{10,}\.ey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})\b")),
    ("SYSTEM_PATH", re.compile(r"(C:\\Users\\[A-Za-z0-9._-]+\\AppData|/etc/(?:passwd|shadow)|/home/[A-Za-z0-9._-]+/\.)", re.IGNORECASE)),
]

# ── 2. Harmful / Toxic Keywords in Model Outputs ─────────────────────────────
TOXIC_OUTPUT_PATTERNS = [
    re.compile(r"(step-by-step\s+instructions\s+to\s+build\s+a\s+bomb)", re.IGNORECASE),
    re.compile(r"(here\s+is\s+how\s+to\s+bypass\s+antivirus\s+and\s+execute\s+malware)", re.IGNORECASE),
    re.compile(r"(instructions\s+for\s+synthesizing\s+controlled\s+substances)", re.IGNORECASE),
    re.compile(r"(you\s+should\s+harm\s+yourself|commit\s+suicide)", re.IGNORECASE),
]


class OutputGuardrails:
    """Validator for AI-generated outputs, reports, and agent communications."""

    def redact_secrets(self, text: str) -> tuple[str, list[str]]:
        """Identify and redact leaked secrets, database URLs, and server paths."""
        if not text:
            return "", []

        redacted = text
        found_secrets: list[str] = []

        for secret_name, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                val = match.group(0)
                found_secrets.append(secret_name)
                redacted = redacted.replace(val, f"[REDACTED_{secret_name}]")

        return redacted, list(set(found_secrets))

    def detect_toxicity(self, text: str) -> tuple[float, list[str]]:
        """Calculate toxicity / harmfulness score of output."""
        if not text:
            return 0.0, []

        matches = []
        for pattern in TOXIC_OUTPUT_PATTERNS:
            if pattern.search(text):
                matches.append(pattern.pattern)

        score = min(1.0, len(matches) * 0.7)
        return score, matches

    def validate_format(self, output: str, expected_format: str = "text") -> list[str]:
        """Validate structure and format compliance of output."""
        errors: list[str] = []
        if not output or not output.strip():
            return ["Output is completely empty"]

        if expected_format == "json":
            try:
                json.loads(output)
            except json.JSONDecodeError as exc:
                errors.append(f"Invalid JSON format: {exc.msg}")
        elif expected_format == "report":
            # Research reports should have key structural sections
            lower = output.lower()
            if len(output.strip()) < 100:
                errors.append("Report is shorter than minimum length (100 characters)")
            if "summary" not in lower and "finding" not in lower:
                errors.append("Report lacks mandatory sections (Summary or Findings)")

        return errors

    def detect_hallucinations(
        self,
        output_text: str,
        citations: list[dict] | None = None,
        claims: list[dict] | None = None,
    ) -> tuple[float, list[str]]:
        """Estimate hallucination and factual accuracy risk based on evidence grounding.

        Scoring:
        - If claims are present: checks ratio of verified claims vs unverified/refuted.
        - If citations are missing or empty in a comprehensive report, adds risk penalty.
        """
        violations: list[str] = []
        risk_score = 0.0

        if claims:
            total = len(claims)
            refuted = sum(1 for c in claims if c.get("verification_status") == "refuted")
            unverified = sum(1 for c in claims if c.get("verification_status") in ("unverified", "insufficient_evidence"))

            if total > 0:
                refuted_ratio = refuted / total
                unverified_ratio = unverified / total

                if refuted_ratio > 0.1:
                    violations.append(f"{refuted} claims were refuted by source evidence")
                    risk_score += refuted_ratio * 0.8

                if unverified_ratio > 0.4:
                    violations.append(f"{unverified} claims could not be verified by retrieved evidence")
                    risk_score += unverified_ratio * 0.4

        if citations is not None and len(citations) == 0 and len(output_text) > 500:
            violations.append("Output contains substantial claims without supporting citations")
            risk_score += 0.3

        return min(1.0, risk_score), violations

    def validate(
        self,
        text: str,
        expected_format: str = "text",
        citations: list[dict] | None = None,
        claims: list[dict] | None = None,
    ) -> OutputValidationResult:
        """Run complete output guardrail checks."""
        violations: list[str] = []

        # 1. Redact secrets
        sanitized_text, secrets = self.redact_secrets(text)
        if secrets:
            violations.append(f"Sensitive information redacted: {', '.join(secrets)}")

        # 2. Harmful / toxic content
        toxicity_score, toxic_matches = self.detect_toxicity(sanitized_text)
        if toxic_matches:
            violations.append("Harmful or toxic content detected in model response")

        # 3. Format validation
        format_errors = self.validate_format(sanitized_text, expected_format=expected_format)
        if format_errors:
            violations.extend(format_errors)

        # 4. Hallucination and factual accuracy
        hallucination_score, ungrounded_items = self.detect_hallucinations(
            sanitized_text, citations=citations, claims=claims
        )
        violations.extend(ungrounded_items)

        is_valid = toxicity_score < 0.5 and len(format_errors) == 0 and len(toxic_matches) == 0

        return OutputValidationResult(
            is_valid=is_valid,
            sanitized_output=sanitized_text,
            original_output=text,
            hallucination_score=hallucination_score,
            toxicity_score=toxicity_score,
            violations=violations,
            redacted_secrets=secrets,
            format_errors=format_errors,
            unsupported_claims=ungrounded_items,
        )


output_guardrails = OutputGuardrails()
