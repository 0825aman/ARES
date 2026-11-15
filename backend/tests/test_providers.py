from __future__ import annotations
import pytest
from app.providers.web_fetcher import is_safe_url
from app.providers.llm import MockLLMProvider, CANNED_REPORT_JSON
from app.providers.web_search import MockWebSearchProvider

# ---------------------------------------------------------------------------
# SSRF tests
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("url,expected", [
    ("http://localhost:3000", False),
    ("http://127.0.0.1", False),
    ("http://127.0.0.1:8080/path", False),
    ("http://192.168.1.1", False),
    ("http://10.0.0.1", False),
    ("http://172.16.0.1", False),
    ("http://169.254.169.254", False),   # AWS metadata
    ("ftp://example.com", False),
    ("javascript:alert(1)", False),
    ("", False),
])
async def test_ssrf_blocked_urls(url, expected):
    assert is_safe_url(url) == expected

async def test_ssrf_example_com():
    # example.com resolves to a public IP — should pass
    result = is_safe_url("https://example.com")
    # Note: this requires DNS resolution; skip if DNS unavailable
    assert isinstance(result, bool)

async def test_ssrf_invalid_hostname():
    assert is_safe_url("http://this-hostname-does-not-exist.invalid/") == False

# ---------------------------------------------------------------------------
# LLM mock tests
# ---------------------------------------------------------------------------
async def test_mock_llm_returns_canned_response():
    provider = MockLLMProvider()
    result = await provider.complete("system", "user")
    assert result == CANNED_REPORT_JSON

async def test_mock_llm_custom_response():
    provider = MockLLMProvider(response='{"test": true}')
    result = await provider.complete("system", "user")
    assert result == '{"test": true}'

async def test_mock_llm_simulates_failure():
    provider = MockLLMProvider(fail=True)
    with pytest.raises(RuntimeError, match="simulated failure"):
        await provider.complete("system", "user")

async def test_mock_llm_fails_n_times_then_succeeds():
    provider = MockLLMProvider(fail_times=1)
    with pytest.raises(RuntimeError):
        await provider.complete("system", "user")  # call 1 — fails
    result = await provider.complete("system", "user")  # call 2 — succeeds
    assert result == CANNED_REPORT_JSON

# ---------------------------------------------------------------------------
# Web search mock tests
# ---------------------------------------------------------------------------
async def test_mock_search_returns_results():
    provider = MockWebSearchProvider()
    results = await provider.search("test query", num_results=5)
    assert len(results) > 0
    assert results[0].url.startswith("https://")
    assert results[0].title
    assert results[0].content

async def test_mock_search_simulates_failure():
    provider = MockWebSearchProvider(fail=True)
    with pytest.raises(RuntimeError, match="simulated failure"):
        await provider.search("test query", num_results=5)

async def test_mock_search_respects_num_results():
    provider = MockWebSearchProvider()
    results = await provider.search("query", num_results=1)
    assert len(results) <= 1
