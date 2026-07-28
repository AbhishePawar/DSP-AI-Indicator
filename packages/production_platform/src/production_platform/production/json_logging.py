"""Structured JSON logging adapters (PEP-003 / CERT-In posture)."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any, TextIO

from production_platform.production.correlation import get_correlation_id
from production_platform.production.interfaces import LoggingPort

__all__ = ["JsonLoggingPort", "ObservabilityLogEvent", "FanoutLoggingPort"]


@dataclass(frozen=True, slots=True)
class ObservabilityLogEvent:
    """JSON-serialisable structured log event."""

    timestamp: str
    level: str
    message: str
    correlation_id: str | None
    service: str
    fields: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "timestamp": self.timestamp,
            "level": self.level,
            "message": self.message,
            "service": self.service,
        }
        if self.correlation_id:
            payload["correlation_id"] = self.correlation_id
        if self.fields:
            payload["fields"] = self.fields
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True)


class JsonLoggingPort:
    """Emit one JSON object per line — CERT-In friendly structured logs."""

    def __init__(
        self,
        *,
        service_name: str = "dsp-ai-indicator",
        stream: TextIO | None = None,
        capture: bool = True,
        max_records: int = 2000,
    ) -> None:
        self._service = service_name
        self._stream = stream if stream is not None else sys.stdout
        self._capture = capture
        self._max = max(1, max_records)
        self._records: list[ObservabilityLogEvent] = []
        self._lock = Lock()

    def log(
        self,
        level: str,
        message: str,
        *,
        correlation_id: str | None = None,
        fields: dict[str, Any] | None = None,
    ) -> None:
        cid = correlation_id if correlation_id is not None else get_correlation_id()
        event = ObservabilityLogEvent(
            timestamp=datetime.now(tz=UTC).isoformat(),
            level=level.strip().upper() or "INFO",
            message=message,
            correlation_id=cid,
            service=self._service,
            fields=dict(fields or {}),
        )
        line = event.to_json()
        try:
            self._stream.write(line + "\n")
            if hasattr(self._stream, "flush"):
                self._stream.flush()
        except Exception:
            pass
        if self._capture:
            with self._lock:
                self._records.append(event)
                if len(self._records) > self._max:
                    self._records = self._records[-self._max :]

    def list_events(self) -> tuple[ObservabilityLogEvent, ...]:
        with self._lock:
            return tuple(self._records)


class FanoutLoggingPort:
    """Fan-out LoggingPort to multiple sinks."""

    def __init__(self, *ports: LoggingPort) -> None:
        self._ports = ports

    def log(
        self,
        level: str,
        message: str,
        *,
        correlation_id: str | None = None,
        fields: dict[str, Any] | None = None,
    ) -> None:
        for port in self._ports:
            port.log(
                level, message, correlation_id=correlation_id, fields=fields
            )
