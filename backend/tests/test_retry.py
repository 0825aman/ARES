from __future__ import annotations

"""test_retry.py — Unit tests for the async_retry decorator.

Tests cover:
  - Retry on HTTP 429 (rate limit)
  - Retry on httpx.TimeoutException
  - No retry on HTTP 404 (client error)
  - No retry on ValueError (programming error)
  - No retry on HTTP 400
  - max_attempts is honoured (does not retry beyond limit)
  - Backoff delay increases with each attempt
  - Successful call on first attempt returns without retry
  - Successful retry after transient failure
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_http_status_error(status_code: int):
    """Create an httpx.HTTPStatusError with the given status code."""
    import httpx
    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(status_code=status_code, request=request)
    return httpx.HTTPStatusError(
        f"HTTP {status_code}",
        request=request,
        response=response,
    )


# ---------------------------------------------------------------------------
# Basic retry behaviour
# ---------------------------------------------------------------------------


async def test_retry_success_on_first_attempt():
    """A successful call should return immediately without any retry."""
    from app.core.retry import async_retry

    call_count = 0

    @async_retry(max_attempts=3, base_delay=0.0)
    async def succeeds():
        nonlocal call_count
        call_count += 1
        return "ok"

    result = await succeeds()
    assert result == "ok"
    assert call_count == 1


async def test_retry_success_after_transient_failure():
    """Should succeed on second attempt after a timeout on the first."""
    import httpx
    from app.core.retry import async_retry

    call_count = 0

    @async_retry(max_attempts=3, base_delay=0.0, jitter=False)
    async def sometimes_times_out():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.TimeoutException("timed out")
        return "recovered"

    with patch("app.core.retry.asyncio.sleep", new_callable=AsyncMock):
        result = await sometimes_times_out()

    assert result == "recovered"
    assert call_count == 2


# ---------------------------------------------------------------------------
# Retryable errors
# ---------------------------------------------------------------------------


async def test_retry_on_http_429():
    """HTTP 429 must trigger a retry."""
    from app.core.retry import async_retry

    call_count = 0
    exc_429 = _make_http_status_error(429)

    @async_retry(max_attempts=3, base_delay=0.0, jitter=False)
    async def rate_limited():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise exc_429
        return "ok"

    with patch("app.core.retry.asyncio.sleep", new_callable=AsyncMock):
        result = await rate_limited()

    assert result == "ok"
    assert call_count == 3


async def test_retry_on_http_503():
    """HTTP 503 must trigger a retry."""
    from app.core.retry import async_retry

    call_count = 0
    exc_503 = _make_http_status_error(503)

    @async_retry(max_attempts=2, base_delay=0.0, jitter=False)
    async def server_error():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise exc_503
        return "ok"

    with patch("app.core.retry.asyncio.sleep", new_callable=AsyncMock):
        result = await server_error()

    assert result == "ok"
    assert call_count == 2


async def test_retry_on_timeout():
    """httpx.TimeoutException must trigger a retry."""
    import httpx
    from app.core.retry import async_retry

    call_count = 0

    @async_retry(max_attempts=3, base_delay=0.0, jitter=False)
    async def times_out():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.TimeoutException("timeout")
        return "ok"

    with patch("app.core.retry.asyncio.sleep", new_callable=AsyncMock):
        result = await times_out()

    assert result == "ok"
    assert call_count == 3


async def test_retry_on_connect_error():
    """httpx.ConnectError must trigger a retry."""
    import httpx
    from app.core.retry import async_retry

    call_count = 0
    request = httpx.Request("GET", "https://example.com")

    @async_retry(max_attempts=2, base_delay=0.0, jitter=False)
    async def connection_refused():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.ConnectError("connection refused", request=request)
        return "ok"

    with patch("app.core.retry.asyncio.sleep", new_callable=AsyncMock):
        result = await connection_refused()

    assert result == "ok"
    assert call_count == 2


# ---------------------------------------------------------------------------
# Non-retryable errors — must propagate immediately
# ---------------------------------------------------------------------------


async def test_no_retry_on_http_404():
    """HTTP 404 must NOT be retried — client error."""
    from app.core.retry import async_retry

    call_count = 0
    exc_404 = _make_http_status_error(404)

    @async_retry(max_attempts=3, base_delay=0.0)
    async def not_found():
        nonlocal call_count
        call_count += 1
        raise exc_404

    with pytest.raises(type(exc_404)):
        await not_found()

    assert call_count == 1  # raised immediately, no retry


async def test_no_retry_on_http_400():
    """HTTP 400 must NOT be retried."""
    from app.core.retry import async_retry

    call_count = 0
    exc_400 = _make_http_status_error(400)

    @async_retry(max_attempts=3, base_delay=0.0)
    async def bad_request():
        nonlocal call_count
        call_count += 1
        raise exc_400

    with pytest.raises(type(exc_400)):
        await bad_request()

    assert call_count == 1


async def test_no_retry_on_http_401():
    """HTTP 401 must NOT be retried."""
    from app.core.retry import async_retry

    call_count = 0
    exc_401 = _make_http_status_error(401)

    @async_retry(max_attempts=3, base_delay=0.0)
    async def unauthorized():
        nonlocal call_count
        call_count += 1
        raise exc_401

    with pytest.raises(type(exc_401)):
        await unauthorized()

    assert call_count == 1


async def test_no_retry_on_value_error():
    """ValueError must NOT be retried — programming error."""
    from app.core.retry import async_retry

    call_count = 0

    @async_retry(max_attempts=3, base_delay=0.0)
    async def bad_input():
        nonlocal call_count
        call_count += 1
        raise ValueError("invalid input")

    with pytest.raises(ValueError, match="invalid input"):
        await bad_input()

    assert call_count == 1


async def test_no_retry_on_type_error():
    """TypeError must NOT be retried."""
    from app.core.retry import async_retry

    call_count = 0

    @async_retry(max_attempts=3, base_delay=0.0)
    async def type_error():
        nonlocal call_count
        call_count += 1
        raise TypeError("wrong type")

    with pytest.raises(TypeError, match="wrong type"):
        await type_error()

    assert call_count == 1


# ---------------------------------------------------------------------------
# max_attempts enforcement
# ---------------------------------------------------------------------------


async def test_max_attempts_honoured():
    """After max_attempts, the last exception is re-raised."""
    import httpx
    from app.core.retry import async_retry

    call_count = 0

    @async_retry(max_attempts=3, base_delay=0.0, jitter=False)
    async def always_times_out():
        nonlocal call_count
        call_count += 1
        raise httpx.TimeoutException("always timeout")

    with patch("app.core.retry.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(httpx.TimeoutException):
            await always_times_out()

    assert call_count == 3  # exactly max_attempts, no more


async def test_max_attempts_1_means_no_retry():
    """max_attempts=1 means exactly one attempt and no retry."""
    import httpx
    from app.core.retry import async_retry

    call_count = 0

    @async_retry(max_attempts=1, base_delay=0.0)
    async def fails_once():
        nonlocal call_count
        call_count += 1
        raise httpx.TimeoutException("fail")

    with pytest.raises(httpx.TimeoutException):
        await fails_once()

    assert call_count == 1


# ---------------------------------------------------------------------------
# Backoff delay verification
# ---------------------------------------------------------------------------


async def test_backoff_delay_increases():
    """The delay passed to asyncio.sleep must increase between retries."""
    import httpx
    from app.core.retry import async_retry

    sleep_calls: list[float] = []

    async def mock_sleep(delay: float):
        sleep_calls.append(delay)

    call_count = 0

    @async_retry(max_attempts=4, base_delay=1.0, jitter=False)
    async def always_timeout():
        nonlocal call_count
        call_count += 1
        raise httpx.TimeoutException("always")

    with patch("app.core.retry.asyncio.sleep", side_effect=mock_sleep):
        with pytest.raises(httpx.TimeoutException):
            await always_timeout()

    # 4 attempts = 3 sleeps between them
    assert len(sleep_calls) == 3
    # Each delay should be >= the previous (exponential backoff)
    for i in range(1, len(sleep_calls)):
        assert sleep_calls[i] >= sleep_calls[i - 1], (
            f"Delay did not increase: {sleep_calls}"
        )


async def test_backoff_respects_max_delay():
    """Delays must never exceed max_delay."""
    import httpx
    from app.core.retry import async_retry

    sleep_calls: list[float] = []

    async def mock_sleep(delay: float):
        sleep_calls.append(delay)

    @async_retry(max_attempts=5, base_delay=10.0, max_delay=15.0, jitter=False)
    async def always_timeout():
        raise httpx.TimeoutException("always")

    with patch("app.core.retry.asyncio.sleep", side_effect=mock_sleep):
        with pytest.raises(httpx.TimeoutException):
            await always_timeout()

    for delay in sleep_calls:
        assert delay <= 15.0, f"Delay {delay} exceeded max_delay 15.0"
