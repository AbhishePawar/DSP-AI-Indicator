"""Tracing — in-memory provider-neutral adapter."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock

from production_platform.production.interfaces import TracingPort

__all__ = ["InMemoryTracingPort", "SpanRecord"]


@dataclass
class SpanRecord:
    span_id: str
    name: str
    correlation_id: str | None
    status: str | None = None
    annotations: dict[str, str] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    ended_at: datetime | None = None


class InMemoryTracingPort:
    """Process-local span store — not OpenTelemetry."""

    def __init__(self) -> None:
        self._spans: dict[str, SpanRecord] = {}
        self._lock = Lock()

    def start_span(self, name: str, *, correlation_id: str | None = None) -> str:
        span_id = f"span_{uuid.uuid4().hex[:16]}"
        with self._lock:
            self._spans[span_id] = SpanRecord(
                span_id=span_id,
                name=name,
                correlation_id=correlation_id,
            )
        return span_id

    def end_span(self, span_id: str, *, status: str = "ok") -> None:
        with self._lock:
            span = self._spans.get(span_id)
            if span is None:
                return
            span.status = status
            span.ended_at = datetime.now(tz=UTC)

    def annotate(self, span_id: str, key: str, value: str) -> None:
        with self._lock:
            span = self._spans.get(span_id)
            if span is None:
                return
            span.annotations[key] = value

    def list_spans(self) -> tuple[SpanRecord, ...]:
        with self._lock:
            return tuple(self._spans[k] for k in sorted(self._spans))


def ensure_tracing_port(port: TracingPort | None) -> TracingPort:
    return port if port is not None else InMemoryTracingPort()
