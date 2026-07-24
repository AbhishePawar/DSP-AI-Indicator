"""ProductionBundle — operational composition root (K1.3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from production_platform.production.cache import InMemoryCachePort, ensure_cache_port
from production_platform.production.configuration import (
    ConfigurationManager,
    InMemorySecretsPort,
    ProductionConfiguration,
)
from production_platform.production.diagnostics import (
    DiagnosticsManager,
    DiagnosticsReport,
    ProductionMetadata,
)
from production_platform.production.feature_flags import FeatureFlagManager
from production_platform.production.health import HealthManager, HealthReport
from production_platform.production.interfaces import (
    CachePort,
    LoggingPort,
    MetricsPort,
    SchedulerPort,
    SecretsPort,
    StoragePort,
    TracingPort,
)
from production_platform.production.logging import (
    InMemoryLoggingPort,
    ensure_logging_port,
)
from production_platform.production.metrics import (
    InMemoryMetricsPort,
    ensure_metrics_port,
)
from production_platform.production.scheduler import (
    InMemorySchedulerPort,
    ensure_scheduler_port,
)
from production_platform.production.storage import (
    InMemoryStoragePort,
    ensure_storage_port,
)
from production_platform.production.tracing import (
    InMemoryTracingPort,
    ensure_tracing_port,
)

__all__ = ["ProductionBundle"]

_PACKAGE_VERSION = "0.1.0"


@dataclass
class ProductionBundle:
    """Provider-neutral operational façade.

    Exposes health / readiness / diagnostics / configuration / flags / metrics
    without business logic or vendor SDKs.
    """

    configuration: ConfigurationManager
    feature_flags: FeatureFlagManager
    logging: LoggingPort
    metrics: MetricsPort
    tracing: TracingPort
    cache: CachePort
    storage: StoragePort
    scheduler: SchedulerPort
    health_manager: HealthManager
    diagnostics_manager: DiagnosticsManager

    @classmethod
    def create(
        cls,
        *,
        configuration: ProductionConfiguration | None = None,
        secrets: SecretsPort | None = None,
        feature_flags: dict[str, bool] | None = None,
        logging: LoggingPort | None = None,
        metrics: MetricsPort | None = None,
        tracing: TracingPort | None = None,
        cache: CachePort | None = None,
        storage: StoragePort | None = None,
        scheduler: SchedulerPort | None = None,
    ) -> ProductionBundle:
        """Build a bundle with in-memory defaults unless ports are injected."""
        config_mgr = ConfigurationManager(
            configuration or ProductionConfiguration(),
            secrets=secrets if secrets is not None else InMemorySecretsPort(),
        )
        flags = FeatureFlagManager(feature_flags)
        log_port = ensure_logging_port(logging)
        metrics_port = ensure_metrics_port(metrics)
        tracing_port = ensure_tracing_port(tracing)
        cache_port = ensure_cache_port(cache)
        storage_port = ensure_storage_port(storage)
        scheduler_port = ensure_scheduler_port(scheduler)

        health_mgr = HealthManager(
            configuration=config_mgr,
            logging=log_port,
            metrics=metrics_port,
            tracing=tracing_port,
            cache=cache_port,
            storage=storage_port,
            scheduler=scheduler_port,
        )
        diagnostics_mgr = DiagnosticsManager(
            configuration=config_mgr,
            health=health_mgr,
            feature_flags=flags,
            metrics=metrics_port,
            tracing=tracing_port,
            cache=cache_port,
            storage=storage_port,
            scheduler=scheduler_port,
            logging=log_port,
            package_version=_PACKAGE_VERSION,
        )
        return cls(
            configuration=config_mgr,
            feature_flags=flags,
            logging=log_port,
            metrics=metrics_port,
            tracing=tracing_port,
            cache=cache_port,
            storage=storage_port,
            scheduler=scheduler_port,
            health_manager=health_mgr,
            diagnostics_manager=diagnostics_mgr,
        )

    def health(self) -> HealthReport:
        return self.health_manager.health()

    def readiness(self) -> HealthReport:
        return self.health_manager.readiness()

    def liveness(self) -> HealthReport:
        return self.health_manager.liveness()

    def diagnostics(self) -> DiagnosticsReport:
        return self.diagnostics_manager.run()

    def get_configuration(self) -> ProductionConfiguration:
        return self.configuration.get()

    def get_feature_flags(self) -> dict[str, bool]:
        return self.feature_flags.as_dict()

    def get_metrics(self) -> dict[str, Any]:
        snap = getattr(self.metrics, "snapshot", None)
        if callable(snap):
            return snap()  # type: ignore[no-any-return, misc]
        return {"adapter": type(self.metrics).__name__}

    def get_metadata(self) -> ProductionMetadata:
        return self.diagnostics_manager.metadata()
