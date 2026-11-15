"""data_guardrails.py — Data Privacy and Access Restriction Guardrails.

Protects data accessed, processed, and stored by AI agents:
1. Data privacy protection (automatic scrubbing of confidential markers).
2. Data masking and anonymization (replacing sensitive fields with tokens).
3. Role-based data access (RBAC: Admin, Researcher, Viewer).
4. Database access restrictions (enforcing parameterized queries, disallowing raw dynamic SQL).
5. Prevention of unauthorized data retrieval (ensuring documents and runs strictly belong to caller's project).
"""
from __future__ import annotations

import logging
import re
from typing import Any
from app.guardrails.input_guardrails import PII_PATTERNS

logger = logging.getLogger(__name__)


# User Roles Matrix
USER_ROLES = {
    "admin": {"read", "write", "delete", "export", "manage_users"},
    "researcher": {"read", "write", "export"},
    "viewer": {"read", "export"},
}


class DataAccessDeniedError(PermissionError):
    """Raised when an unauthorized data retrieval or modification is attempted."""


class DataGuardrails:
    """Enforces data boundaries, masking, and role-based data permissions."""

    def mask_sensitive_data(self, data: str | dict | list) -> str | dict | list:
        """Recursively mask PII and sensitive tokens in strings, dicts, and lists."""
        if isinstance(data, str):
            masked = data
            for entity_type, pattern in PII_PATTERNS:
                masked = pattern.sub(f"[REDACTED_{entity_type}]", masked)
            return masked

        elif isinstance(data, dict):
            return {k: self.mask_sensitive_data(v) for k, v in data.items()}

        elif isinstance(data, list):
            return [self.mask_sensitive_data(item) for item in data]

        return data

    def check_user_permission(self, user_role: str, action: str) -> bool:
        """Verify whether user role has permission to perform data action."""
        allowed_actions = USER_ROLES.get(user_role.lower(), set())
        return action in allowed_actions

    def validate_project_data_access(
        self,
        request_project_id: str,
        resource_project_id: str,
        resource_type: str = "resource",
    ) -> None:
        """Enforce strict project boundary isolation.

        Prevents cross-project data leakage: resources (documents, runs, evidence)
        must belong strictly to the project being accessed.
        """
        if str(request_project_id).strip() != str(resource_project_id).strip():
            logger.error(
                "UNAUTHORIZED DATA RETRIEVAL ATTEMPT: Attempted to access %s of project %s via project %s",
                resource_type,
                resource_project_id,
                request_project_id,
            )
            raise DataAccessDeniedError(
                f"Cross-project data boundary violation: {resource_type} does not belong to project {request_project_id}"
            )

    def validate_query_safety(self, query: str) -> bool:
        """Verify query doesn't contain raw destructive or exploratory SQL commands."""
        forbidden_sql = [
            r"\bDROP\s+TABLE\b",
            r"\bALTER\s+TABLE\b",
            r"\bTRUNCATE\b",
            r"\bDELETE\s+FROM\s+users\b",
            r"\bINSERT\s+INTO\s+users\b",
            r"\bSELECT\s+.*\s+FROM\s+information_schema\b",
            r"\bATTACH\s+DATABASE\b",
        ]
        for pattern in forbidden_sql:
            if re.search(pattern, query, re.IGNORECASE):
                logger.warning("Unsafe SQL pattern blocked by Data Guardrail: %s", pattern)
                return False
        return True


data_guardrails = DataGuardrails()
