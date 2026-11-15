"""metrics.py — In-process thread-safe operational metrics for ARES.

Provides:
  - increment(name, value=1, labels=None): increment a named counter.
  - get_snapshot(): returns current metrics summary dict.
  - reset(): clears all metrics (primarily for test isolation).
"""
from __future__ import annotations

import threading
from collections import Counter
from datetime import datetime, timezone
from typing import Any


class MetricsRegistry:
    """Thread-safe in-process metrics aggregator."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Counter[str] = Counter()
        self._labeled_counters: dict[str, Counter[str]] = {
            "llm_calls_total": Counter(),
            "llm_tokens_total": Counter(),
            "exports_total": Counter(),
            "http_requests_total": Counter(),
        }
        self._start_time = datetime.now(timezone.utc)

    def increment(
        self,
        name: str,
        value: int = 1,
        labels: dict[str, str | int] | None = None,
    ) -> None:
        """Increment a counter by value, optionally with labels."""
        with self._lock:
            self._counters[name] += value
            if labels and name in self._labeled_counters:
                label_key = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
                self._labeled_counters[name][label_key] += value

    def get_snapshot(self) -> dict[str, Any]:
        """Return a snapshot of all tracked metrics."""
        with self._lock:
            snapshot: dict[str, Any] = {
                "started_at": self._start_time.isoformat(),
                "counters": dict(self._counters),
            }
            for name, labeled in self._labeled_counters.items():
                if labeled:
                    snapshot[name] = dict(labeled)
            return snapshot

    def reset(self) -> None:
        """Reset all counters to zero."""
        with self._lock:
            self._counters.clear()
            for key in self._labeled_counters:
                self._labeled_counters[key].clear()
            self._start_time = datetime.now(timezone.utc)


metrics = MetricsRegistry()
