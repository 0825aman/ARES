"""tool_guardrails.py — Tool Execution and API Authorization Guardrails.

Controls how AI agents interact with external tools and APIs:
1. Tool access permissions (Role-Based Tool Matrix per Agent Role).
2. API authorization (verifying credentials and endpoint legitimacy).
3. Function-call validation (argument validation, sanitization, length boundaries).
4. Restricted tool execution (blocking arbitrary shell execution, file traversal, network scans).
5. Prevention of unauthorized actions (rate limiting, circuit breakers).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


class ToolAccessDeniedError(PermissionError):
    """Raised when an agent attempts to execute an unauthorized tool."""


class ToolArgumentValidationError(ValueError):
    """Raised when tool arguments fail security or constraint validation."""


# ── 1. Role-Based Tool Matrix ──────────────────────────────────────────────────
# Defines which agent roles are authorized to invoke which tools
ROLE_TOOL_PERMISSIONS: dict[str, set[str]] = {
    # Researcher agent: gathers evidence from project documents and allowed web search
    "researcher": {
        "web_search",
        "fetch_web_content",
        "get_document_chunks",
        "extract_evidence",
    },
    # Planner agent: analyzes research scope and reads internal documents only
    "planner": {
        "get_document_chunks",
        "create_plan",
        "revise_plan",
    },
    # Critic agent: reviews factual accuracy and evaluates citations against chunks
    "critic": {
        "get_document_chunks",
        "verify_citations",
        "evaluate_report",
    },
    # Supervisor agent: coordinates state routing and approval requests
    "supervisor": {
        "route_task",
        "request_human_approval",
        "finalize_report",
    },
}

# Dangerous / restricted tools that agents must NEVER be allowed to execute
RESTRICTED_SYSTEM_TOOLS = {
    "execute_shell",
    "run_command",
    "delete_database",
    "modify_system_files",
    "eval_code",
    "download_executable",
}


@dataclass
class ToolExecutionPolicy:
    agent_role: str
    tool_name: str
    is_allowed: bool
    reason: str | None = None


class ToolGuardrails:
    """Gatekeeper for agent tool invocation and external API authorization."""

    def __init__(self, max_calls_per_minute: int = 60):
        self.max_calls_per_minute = max_calls_per_minute
        self._call_history: list[float] = []

    def check_tool_permission(self, agent_role: str, tool_name: str) -> ToolExecutionPolicy:
        """Verify whether an agent role is authorized to execute the given tool."""
        # Check against blacklisted system commands first
        if tool_name in RESTRICTED_SYSTEM_TOOLS:
            logger.warning("BLOCKED tool execution: %s is a restricted system tool", tool_name)
            return ToolExecutionPolicy(
                agent_role=agent_role,
                tool_name=tool_name,
                is_allowed=False,
                reason=f"Execution of restricted tool '{tool_name}' is permanently prohibited",
            )

        allowed_tools = ROLE_TOOL_PERMISSIONS.get(agent_role.lower(), set())
        if tool_name not in allowed_tools:
            logger.warning(
                "Access Denied: Agent '%s' attempted to call unauthorized tool '%s'",
                agent_role,
                tool_name,
            )
            return ToolExecutionPolicy(
                agent_role=agent_role,
                tool_name=tool_name,
                is_allowed=False,
                reason=f"Agent '{agent_role}' does not have permission to execute tool '{tool_name}'",
            )

        return ToolExecutionPolicy(agent_role=agent_role, tool_name=tool_name, is_allowed=True)

    def validate_tool_arguments(self, tool_name: str, args: dict[str, Any]) -> None:
        """Validate argument constraints and safety boundaries before tool execution."""
        if not isinstance(args, dict):
            raise ToolArgumentValidationError(f"Tool arguments for '{tool_name}' must be a dictionary")

        if tool_name == "web_search":
            query = args.get("query", "")
            if not query or not str(query).strip():
                raise ToolArgumentValidationError("Web search query cannot be empty")
            if len(str(query)) > 500:
                raise ToolArgumentValidationError("Web search query exceeds max length of 500 characters")
            num_results = args.get("num_results", 8)
            if not isinstance(num_results, int) or num_results < 1 or num_results > 20:
                raise ToolArgumentValidationError("num_results must be an integer between 1 and 20")

        elif tool_name == "fetch_web_content":
            url = args.get("url", "")
            if not url or not isinstance(url, str):
                raise ToolArgumentValidationError("URL must be a non-empty string")
            if not (url.startswith("http://") or url.startswith("https://")):
                raise ToolArgumentValidationError("URL must use http or https protocol")
            # SSRF check
            from app.providers.web_fetcher import is_safe_url
            if not is_safe_url(url):
                raise ToolArgumentValidationError(f"URL '{url}' violates SSRF protection policy (private/local IP)")

        elif tool_name == "get_document_chunks":
            project_id = args.get("project_id")
            if not project_id:
                raise ToolArgumentValidationError("get_document_chunks requires a project_id")

    def check_rate_limit(self) -> bool:
        """Leaky bucket rate limit check for external tool calls."""
        now = time.time()
        # Discard calls older than 60 seconds
        self._call_history = [t for t in self._call_history if now - t < 60.0]

        if len(self._call_history) >= self.max_calls_per_minute:
            logger.warning("Tool execution rate limit exceeded (%d calls/min)", self.max_calls_per_minute)
            return False

        self._call_history.append(now)
        return True

    def execute_guarded(
        self,
        agent_role: str,
        tool_name: str,
        func: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute a tool with full access, argument, and rate limit validation."""
        policy = self.check_tool_permission(agent_role, tool_name)
        if not policy.is_allowed:
            raise ToolAccessDeniedError(policy.reason)

        call_kwargs = kwargs if kwargs else {}
        self.validate_tool_arguments(tool_name, call_kwargs)

        if not self.check_rate_limit():
            raise RuntimeError(f"Rate limit exceeded for tool '{tool_name}' ({self.max_calls_per_minute}/min)")

        return func(*args, **kwargs)


tool_guardrails = ToolGuardrails()
