"""retry.py — Async retry decorator with exponential backoff for ARES.

Provides ``async_retry``: a decorator that retries an async function when it
raises a *transient* error (network timeout, connection failure, HTTP 5xx,
HTTP 429 rate-limit).

Non-retryable errors (client errors, programming errors) are re-raised
immediately without consuming retry attempts.

Usage:
    from app.core.retry import async_retry

    @async_retry(max_attempts=3, base_delay=1.0)
    async def call_external_api() -> dict:
        ...
"""
from __future__ import annotations

import asyncio
import functools
import logging
import random
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# HTTP status codes that are worth retrying
_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503, 504})

# HTTP status codes that are client errors — retrying will not help
_NON_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({400, 401, 403, 404, 422})

# Exception types that indicate a transient network problem
_RETRYABLE_EXCEPTION_TYPES: tuple[type[Exception], ...] = ()


def _get_retryable_exception_types() -> tuple[type[Exception], ...]:
    """Lazy import of httpx exception types to avoid import-time httpx requirement."""
    try:
        import httpx
        return (
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.RemoteProtocolError,
        )
    except ImportError:
        return ()


def _is_retryable(exc: Exception) -> bool:
    """Return True if the exception represents a transient, retryable failure."""
    # Hard non-retryable: programming errors
    if isinstance(exc, (ValueError, TypeError)):
        return False

    # Lazy-import httpx exception check
    retryable_types = _get_retryable_exception_types()
    if retryable_types and isinstance(exc, retryable_types):
        return True

    # HTTP status code check (httpx.HTTPStatusError)
    try:
        import httpx
        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
            if status in _NON_RETRYABLE_STATUS_CODES:
                return False
            if status in _RETRYABLE_STATUS_CODES:
                return True
            # Other status codes (e.g. 301, 403) → do not retry
            return False
    except ImportError:
        pass

    return False


def _backoff_delay(attempt: int, base_delay: float, max_delay: float, jitter: bool) -> float:
    """Calculate the delay before the next attempt.

    Formula: min(base_delay * 2^attempt + jitter_component, max_delay)
    where jitter_component = random(0, 0.1 * delay_before_jitter) when jitter=True.
    """
    delay = base_delay * (2 ** attempt)
    if jitter:
        delay += random.uniform(0, 0.1 * delay)
    return min(delay, max_delay)


def async_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
) -> Callable[[F], F]:
    """Decorator factory: retry an async function on transient failures.

    Args:
        max_attempts: Total number of attempts (1 = no retries, 3 = up to 2 retries).
        base_delay: Initial delay in seconds before the first retry.
        max_delay: Maximum delay cap in seconds.
        jitter: Add random jitter to avoid thundering herd (default True).

    Non-retryable exceptions (ValueError, TypeError, HTTP 4xx) propagate immediately.
    Retryable exceptions (httpx.TimeoutException, ConnectError, HTTP 429/5xx) are
    retried up to (max_attempts - 1) times with exponential backoff.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    if not _is_retryable(exc):
                        raise

                    last_exc = exc
                    remaining = max_attempts - attempt - 1
                    if remaining <= 0:
                        # Exhausted all attempts
                        break

                    delay = _backoff_delay(attempt, base_delay, max_delay, jitter)
                    logger.warning(
                        "async_retry: %s failed (attempt %d/%d), retrying in %.2fs: %s",
                        func.__qualname__,
                        attempt + 1,
                        max_attempts,
                        delay,
                        exc,
                    )
                    await asyncio.sleep(delay)

            assert last_exc is not None
            raise last_exc

        return wrapper  # type: ignore[return-value]

    return decorator
