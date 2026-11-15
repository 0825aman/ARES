"""input_guardrails.py — Input Validation and Threat Detection Guardrails.

Validates user and external inputs before passing them to AI agents:
1. Prompt injection detection (direct, indirect, roleplay override, system prompt leaks).
2. Malicious input detection (command injection, shell commands, script tags, path traversal).
3. Input validation (length checks, control character stripping, schema compliance).
4. PII detection & masking (SSN, credit card, phone, email, IP, API keys).
5. Inappropriate content filtering (toxicity, violence, profanity, hate speech).
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PIIItem:
    entity_type: str
    raw_value: str
    masked_value: str
    start: int
    end: int


@dataclass
class InputValidationResult:
    is_valid: bool
    sanitized_text: str
    original_text: str
    risk_score: float  # 0.0 to 1.0
    violations: list[str] = field(default_factory=list)
    detected_pii: list[PIIItem] = field(default_factory=list)
    detected_injections: list[str] = field(default_factory=list)
    detected_malicious: list[str] = field(default_factory=list)
    detected_inappropriate: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "sanitized_text": self.sanitized_text,
            "risk_score": round(self.risk_score, 2),
            "violations": self.violations,
            "detected_pii": [
                {"type": p.entity_type, "masked": p.masked_value}
                for p in self.detected_pii
            ],
            "detected_injections": self.detected_injections,
            "detected_malicious": self.detected_malicious,
            "detected_inappropriate": self.detected_inappropriate,
        }


# ── 1. Prompt Injection Patterns ──────────────────────────────────────────────
PROMPT_INJECTION_PATTERNS = [
    # Direct instruction override
    (re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|directions)", re.IGNORECASE), "instruction_override"),
    (re.compile(r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)", re.IGNORECASE), "instruction_override"),
    (re.compile(r"forget\s+(all\s+)?(previous|prior|system)\s+(instructions|prompts|rules)", re.IGNORECASE), "instruction_override"),
    # Jailbreak personas
    (re.compile(r"\b(DAN|AIM|STAN|DUDE)\s+mode\b", re.IGNORECASE), "jailbreak_persona"),
    (re.compile(r"you\s+are\s+now\s+(unrestricted|unfiltered|jailbroken|free)", re.IGNORECASE), "jailbreak_persona"),
    (re.compile(r"do\s+anything\s+now", re.IGNORECASE), "jailbreak_persona"),
    (re.compile(r"developer\s+mode\s+(enabled|activated|on)", re.IGNORECASE), "jailbreak_persona"),
    # System prompt extraction
    (re.compile(r"(repeat|show|display|reveal|print)\s+(your\s+)?(system\s+prompt|initial\s+prompt|secret\s+instructions)", re.IGNORECASE), "system_prompt_leak"),
    (re.compile(r"what\s+are\s+your\s+(exact\s+)?(system|internal)\s+(instructions|prompts)", re.IGNORECASE), "system_prompt_leak"),
    # Delimiter escapes
    (re.compile(r"(</?system>|\[INST\]|\[/INST\]|<<SYS>>|<\|im_start\|>|<\|im_end\|>)", re.IGNORECASE), "delimiter_escape"),
    (re.compile(r"<!--\s*#system|###\s*System\s*Instruction", re.IGNORECASE), "delimiter_escape"),
]

# ── 2. Malicious Input Patterns ───────────────────────────────────────────────
MALICIOUS_INPUT_PATTERNS = [
    # Command injection
    (re.compile(r"\b(rm\s+-rf|del\s+/f|powershell|cmd\.exe|/bin/sh|/bin/bash)\b", re.IGNORECASE), "command_execution"),
    (re.compile(r"(\b(curl|wget|nc|netcat|ncat)\s+https?://)", re.IGNORECASE), "remote_tool_execution"),
    (re.compile(r"(\bsubprocess\.(Popen|run|call)|\bos\.system\b|\beval\(|\bexec\()", re.IGNORECASE), "code_execution"),
    # Path traversal
    (re.compile(r"(\.\./\.\.|\\\.\.\\|\.\.\\\.\.|%2e%2e)", re.IGNORECASE), "path_traversal"),
    # Script / XSS injection
    (re.compile(r"(<\s*script[^>]*>|javascript:\s*|on(error|load|click)\s*=)", re.IGNORECASE), "xss_injection"),
    # SQL injection patterns
    (re.compile(r"(\bUNION\s+SELECT\b|'\s*OR\s*'\d+'='|\bDROP\s+TABLE\b|;\s*--)", re.IGNORECASE), "sql_injection"),
]

# ── 3. PII Detection Patterns ─────────────────────────────────────────────────
PII_PATTERNS = [
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("PHONE", re.compile(r"(\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b)")),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("CREDIT_CARD", re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")),
    ("IPV4", re.compile(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b")),
    ("API_KEY", re.compile(r"\b(sk-[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|bearer\s+[a-zA-Z0-9_\-\.]{25,})\b", re.IGNORECASE)),
]

# ── 4. Inappropriate Content Lexicon ──────────────────────────────────────────
INAPPROPRIATE_KEYWORDS = [
    "bomb making", "synthesize ricin", "create biological weapon", "how to build explosive",
    "hack corporate firewall", "ddos script", "dox person", "credit card dump",
    "kill yourself", "mass shooter", "hate crime", "terrorist attack execution"
]


class InputGuardrails:
    """Validator and threat scanner for agent inputs."""

    def __init__(
        self,
        min_length: int = 3,
        max_length: int = 2000,
        strict_mode: bool = False,
    ):
        self.min_length = min_length
        self.max_length = max_length
        self.strict_mode = strict_mode

    def sanitize_characters(self, text: str) -> str:
        """Strip non-printable ASCII control characters and normalize brackets."""
        if not text:
            return ""
        # Strip ASCII control characters except \t and \n
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        # HTML-encode < and > to prevent tag injection into prompts
        cleaned = html.escape(cleaned, quote=False)
        return cleaned[: self.max_length].strip()

    def detect_prompt_injections(self, text: str) -> list[str]:
        """Scan text for prompt injection and jailbreak signatures."""
        detected = []
        for pattern, label in PROMPT_INJECTION_PATTERNS:
            if pattern.search(text):
                detected.append(label)
        return list(set(detected))

    def detect_malicious_inputs(self, text: str) -> list[str]:
        """Scan text for malicious payloads (command injection, traversal, XSS, SQLi)."""
        detected = []
        for pattern, label in MALICIOUS_INPUT_PATTERNS:
            if pattern.search(text):
                detected.append(label)
        return list(set(detected))

    def detect_pii(self, text: str) -> list[PIIItem]:
        """Detect personally identifiable information in input text."""
        pii_items: list[PIIItem] = []
        for entity_type, pattern in PII_PATTERNS:
            for match in pattern.finditer(text):
                raw = match.group(0)
                # Avoid false positives for generic short numbers
                if entity_type == "PHONE" and len(re.sub(r"\D", "", raw)) < 10:
                    continue
                masked = f"[REDACTED_{entity_type}]"
                pii_items.append(
                    PIIItem(
                        entity_type=entity_type,
                        raw_value=raw,
                        masked_value=masked,
                        start=match.start(),
                        end=match.end(),
                    )
                )
        return pii_items

    def mask_pii(self, text: str) -> tuple[str, list[PIIItem]]:
        """Mask detected PII occurrences with standard redaction tokens."""
        pii_items = self.detect_pii(text)
        if not pii_items:
            return text, []

        masked_text = text
        for item in sorted(pii_items, key=lambda x: len(x.raw_value), reverse=True):
            masked_text = masked_text.replace(item.raw_value, item.masked_value)
        return masked_text, pii_items

    def detect_inappropriate_content(self, text: str) -> list[str]:
        """Detect illegal, dangerous, or abusive keyword combinations."""
        text_lower = text.lower()
        detected = []
        for kw in INAPPROPRIATE_KEYWORDS:
            if kw in text_lower:
                detected.append(kw)
        return detected

    def validate(self, text: str, mask_pii_enabled: bool = True) -> InputValidationResult:
        """Run all input guardrail checks on input text."""
        violations: list[str] = []
        risk_score: float = 0.0

        if not text or not text.strip():
            return InputValidationResult(
                is_valid=False,
                sanitized_text="",
                original_text=text or "",
                risk_score=1.0,
                violations=["Input is empty or whitespace only"],
            )

        # 1. Length validation
        clean_stripped = text.strip()
        if len(clean_stripped) < self.min_length:
            violations.append(f"Input is too short (min {self.min_length} characters)")
            risk_score += 0.3

        if len(clean_stripped) > self.max_length:
            violations.append(f"Input exceeds maximum length of {self.max_length} characters")
            risk_score += 0.2

        # 2. Prompt injection detection
        injections = self.detect_prompt_injections(text)
        if injections:
            violations.append(f"Prompt injection pattern detected: {', '.join(injections)}")
            risk_score += 0.5 * len(injections)

        # 3. Malicious payload detection
        malicious = self.detect_malicious_inputs(text)
        if malicious:
            violations.append(f"Malicious input detected: {', '.join(malicious)}")
            risk_score += 0.6 * len(malicious)

        # 4. Inappropriate content filtering
        inappropriate = self.detect_inappropriate_content(text)
        if inappropriate:
            violations.append(f"Inappropriate or dangerous content detected: {', '.join(inappropriate)}")
            risk_score += 0.8

        # 5. PII Detection & optional masking
        if mask_pii_enabled:
            sanitized_text, pii_items = self.mask_pii(text)
            sanitized_text = self.sanitize_characters(sanitized_text)
        else:
            pii_items = self.detect_pii(text)
            sanitized_text = self.sanitize_characters(text)

        if pii_items:
            pii_types = list({item.entity_type for item in pii_items})
            violations.append(f"Personally Identifiable Information (PII) detected: {', '.join(pii_types)}")
            risk_score += 0.2 * len(pii_types)

        # Cap risk score at 1.0
        risk_score = min(1.0, risk_score)

        # Determine validity: strict mode or high risk marks as invalid
        threshold = 0.6 if not self.strict_mode else 0.3
        is_valid = risk_score < threshold and not (injections or malicious or inappropriate)

        return InputValidationResult(
            is_valid=is_valid,
            sanitized_text=sanitized_text,
            original_text=text,
            risk_score=risk_score,
            violations=violations,
            detected_pii=pii_items,
            detected_injections=injections,
            detected_malicious=malicious,
            detected_inappropriate=inappropriate,
        )


input_guardrails = InputGuardrails()
