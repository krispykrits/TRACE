"""Structured JSON logging with correlation context and secret redaction."""

from __future__ import annotations

import contextvars
import json
import logging
import re
import sys
import uuid
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import TextIO

_SENSITIVE_NAME = re.compile(
    r"(?:password|secret|token|api[_-]?key|authorization|credential|private[_-]?key)",
    re.IGNORECASE,
)
_CORRELATION_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "trace_correlation_id", default=None
)
_STANDARD_RECORD_KEYS = frozenset(
    logging.LogRecord(
        name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
    ).__dict__
)


class SecretRedactor:
    """Redact sensitive fields and known secret values before JSON encoding."""

    def __init__(self, secret_values: Iterable[str] = ()) -> None:
        self._secret_values = tuple(
            sorted({value for value in secret_values if value}, key=len, reverse=True)
        )

    def sanitize(self, value: object, *, key: str | None = None) -> object:
        if key is not None and _SENSITIVE_NAME.search(key):
            return "[REDACTED]"
        if isinstance(value, str):
            for secret in self._secret_values:
                value = value.replace(secret, "[REDACTED]")
            return value
        if isinstance(value, Mapping):
            return {
                str(child_key): self.sanitize(child_value, key=str(child_key))
                for child_key, child_value in value.items()
            }
        if isinstance(value, (list, tuple, set, frozenset)):
            return [self.sanitize(item) for item in value]
        if value is None or isinstance(value, (bool, int, float)):
            return value
        return self.sanitize(str(value))


class JsonFormatter(logging.Formatter):
    """Serialize log records as one JSON object per line."""

    def __init__(self, redactor: SecretRedactor | None = None) -> None:
        super().__init__()
        self._redactor = redactor or SecretRedactor()

    def format(self, record: logging.LogRecord) -> str:
        correlation_id = getattr(record, "correlation_id", None) or _CORRELATION_ID.get()
        component = getattr(record, "component", None) or record.name.removeprefix(
            "trace_app."
        )
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "component": component,
            "correlation_id": correlation_id or "unassigned",
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_KEYS or key in payload or key.startswith("_"):
                continue
            if key in {"message", "asctime", "exc_text"}:
                continue
            payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(
            self._redactor.sanitize(payload),
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )


def configure_logging(
    *,
    level: str = "INFO",
    secret_values: Iterable[str] = (),
    stream: TextIO | None = None,
    correlation_id: str | None = None,
) -> str:
    """Configure TRACE's JSON handler and return the invocation correlation ID."""
    invocation_id = correlation_id or str(uuid.uuid4())
    _CORRELATION_ID.set(invocation_id)

    logger = logging.getLogger("trace_app")
    logger.handlers.clear()
    logger.setLevel(level)
    logger.propagate = False

    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(JsonFormatter(SecretRedactor(secret_values)))
    logger.addHandler(handler)
    return invocation_id


def get_correlation_id() -> str | None:
    """Return the correlation ID bound to the current execution context."""
    return _CORRELATION_ID.get()


def set_correlation_id(correlation_id: str | None) -> contextvars.Token[str | None]:
    """Bind a correlation ID for a future investigation or execution attempt."""
    return _CORRELATION_ID.set(correlation_id)


def reset_correlation_id(token: contextvars.Token[str | None]) -> None:
    """Restore the correlation ID that was active before a scoped operation."""
    _CORRELATION_ID.reset(token)

def collect_secret_values(*sources: Mapping[str, str]) -> tuple[str, ...]:
    """Collect values from mappings whose names identify secrets or credentials."""
    return tuple(
        value
        for source in sources
        for key, value in source.items()
        if _SENSITIVE_NAME.search(key) and value
    )
