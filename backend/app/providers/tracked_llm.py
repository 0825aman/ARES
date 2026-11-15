"""TrackedLLMProvider — Phase 4 M4.7.

A lightweight wrapper around any LLMProvider that intercepts complete() calls
and records usage statistics. Observability only — never gates features.

Usage:
    llm = get_llm_provider()
    tracked = TrackedLLMProvider(llm)
    response = await tracked.complete(system_prompt, user_prompt)
    # tracked.call_count, tracked.total_tokens, tracked.estimated_cost_usd are now set

The tracker is not thread-safe for concurrent writes, but individual research
runs are executed sequentially within a single coroutine chain, so this is safe.

Token approximation: (len(input) + len(output)) / 4
Cost approximation: (total_tokens / 1000) * LLM_COST_PER_1K_TOKENS
"""
from __future__ import annotations

import logging
import time

from app.providers.llm import LLMProvider

logger = logging.getLogger(__name__)


class TrackedLLMProvider(LLMProvider):
    """Wraps an LLMProvider and accumulates per-run usage statistics.

    All statistics are accumulated in-memory; the caller is responsible for
    writing them to the ResearchRun record at run completion.
    """

    def __init__(self, provider: LLMProvider, cost_per_1k_tokens: float = 0.0):
        self._provider = provider
        self._cost_per_1k = cost_per_1k_tokens
        # Mutable accumulators
        self.call_count: int = 0
        self.total_tokens: int = 0
        self.estimated_cost_usd: float = 0.0
        self.total_latency_ms: float = 0.0

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Delegate to the wrapped provider and record usage."""
        start = time.monotonic()
        try:
            response = await self._provider.complete(system_prompt, user_prompt)
        finally:
            elapsed_ms = (time.monotonic() - start) * 1000
            self.total_latency_ms += elapsed_ms

        # Approximate token count: (input chars + output chars) / 4
        input_chars = len(system_prompt) + len(user_prompt)
        output_chars = len(response) if response else 0
        approx_tokens = (input_chars + output_chars) // 4

        self.call_count += 1
        self.total_tokens += approx_tokens
        self.estimated_cost_usd += (approx_tokens / 1000.0) * self._cost_per_1k

        logger.debug(
            "TrackedLLMProvider: call %d, ~%d tokens, cumulative cost $%.6f",
            self.call_count,
            approx_tokens,
            self.estimated_cost_usd,
        )
        return response

    def reset(self) -> None:
        """Reset all accumulators (useful for tests)."""
        self.call_count = 0
        self.total_tokens = 0
        self.estimated_cost_usd = 0.0
        self.total_latency_ms = 0.0

    @property
    def summary(self) -> dict:
        """Return a summary dict for logging or API response."""
        return {
            "call_count": self.call_count,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "total_latency_ms": round(self.total_latency_ms, 1),
        }
