"""Observability composition root (PEP-003)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from production_platform.production.audit_events import (
    FanoutAuditEventPort,
    InMemoryAuditEventPort,
    LoggingAuditEventPort,
)
from production_platform.production.configuration import (
    ConfigurationManager,
    ProductionConfiguration,
)
from production_platform.production.correlation import (
    correlation_context,
    get_correlation_id,
    new_request_id,
)
from production_platform.production.health import HealthManager
from production_platform.production.interfaces import (
    AuditEventPort,
    HealthPort,
    LoggingPort,
    MetricsPort,
    TracingPort,
)
from production_platform.production.json_logging import FanoutLoggingPort, JsonLoggingPort
from production_platform.production.logging import InMemoryLoggingPort, ensure_logging_port
from production_platform.production.metrics import InMemoryMetricsPort, ensure_metrics_port
from production_platform.production.prometheus_metrics import (
    PrometheusTextRenderer,
    render_prometheus,
    try_build_prometheus_client_metrics,
)
from production_platform.production.otel_tracing import try_build_otel_tracing
from production_platform.production.tracing import InMemoryTracingPort, ensure_tracing_port

__all__ = ["ObservabilityBundle", "ObservabilitySettings"]


@dataclass(frozen=True, slots=True)
class ObservabilitySettings:
    """CERT-In–aligned observability defaults."""

    json_logging: bool = True
    prometheus_namespace: str = "dsp"
    prefer_otel: bool = False
    prefer_prometheus_client: bool = False
    cert_in_log_retention_days: int = 180
    service_name: str = "dsp-ai-indicator"

    def __post_init__(self) -> None:
        from production_platform.production.exceptions import ConfigurationError

        if self.cert_in_log_retention_days < 180:
            raise ConfigurationError(
                "cert_in_log_retention_days must be >= 180 (CERT-In posture)"
            )


@dataclass
class ObservabilityBundle:
    """Resolved observability ports for one process."""

    settings: ObservabilitySettings
    logging: LoggingPort
    metrics: MetricsPort
    tracing: TracingPort
    audit: AuditEventPort
    health: HealthPort | None = None
    notes: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        *,
        settings: ObservabilitySettings | None = None,
        configuration: ConfigurationManager | ProductionConfiguration | None = None,
        logging: LoggingPort | None = None,
        metrics: MetricsPort | None = None,
        tracing: TracingPort | None = None,
        audit: AuditEventPort | None = None,
        health: HealthPort | None = None,
    ) -> ObservabilityBundle:
        cfg = settings or ObservabilitySettings()
        notes: list[str] = []

        memory_log = InMemoryLoggingPort()
        if logging is not None:
            log_port = logging
        elif cfg.json_logging:
            json_log = JsonLoggingPort(
                service_name=cfg.service_name,
                stream=__import__("io").StringIO(),  # capture without noisy stdout in tests
                capture=True,
            )
            log_port = FanoutLoggingPort(memory_log, json_log)
            notes.append("JsonLoggingPort enabled")
        else:
            log_port = memory_log

        metrics_port = ensure_metrics_port(metrics)
        if metrics is None and cfg.prefer_prometheus_client:
            prom = try_build_prometheus_client_metrics()
            if prom is not None:
                metrics_port = prom
                notes.append("prometheus_client MetricsPort active")
            else:
                notes.append("prometheus_client unavailable; using InMemoryMetricsPort")

        tracing_port = ensure_tracing_port(tracing)
        if tracing is None and cfg.prefer_otel:
            otel = try_build_otel_tracing(tracer_name=cfg.service_name)
            if otel is not None:
                tracing_port = otel
                notes.append("OpenTelemetryTracingPort active")
            else:
                notes.append("OpenTelemetry unavailable; using InMemoryTracingPort")

        if audit is not None:
            audit_port = audit
        else:
            audit_port = FanoutAuditEventPort(
                InMemoryAuditEventPort(),
                LoggingAuditEventPort(log_port),
            )

        _ = configuration  # reserved for future retention sink wiring
        return cls(
            settings=cfg,
            logging=ensure_logging_port(log_port),
            metrics=metrics_port,
            tracing=tracing_port,
            audit=audit_port,
            health=health,
            notes=notes,
        )

    def render_prometheus(self) -> str:
        return render_prometheus(
            self.metrics, namespace=self.settings.prometheus_namespace
        )

    def prometheus_renderer(self) -> PrometheusTextRenderer:
        return PrometheusTextRenderer(
            self.metrics, namespace=self.settings.prometheus_namespace
        )

    def request_context(self, request_id: str | None = None):
        """Return correlation_context manager for a request."""
        return correlation_context(request_id or new_request_id())

    def current_correlation_id(self) -> str | None:
        return get_correlation_id()

    def attach_health(self, health: HealthPort) -> None:
        self.health = health

    def diagnostics(self) -> dict[str, Any]:
        return {
            "logging": type(self.logging).__name__,
            "metrics": type(self.metrics).__name__,
            "tracing": type(self.tracing).__name__,
            "audit": type(self.audit).__name__,
            "health": type(self.health).__name__ if self.health else None,
            "cert_in_log_retention_days": self.settings.cert_in_log_retention_days,
            "notes": list(self.notes),
        }
