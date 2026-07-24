"""Metrics — in-memory provider-neutral adapter."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock

from production_platform.production.interfaces import MetricsPort

__all__ = ["InMemoryMetricsPort", "MetricSample"]


@dataclass(frozen=True, slots=True)
class MetricSample:
    kind: str
    name: str
    value: float
    tags: dict[str, str] = field(default_factory=dict)


class InMemoryMetricsPort:
    """Process-local metrics store — not Prometheus."""

    def __init__(self) -> None:
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._timings: dict[str, list[float]] = defaultdict(list)
        self._samples: list[MetricSample] = []
        self._lock = Lock()

    def incr(
        self, name: str, value: float = 1.0, *, tags: dict[str, str] | None = None
    ) -> None:
        key = _key(name, tags)
        with self._lock:
            self._counters[key] += value
            self._samples.append(
                MetricSample("counter", name, value, dict(tags or {}))
            )

    def gauge(
        self, name: str, value: float, *, tags: dict[str, str] | None = None
    ) -> None:
        key = _key(name, tags)
        with self._lock:
            self._gauges[key] = value
            self._samples.append(
                MetricSample("gauge", name, value, dict(tags or {}))
            )

    def timing(
        self, name: str, ms: float, *, tags: dict[str, str] | None = None
    ) -> None:
        key = _key(name, tags)
        with self._lock:
            self._timings[key].append(ms)
            self._samples.append(
                MetricSample("timing", name, ms, dict(tags or {}))
            )

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "timings": {k: list(v) for k, v in self._timings.items()},
                "sample_count": len(self._samples),
            }

    def list_samples(self) -> tuple[MetricSample, ...]:
        with self._lock:
            return tuple(self._samples)


def _key(name: str, tags: dict[str, str] | None) -> str:
    if not tags:
        return name
    parts = ",".join(f"{k}={tags[k]}" for k in sorted(tags))
    return f"{name}|{parts}"


def ensure_metrics_port(port: MetricsPort | None) -> MetricsPort:
    return port if port is not None else InMemoryMetricsPort()
