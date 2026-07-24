"""Diagnostics snapshots — immutable operational metadata."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from production_platform.production.configuration import ConfigurationManager
from production_platform.production.feature_flags import FeatureFlagManager
from production_platform.production.health import HealthManager, HealthReport
from production_platform.production.interfaces import (
    CachePort,
    LoggingPort,
    MetricsPort,
    SchedulerPort,
    StoragePort,
    TracingPort,
)

__all__ = ["DiagnosticsManager", "DiagnosticsReport", "ProductionMetadata"]


@dataclass(frozen=True, slots=True)
class ProductionMetadata:
    """Immutable production identity metadata."""

    service_name: str
    service_version: str
    environment: str
    region: str
    package_version: str
    ports: tuple[str, ...]
    generated_at: datetime


@dataclass(frozen=True, slots=True)
class DiagnosticsReport:
    """Immutable diagnostics envelope."""

    metadata: ProductionMetadata
    health: HealthReport
    feature_flags: dict[str, bool]
    metrics_snapshot: dict[str, object] | None
    notes: tuple[str, ...] = ()


class DiagnosticsManager:
    """Builds diagnostics without inspecting business domains."""

    def __init__(
        self,
        *,
        configuration: ConfigurationManager,
        health: HealthManager,
        feature_flags: FeatureFlagManager,
        metrics: MetricsPort,
        tracing: TracingPort,
        cache: CachePort,
        storage: StoragePort,
        scheduler: SchedulerPort,
        logging: LoggingPort,
        package_version: str,
    ) -> None:
        self._configuration = configuration
        self._health = health
        self._feature_flags = feature_flags
        self._metrics = metrics
        self._tracing = tracing
        self._cache = cache
        self._storage = storage
        self._scheduler = scheduler
        self._logging = logging
        self._package_version = package_version

    def metadata(self) -> ProductionMetadata:
        cfg = self._configuration.get()
        return ProductionMetadata(
            service_name=cfg.service_name,
            service_version=cfg.service_version,
            environment=cfg.environment.value,
            region=cfg.region,
            package_version=self._package_version,
            ports=(
                f"logging={type(self._logging).__name__}",
                f"metrics={type(self._metrics).__name__}",
                f"tracing={type(self._tracing).__name__}",
                f"cache={type(self._cache).__name__}",
                f"storage={type(self._storage).__name__}",
                f"scheduler={type(self._scheduler).__name__}",
            ),
            generated_at=datetime.now(tz=UTC),
        )

    def run(self) -> DiagnosticsReport:
        metrics_snapshot: dict[str, object] | None = None
        snap = getattr(self._metrics, "snapshot", None)
        if callable(snap):
            metrics_snapshot = snap()  # type: ignore[misc]
        return DiagnosticsReport(
            metadata=self.metadata(),
            health=self._health.health(),
            feature_flags=self._feature_flags.as_dict(),
            metrics_snapshot=metrics_snapshot,
            notes=(
                "Provider-neutral in-memory defaults; replace ports with adapters.",
            ),
        )
