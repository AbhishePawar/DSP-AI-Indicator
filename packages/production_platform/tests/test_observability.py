"""PEP-003 observability contract tests."""

from __future__ import annotations

import json

import pytest

from production_platform import (
    ConfigurationError,
    HealthManager,
    InMemoryLoggingPort,
    InMemoryMetricsPort,
    InMemoryTracingPort,
    ObservabilityBundle,
    ObservabilitySettings,
    ProductionBundle,
    ProductionConfiguration,
    Environment,
    correlation_context,
    get_correlation_id,
    render_prometheus,
    try_build_otel_tracing,
    try_build_prometheus_client_metrics,
)


class TestCorrelation:
    def test_context_binds_id(self) -> None:
        assert get_correlation_id() is None
        with correlation_context("corr_test") as cid:
            assert cid == "corr_test"
            assert get_correlation_id() == "corr_test"
        assert get_correlation_id() is None


class TestJsonLogging:
    def test_structured_json_event(self) -> None:
        obs = ObservabilityBundle.create(
            settings=ObservabilitySettings(service_name="dsp-test")
        )
        with obs.request_context("corr_abc"):
            obs.logging.log("INFO", "hello", fields={"route": "/health"})
        # Fanout includes JsonLoggingPort with capture
        from production_platform.production.json_logging import FanoutLoggingPort

        assert isinstance(obs.logging, FanoutLoggingPort)
        json_port = obs.logging._ports[1]  # noqa: SLF001
        events = json_port.list_events()
        assert events
        payload = json.loads(events[-1].to_json())
        assert payload["message"] == "hello"
        assert payload["correlation_id"] == "corr_abc"
        assert payload["service"] == "dsp-test"
        assert payload["fields"]["route"] == "/health"


class TestMetricsPrometheus:
    def test_render_prometheus_text(self) -> None:
        metrics = InMemoryMetricsPort()
        metrics.incr("http_requests", tags={"route": "health"})
        metrics.gauge("queue_depth", 2)
        metrics.timing("latency_ms", 12.5)
        text = render_prometheus(metrics)
        assert "dsp_up 1" in text
        assert "http_requests" in text
        assert "queue_depth" in text
        assert "TYPE" in text

    def test_optional_prometheus_client(self) -> None:
        # May be None when package absent — must not raise.
        port = try_build_prometheus_client_metrics()
        assert port is None or hasattr(port, "incr")


class TestTracingOtel:
    def test_memory_tracing_contract(self) -> None:
        tracing = InMemoryTracingPort()
        span = tracing.start_span("op", correlation_id="c1")
        tracing.annotate(span, "k", "v")
        tracing.end_span(span, status="ok")
        spans = tracing.list_spans()
        assert spans[0].status == "ok"
        assert spans[0].annotations["k"] == "v"

    def test_optional_otel(self) -> None:
        port = try_build_otel_tracing()
        assert port is None or hasattr(port, "start_span")


class TestAuditPipeline:
    def test_audit_emit_and_list(self) -> None:
        obs = ObservabilityBundle.create()
        obs.audit.emit(
            action="login_success",
            subject="usr_admin",
            success=True,
            detail="password",
            correlation_id="corr_1",
        )
        events = obs.audit.list_events()
        assert events
        assert events[-1].action == "login_success"
        assert events[-1].correlation_id == "corr_1"


class TestHealthPort:
    def test_health_attached(self) -> None:
        bundle = ProductionBundle.create(
            configuration=ProductionConfiguration(environment=Environment.TEST),
            with_observability=True,
        )
        assert bundle.observability is not None
        assert bundle.observability.health is not None
        assert bundle.liveness().live is True
        assert bundle.readiness().ready is True
        assert bundle.health().ready is True


class TestObservabilitySettings:
    def test_cert_in_retention_floor(self) -> None:
        with pytest.raises(ConfigurationError):
            ObservabilitySettings(cert_in_log_retention_days=30)


class TestProductionBundlePrometheus:
    def test_render_via_bundle(self) -> None:
        bundle = ProductionBundle.create(with_observability=True)
        bundle.metrics.incr("requests")
        text = bundle.render_prometheus()
        assert "dsp_up 1" in text
        assert bundle.get_metadata().package_version == "0.3.0"
