"""test_metrics.py — Tests for metrics collection and sensitive data log filtering."""
import logging
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.logging_config import SensitiveDataFilter
from app.core.metrics import metrics
from app.main import app


def test_sensitive_data_filter_redacts_keys():
    filter_ = SensitiveDataFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Using api_key: sk-1234567890abcdef1234567890 for provider",
        args=(),
        exc_info=None,
    )
    filter_.filter(record)
    assert "sk-1234567890abcdef1234567890" not in record.msg
    assert "[REDACTED]" in record.msg


def test_sensitive_data_filter_redacts_password():
    filter_ = SensitiveDataFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Login failed with password=SuperSecretPassword123",
        args=(),
        exc_info=None,
    )
    filter_.filter(record)
    assert "SuperSecretPassword123" not in record.msg
    assert "[REDACTED]" in record.msg


def test_metrics_registry_increment_and_snapshot():
    metrics.reset()
    metrics.increment("runs_started")
    metrics.increment("runs_completed")
    metrics.increment("llm_calls_total", labels={"provider": "openai"})
    metrics.increment("exports_total", labels={"format": "pdf"})

    snapshot = metrics.get_snapshot()
    assert "counters" in snapshot
    assert snapshot["counters"]["runs_started"] == 1
    assert snapshot["counters"]["runs_completed"] == 1
    assert "llm_calls_total" in snapshot
    assert snapshot["llm_calls_total"]["provider=openai"] == 1
    assert "exports_total" in snapshot
    assert snapshot["exports_total"]["format=pdf"] == 1


@pytest.mark.asyncio
async def test_get_metrics_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/metrics")
        assert res.status_code == 200
        data = res.json()
        assert "started_at" in data
        assert "counters" in data
