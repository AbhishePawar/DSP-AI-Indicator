"""OpenTelemetry-ready tracing adapter (PEP-003) — lazy vendor import."""

from __future__ import annotations

import importlib
from typing import Any

from production_platform.production.exceptions import ProviderError
from production_platform.production.interfaces import TracingPort
from production_platform.production.tracing import InMemoryTracingPort

__all__ = ["OpenTelemetryTracingPort", "try_build_otel_tracing"]


class OpenTelemetryTracingPort:
    """TracingPort backed by OpenTelemetry when installed; else ProviderError on use."""

    def __init__(self, *, tracer_name: str = "dsp-ai-indicator") -> None:
        try:
            otel_trace = importlib.import_module("opentelemetry.trace")
        except ImportError as exc:
            raise ProviderError(
                "opentelemetry is not installed; pip install 'production-platform[otel]'"
            ) from exc
        self._otel_trace = otel_trace
        self._tracer = otel_trace.get_tracer(tracer_name)
        self._spans: dict[str, Any] = {}
        self._fallback = InMemoryTracingPort()

    def start_span(self, name: str, *, correlation_id: str | None = None) -> str:
        span_id = self._fallback.start_span(name, correlation_id=correlation_id)
        span = self._tracer.start_span(name)
        if correlation_id:
            span.set_attribute("correlation_id", correlation_id)
        self._spans[span_id] = span
        return span_id

    def end_span(self, span_id: str, *, status: str = "ok") -> None:
        self._fallback.end_span(span_id, status=status)
        span = self._spans.pop(span_id, None)
        if span is None:
            return
        if status != "ok":
            span.set_status(self._otel_trace.Status(self._otel_trace.StatusCode.ERROR))
        else:
            span.set_status(self._otel_trace.Status(self._otel_trace.StatusCode.OK))
        span.end()

    def annotate(self, span_id: str, key: str, value: str) -> None:
        self._fallback.annotate(span_id, key, value)
        span = self._spans.get(span_id)
        if span is not None:
            span.set_attribute(key, value)

    def list_spans(self):
        return self._fallback.list_spans()


def try_build_otel_tracing(*, tracer_name: str = "dsp-ai-indicator") -> TracingPort | None:
    try:
        return OpenTelemetryTracingPort(tracer_name=tracer_name)
    except ProviderError:
        return None
    except Exception:
        return None
