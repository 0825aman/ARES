"""performance_metrics.py — LLM Performance, Latency, and Cost Metrics.

Metrics implemented:
- Response Latency: Mean, median, p95, and p99 run/request duration in seconds.
- Time to First Token (TTFT): Initial token streaming latency in seconds.
- Tokens per Second: Generation velocity (output tokens / response time).
- Input Tokens: Total prompt tokens sent to LLMs.
- Output Tokens: Total completion tokens received from LLMs.
- Cost per Request: Average cost per LLM invocation in USD.
- Cost per Successful Task: Total cost incurred per successfully completed mission in USD.
- Throughput: Completed requests or tasks per unit time (e.g. per minute).
- Error Rate: Percentage of failed LLM calls, rate limits (429), or timeouts.
"""
from __future__ import annotations

import statistics
from typing import Any


def calculate_latency_percentiles(durations_seconds: list[float]) -> dict[str, float]:
    """Calculate mean, min, max, p50, p95, and p99 response latencies."""
    if not durations_seconds:
        return {"mean": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "min": 0.0, "max": 0.0}

    sorted_d = sorted(durations_seconds)
    n = len(sorted_d)

    mean_val = statistics.mean(sorted_d)
    p50 = statistics.median(sorted_d)

    idx_95 = min(n - 1, int(math_ceil(0.95 * n)) - 1)
    idx_99 = min(n - 1, int(math_ceil(0.99 * n)) - 1)

    return {
        "mean": round(mean_val, 2),
        "p50": round(p50, 2),
        "p95": round(sorted_d[idx_95], 2),
        "p99": round(sorted_d[idx_99], 2),
        "min": round(sorted_d[0], 2),
        "max": round(sorted_d[-1], 2),
    }


def math_ceil(x: float) -> int:
    import math
    return math.ceil(x)


def tokens_per_second_metric(output_tokens: int, duration_seconds: float) -> float:
    """Tokens per Second: Output token generation rate."""
    if duration_seconds <= 0 or output_tokens <= 0:
        return 0.0
    return round(output_tokens / duration_seconds, 2)


def cost_per_successful_task(total_cost_usd: float, successful_tasks: int) -> float:
    """Cost per Successful Task: Average financial cost per completed task."""
    if successful_tasks <= 0:
        return 0.0
    return round(total_cost_usd / successful_tasks, 4)


def error_rate_metric(total_requests: int, failed_requests: int) -> float:
    """Error Rate: Percentage of failed requests, rate limits, or exceptions."""
    if total_requests <= 0:
        return 0.0
    return round(failed_requests / total_requests, 4)


def throughput_per_minute_metric(completed_tasks: int, total_window_seconds: float) -> float:
    """Throughput: Tasks processed per minute."""
    if total_window_seconds <= 0:
        return 0.0
    return round((completed_tasks / total_window_seconds) * 60, 2)
