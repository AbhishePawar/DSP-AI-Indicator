"""Prometheus-ready metrics exposition (PEP-003)."""

from __future__ import annotations

from typing import Any

from production_platform.production.exceptions import ProviderError
from production_platform.production.interfaces import MetricsPort
from production_platform.production.metrics import InMemoryMetricsPort

__all__ = [
    "PrometheusTextRenderer",
    "render_prometheus",
    "try_build_prometheus_client_metrics",
]


class PrometheusTextRenderer:
    """Render MetricsPort snapshots as Prometheus text exposition format 0.0.4."""

    def __init__(self, metrics: MetricsPort, *, namespace: str = "dsp") -> None:
        self._metrics = metrics
        self._ns = namespace.strip("_") or "dsp"

    def render(self) -> str:
        snap_fn = getattr(self._metrics, "snapshot", None)
        if not callable(snap_fn):
            return f"# HELP {self._ns}_up DSP observability\n# TYPE {self._ns}_up gauge\n{self._ns}_up 1\n"
        snap = snap_fn()
        lines: list[str] = [
            f"# HELP {self._ns}_up DSP observability adapter up",
            f"# TYPE {self._ns}_up gauge",
            f"{self._ns}_up 1",
        ]
        counters = snap.get("counters", {}) if isinstance(snap, dict) else {}
        gauges = snap.get("gauges", {}) if isinstance(snap, dict) else {}
        timings = snap.get("timings", {}) if isinstance(snap, dict) else {}

        for key, value in sorted(counters.items()):
            name, labels = _split_key(str(key))
            metric = _prom_name(self._ns, name, "_total")
            lines.append(f"# TYPE {metric} counter")
            lines.append(f"{metric}{labels} {float(value)}")

        for key, value in sorted(gauges.items()):
            name, labels = _split_key(str(key))
            metric = _prom_name(self._ns, name, "")
            lines.append(f"# TYPE {metric} gauge")
            lines.append(f"{metric}{labels} {float(value)}")

        for key, samples in sorted(timings.items()):
            name, labels = _split_key(str(key))
            metric = _prom_name(self._ns, name, "_ms")
            vals = list(samples) if isinstance(samples, list) else []
            if not vals:
                continue
            lines.append(f"# TYPE {metric} summary")
            lines.append(f"{metric}_count{labels} {len(vals)}")
            lines.append(f"{metric}_sum{labels} {sum(float(v) for v in vals)}")
        return "\n".join(lines) + "\n"


def render_prometheus(metrics: MetricsPort, *, namespace: str = "dsp") -> str:
    return PrometheusTextRenderer(metrics, namespace=namespace).render()


def try_build_prometheus_client_metrics() -> MetricsPort | None:
    """Optional prometheus_client-backed MetricsPort (lazy import)."""
    import importlib

    try:
        prom = importlib.import_module("prometheus_client")
    except ImportError:
        return None
    try:
        return _PrometheusClientMetricsPort(prom)
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"prometheus_client init failed: {exc}") from exc


class _PrometheusClientMetricsPort:
    def __init__(self, prom: Any) -> None:
        self._prom = prom
        self._registry = prom.CollectorRegistry()
        self._counters: dict[str, Any] = {}
        self._gauges: dict[str, Any] = {}
        self._summaries: dict[str, Any] = {}
        self._fallback = InMemoryMetricsPort()

    def incr(self, name: str, value: float = 1.0, *, tags: dict[str, str] | None = None) -> None:
        self._fallback.incr(name, value, tags=tags)
        counter = self._counters.get(name)
        if counter is None:
            counter = self._prom.Counter(
                _safe_metric(name), name, labelnames=sorted((tags or {}).keys()) or (),
                registry=self._registry,
            )
            self._counters[name] = counter
        if tags:
            counter.labels(**tags).inc(value)
        else:
            counter.inc(value)

    def gauge(self, name: str, value: float, *, tags: dict[str, str] | None = None) -> None:
        self._fallback.gauge(name, value, tags=tags)
        gauge = self._gauges.get(name)
        if gauge is None:
            gauge = self._prom.Gauge(
                _safe_metric(name), name, labelnames=sorted((tags or {}).keys()) or (),
                registry=self._registry,
            )
            self._gauges[name] = gauge
        if tags:
            gauge.labels(**tags).set(value)
        else:
            gauge.set(value)

    def timing(self, name: str, ms: float, *, tags: dict[str, str] | None = None) -> None:
        self._fallback.timing(name, ms, tags=tags)
        summary = self._summaries.get(name)
        if summary is None:
            summary = self._prom.Summary(
                _safe_metric(name) + "_ms", name, labelnames=sorted((tags or {}).keys()) or (),
                registry=self._registry,
            )
            self._summaries[name] = summary
        if tags:
            summary.labels(**tags).observe(ms)
        else:
            summary.observe(ms)

    def snapshot(self) -> dict[str, object]:
        return self._fallback.snapshot()

    def render(self) -> str:
        return self._prom.generate_latest(self._registry).decode("utf-8")


def _split_key(key: str) -> tuple[str, str]:
    if "|" not in key:
        return key, ""
    name, tag_part = key.split("|", 1)
    pairs = []
    for item in tag_part.split(","):
        if "=" in item:
            k, v = item.split("=", 1)
            pairs.append(f'{k}="{v}"')
    if not pairs:
        return name, ""
    return name, "{" + ",".join(pairs) + "}"


def _prom_name(namespace: str, name: str, suffix: str) -> str:
    cleaned = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
    return f"{namespace}_{cleaned}{suffix}"


def _safe_metric(name: str) -> str:
    return "".join(c if c.isalnum() or c == "_" else "_" for c in name)
