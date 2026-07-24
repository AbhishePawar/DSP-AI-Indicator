"""Structured logging — stdlib / in-memory adapters only."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from production_platform.production.interfaces import LoggingPort

__all__ = [
    "InMemoryLoggingPort",
    "LogRecord",
    "StdlibLoggingPort",
    "new_correlation_id",
]


def new_correlation_id() -> str:
    """Return a new opaque correlation id."""
    return f"corr_{uuid.uuid4().hex}"


@dataclass(frozen=True, slots=True)
class LogRecord:
    """Immutable structured log entry (in-memory capture)."""

    level: str
    message: str
    correlation_id: str | None
    fields: dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


class InMemoryLoggingPort:
    """Process-local log capture — not a vendor sink."""

    def __init__(self, *, max_records: int = 1000) -> None:
        self._max = max(1, max_records)
        self._records: list[LogRecord] = []
        self._lock = Lock()

    def log(
        self,
        level: str,
        message: str,
        *,
        correlation_id: str | None = None,
        fields: dict[str, Any] | None = None,
    ) -> None:
        record = LogRecord(
            level=level.strip().upper() or "INFO",
            message=message,
            correlation_id=correlation_id,
            fields=dict(fields or {}),
        )
        with self._lock:
            self._records.append(record)
            if len(self._records) > self._max:
                self._records = self._records[-self._max :]

    def list_records(self) -> tuple[LogRecord, ...]:
        with self._lock:
            return tuple(self._records)

    def clear(self) -> None:
        with self._lock:
            self._records.clear()


class StdlibLoggingPort:
    """Forward structured fields to stdlib ``logging``."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("production_platform")

    def log(
        self,
        level: str,
        message: str,
        *,
        correlation_id: str | None = None,
        fields: dict[str, Any] | None = None,
    ) -> None:
        extra = dict(fields or {})
        if correlation_id:
            extra["correlation_id"] = correlation_id
        lvl = getattr(logging, level.strip().upper(), logging.INFO)
        self._logger.log(lvl, message, extra={"prod_fields": extra})


def ensure_logging_port(port: LoggingPort | None) -> LoggingPort:
    return port if port is not None else InMemoryLoggingPort()
