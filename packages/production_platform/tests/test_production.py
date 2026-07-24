"""Production platform tests (K1.3)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from production_platform import (
    Environment,
    FeatureFlagManager,
    InMemoryCachePort,
    InMemoryMetricsPort,
    ProductionBundle,
    ProductionConfiguration,
    ProductionError,
    __version__,
    new_correlation_id,
)

_SRC = Path(__file__).resolve().parents[1] / "src" / "production_platform"
_FORBIDDEN = frozenset(
    {
        "redis",
        "prometheus_client",
        "opentelemetry",
        "boto3",
        "botocore",
        "azure",
        "google",
        "celery",
        "rq",
        "dsp_platform",
        "api_platform",
        "security_platform",
        "valuation",
        "recommendation",
        "workflow",
        "copilot",
    }
)


def _imported_top_levels(source: str) -> frozenset[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.add(node.module.split(".", 1)[0])
    return frozenset(names)


class TestVersionAndArchitecture:
    def test_version(self) -> None:
        assert __version__ == "0.1.0"

    def test_no_vendor_imports(self) -> None:
        violations: list[str] = []
        for path in _SRC.rglob("*.py"):
            bad = _imported_top_levels(path.read_text(encoding="utf-8")) & _FORBIDDEN
            if bad:
                violations.append(f"{path.name}: {sorted(bad)}")
        assert violations == []


class TestBundle:
    def test_create_defaults(self) -> None:
        bundle = ProductionBundle.create(
            configuration=ProductionConfiguration(
                environment=Environment.TEST,
                service_name="dsp-test",
                service_version="0.0.0",
            ),
            feature_flags={"beta_ui": True, "legacy_path": False},
        )
        assert bundle.health().ready is True
        assert bundle.readiness().ready is True
        assert bundle.liveness().live is True
        cfg = bundle.get_configuration()
        assert cfg.environment is Environment.TEST
        assert bundle.get_feature_flags()["beta_ui"] is True
        meta = bundle.get_metadata()
        assert meta.package_version == "0.1.0"
        assert meta.service_name == "dsp-test"

    def test_diagnostics(self) -> None:
        bundle = ProductionBundle.create()
        report = bundle.diagnostics()
        assert report.health.ready is True
        assert report.metadata.package_version == "0.1.0"
        assert report.metrics_snapshot is not None

    def test_metrics_and_logging(self) -> None:
        bundle = ProductionBundle.create()
        cid = new_correlation_id()
        bundle.logging.log("INFO", "hello", correlation_id=cid, fields={"k": "v"})
        bundle.metrics.incr("requests", tags={"route": "health"})
        bundle.metrics.gauge("queue_depth", 3)
        bundle.metrics.timing("latency_ms", 12.5)
        snap = bundle.get_metrics()
        assert snap["sample_count"] >= 3
        records = bundle.logging.list_records()  # type: ignore[attr-defined]
        assert records[-1].correlation_id == cid

    def test_cache_storage_scheduler(self) -> None:
        bundle = ProductionBundle.create()
        bundle.cache.set("a", 1, ttl_seconds=60)
        assert bundle.cache.get("a") == 1
        bundle.storage.put("obj", b"payload", content_type="text/plain")
        assert bundle.storage.get("obj") == b"payload"
        bundle.scheduler.schedule("job-1", delay_seconds=0)
        assert "job-1" in bundle.scheduler.list_jobs()
        bundle.scheduler.cancel("job-1")
        assert "job-1" not in bundle.scheduler.list_jobs()

    def test_tracing(self) -> None:
        bundle = ProductionBundle.create()
        span = bundle.tracing.start_span("op", correlation_id="c1")
        bundle.tracing.annotate(span, "step", "1")
        bundle.tracing.end_span(span, status="ok")
        spans = bundle.tracing.list_spans()  # type: ignore[attr-defined]
        assert spans[0].status == "ok"

    def test_custom_ports_injected(self) -> None:
        metrics = InMemoryMetricsPort()
        cache = InMemoryCachePort()
        bundle = ProductionBundle.create(metrics=metrics, cache=cache)
        assert bundle.metrics is metrics
        assert bundle.cache is cache

    def test_feature_flag_manager(self) -> None:
        mgr = FeatureFlagManager({"x": True})
        assert mgr.is_enabled("x") is True
        assert mgr.is_enabled("missing", default=False) is False
        mgr.set("y", False, description="off")
        assert mgr.get("y") is not None

    def test_scheduler_rejects_empty_job(self) -> None:
        bundle = ProductionBundle.create()
        with pytest.raises(ProductionError):
            bundle.scheduler.schedule("  ")

    def test_configuration_validation(self) -> None:
        with pytest.raises(Exception):
            ProductionConfiguration(service_name="")
