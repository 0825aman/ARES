from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone


class SensitiveDataFilter(logging.Filter):
    """Redacts sensitive credentials, tokens, and API keys from log messages."""

    _KEY_PATTERN = re.compile(
        r"(?i)\b(api[_-]?key|access[_-]?token|secret[_-]?key|password|bearer|authorization)\b([:=,\s'\"]+)([a-zA-Z0-9_\-\.]{12,})"
    )
    _GENERIC_KEY_PATTERN = re.compile(
        r"\b(sk-[a-zA-Z0-9]{20,}|tvly-[a-zA-Z0-9]{20,})\b"
    )

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            clean_msg = self._KEY_PATTERN.sub(r"\1\2[REDACTED]", record.msg)
            clean_msg = self._GENERIC_KEY_PATTERN.sub("[REDACTED]", clean_msg)
            record.msg = clean_msg
        return True


class JsonFormatter(logging.Formatter):
    """Emits each log record as a single JSON line.

    Picks up any extra={} fields passed by the caller and merges
    them into the JSON payload. Use with LOG_FORMAT=json in .env.
    """

    # Fields that are part of LogRecord internals — not forwarded to JSON
    _SKIP_FIELDS = frozenset({
        "name", "msg", "args", "created", "filename", "funcName",
        "levelname", "levelno", "lineno", "module", "msecs",
        "pathname", "process", "processName", "relativeCreated",
        "stack_info", "thread", "threadName", "exc_info", "exc_text",
        "message",
    })

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        base: dict = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
        }
        # Include request_id if available on record
        if hasattr(record, "request_id") and record.request_id:
            base["request_id"] = record.request_id

        # Merge caller-supplied extra= fields
        for key, value in record.__dict__.items():
            if key not in self._SKIP_FIELDS:
                try:
                    json.dumps(value)  # only include JSON-serialisable values
                    base[key] = value
                except (TypeError, ValueError):
                    base[key] = str(value)
        return json.dumps(base)


def configure_logging(log_format: str = "text") -> None:
    """Configure application-wide logging.

    Call once at application startup (app/main.py lifespan).

    Args:
        log_format: "text" for human-readable output (default),
                    "json" for structured JSON lines.
    """
    sensitive_filter = SensitiveDataFilter()
    handler = logging.StreamHandler()
    handler.addFilter(sensitive_filter)

    if log_format.lower() == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-8s %(name)s — %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        ))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler]
    root.addFilter(sensitive_filter)

    # Suppress noisy third-party loggers
    logging.getLogger("watchfiles").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
