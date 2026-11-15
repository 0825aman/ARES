"""ARES Guardrails System.

Comprehensive safety, security, and compliance guardrails across 9 categories:
1. Input Guardrails (Prompt injection, malicious input, input validation, PII detection, content filtering)
2. Output Guardrails (Hallucination detection, factual accuracy, toxicity, secret filtering, format validation)
3. Tool Execution Guardrails (Tool access permissions, API authorization, function validation, restricted execution)
4. Data Guardrails (Data privacy, PII masking, RBAC, DB access restrictions, unauthorized retrieval prevention)
5. Security Guardrails (Jailbreak detection, SQL injection prevention, cross-agent security, secret management)
6. Operational Guardrails (Execution timeout, token limits, rate limiting, loop prevention, cost budgeting)
7. Human-in-the-Loop Guardrails (Approval gates for critical actions, escalation to experts, data protection)
8. Multi-Agent Guardrails (Agent access control, task assignment validation, cross-agent verification, conflict resolution)
9. Ethical & Compliance Guardrails (Bias detection, fairness validation, explainability, compliance, audit trails)
"""
from __future__ import annotations

from app.guardrails.service import guardrails_service, GuardrailsService

__all__ = ["guardrails_service", "GuardrailsService"]
