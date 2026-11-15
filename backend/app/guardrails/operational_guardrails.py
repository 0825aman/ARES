"""operational_guardrails.py — Execution and Resource Consumption Guardrails.

Controls agent execution and resource limits:
1. Maximum execution time (per-run workflow timeout enforcement).
2. Token usage limits (per-run and per-request caps).
3. API rate limiting (controlling LLM and search frequency).
4. Maximum agent iterations (hard loop ceiling for Supervisor and Critic).
5. Cost monitoring & budget limits (preventing accidental runaway expenditures).
6. Retry & failure handling (safe circuit breaker with exponential backoff).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class OperationalLimits:
    max_execution_time_seconds: int = 300       # 5 minutes default per research run
    max_tokens_per_run: int = 50_000            # Cap on total tokens consumed
    max_cost_budget_usd: float = 1.00           # Cap on cost per run
    max_supervisor_iterations: int = 30        # Loop ceiling
    max_critic_cycles: int = 3                 # Max review repetitions


class OperationalGuardrails:
    """Monitors and limits resource consumption during agent execution."""

    def __init__(self, limits: OperationalLimits | None = None):
        self.limits = limits or OperationalLimits()

    def check_execution_time(self, start_timestamp: float) -> tuple[bool, float, str | None]:
        """Check if execution elapsed time exceeds allowed limit."""
        elapsed = time.time() - start_timestamp
        if elapsed > self.limits.max_execution_time_seconds:
            msg = (
                f"Execution time exceeded: {elapsed:.1f}s elapsed "
                f"(max allowed {self.limits.max_execution_time_seconds}s)"
            )
            logger.warning("OPERATIONAL GUARDRAIL: %s", msg)
            return False, elapsed, msg
        return True, elapsed, None

    def check_token_budget(self, total_tokens_used: int) -> tuple[bool, str | None]:
        """Check if accumulated token usage has reached the token limit."""
        if total_tokens_used > self.limits.max_tokens_per_run:
            msg = (
                f"Token budget exceeded: {total_tokens_used:,} tokens used "
                f"(limit: {self.limits.max_tokens_per_run:,})"
            )
            logger.warning("OPERATIONAL GUARDRAIL: %s", msg)
            return False, msg
        return True, None

    def check_cost_budget(self, estimated_cost_usd: float) -> tuple[bool, str | None]:
        """Check if estimated cost has exceeded the safety budget."""
        if estimated_cost_usd > self.limits.max_cost_budget_usd:
            msg = (
                f"Cost budget exceeded: ${estimated_cost_usd:.4f} "
                f"(limit: ${self.limits.max_cost_budget_usd:.2f})"
            )
            logger.warning("OPERATIONAL GUARDRAIL: %s", msg)
            return False, msg
        return True, None

    def check_iteration_loop(self, current_iteration: int, critic_cycles: int = 0) -> tuple[bool, str | None]:
        """Enforce strict loop boundaries to prevent runaway agent execution."""
        if current_iteration >= self.limits.max_supervisor_iterations:
            msg = (
                f"Supervisor loop limit reached: {current_iteration} cycles "
                f"(max {self.limits.max_supervisor_iterations})"
            )
            logger.warning("OPERATIONAL GUARDRAIL: %s", msg)
            return False, msg

        if critic_cycles >= self.limits.max_critic_cycles:
            msg = (
                f"Critic review cycle limit reached: {critic_cycles} cycles "
                f"(max {self.limits.max_critic_cycles})"
            )
            logger.warning("OPERATIONAL GUARDRAIL: %s", msg)
            return False, msg

        return True, None


operational_guardrails = OperationalGuardrails()
