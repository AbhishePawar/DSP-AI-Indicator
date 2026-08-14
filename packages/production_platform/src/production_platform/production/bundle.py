"""ProductionBundle — operational composition root (K1.3 + PEP-002 + PEP-003)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from production_platform.production.cache import ensure_cache_port
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
from production_platform.production.infrastructure import InfrastructureBundle
from production_platform.production.interfaces import (
    CachePort,
    LoggingPort,
    MetricsPort,
    SchedulerPort,
    SecretsPort,
    StoragePort,
    TracingPort,
)
from production_platform.production.logging import ensure_logging_port
from production_platform.production.metrics import ensure_metrics_port
from production_platform.production.observability import (
    ObservabilityBundle,
    ObservabilitySettings,
)
from production_platform.production.scheduler import ensure_scheduler_port
from production_platform.production.storage import ensure_storage_port
from production_platform.production.tracing import ensure_tracing_port

__all__ = ["ProductionBundle"]

_PACKAGE_VERSION = "0.3.0"


@dataclass
class ProductionBundle:
    """Provider-neutral operational façade.

    Exposes health / readiness / diagnostics / configuration / flags / metrics
    without business logic. Optional infrastructure + observability bundles.
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
    infrastructure: InfrastructureBundle | None = None
    observability: ObservabilityBundle | None = None

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
        infrastructure: InfrastructureBundle | None = None,
        with_infrastructure: bool = False,
        observability: ObservabilityBundle | None = None,
        with_observability: bool = False,
        observability_settings: ObservabilitySettings | None = None,
    ) -> ProductionBundle:
        """Build a bundle with in-memory defaults unless ports are injected."""
        infra = infrastructure
        if infra is None and with_infrastructure:
            infra = InfrastructureBundle.create_offline(
                configuration=configuration, secrets=secrets
            )

        obs = observability
        if obs is None and with_observability:
            svc = (configuration or ProductionConfiguration()).service_name
            obs = ObservabilityBundle.create(
                settings=observability_settings
                or ObservabilitySettings(service_name=svc),
                logging=logging,
                metrics=metrics,
                tracing=tracing,
            )

        if infra is not None:
            config_mgr = infra.configuration
            cache_port = ensure_cache_port(cache if cache is not None else infra.cache)
            storage_port = ensure_storage_port(
                storage if storage is not None else infra.storage
            )
            secrets_port = infra.secrets
        else:
            config_mgr = ConfigurationManager(
                configuration or ProductionConfiguration(),
                secrets=secrets if secrets is not None else InMemorySecretsPort(),
            )
            cache_port = ensure_cache_port(cache)
            storage_port = ensure_storage_port(storage)
            secrets_port = config_mgr.secrets

        _ = secrets_port
        flags = FeatureFlagManager(feature_flags)

        if obs is not None:
            log_port = ensure_logging_port(logging if logging is not None else obs.logging)
            metrics_port = ensure_metrics_port(
                metrics if metrics is not None else obs.metrics
            )
            tracing_port = ensure_tracing_port(
                tracing if tracing is not None else obs.tracing
            )
        else:
            log_port = ensure_logging_port(logging)
            metrics_port = ensure_metrics_port(metrics)
            tracing_port = ensure_tracing_port(tracing)

        scheduler_port = ensure_scheduler_port(scheduler)

        extra_checks = ()
        if infra is not None:
            extra_checks = (
                lambda: _infra_db_check(infra),
                lambda: _infra_redis_check(infra),
            )

        health_mgr = HealthManager(
            configuration=config_mgr,
            logging=log_port,
            metrics=metrics_port,
            tracing=tracing_port,
            cache=cache_port,
            storage=storage_port,
            scheduler=scheduler_port,
            extra_checks=extra_checks,
        )
        if obs is not None:
            obs.attach_health(health_mgr)

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
            infrastructure=infra,
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
            infrastructure=infra,
            observability=obs,
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

    def render_prometheus(self) -> str:
        if self.observability is not None:
            return self.observability.render_prometheus()
        from production_platform.production.prometheus_metrics import render_prometheus

        return render_prometheus(self.metrics)

    def get_metadata(self) -> ProductionMetadata:
        return self.diagnostics_manager.metadata()

    @classmethod
    def from_environment(
        cls,
        *,
        environ: dict[str, str] | None = None,
        force_offline: bool = False,
        with_observability: bool = True,
        feature_flags: dict[str, bool] | None = None,
    ) -> ProductionBundle:
        """Compose ProductionBundle from env-driven InfrastructureBundle."""
        from production_platform.production.runtime import build_runtime_infrastructure

        infra = build_runtime_infrastructure(
            environ=environ, force_offline=force_offline
        )
        return cls.create(
            infrastructure=infra,
            with_observability=with_observability,
            feature_flags=feature_flags,
        )


def _infra_db_check(infra: InfrastructureBundle):  # type: ignore[no-untyped-def]
    from production_platform.production.health import HealthCheckResult, HealthStatus

    ok = infra.database.ping()
    return HealthCheckResult(
        name="database",
        status=HealthStatus.PASS if ok else HealthStatus.FAIL,
        message=f"adapter={infra.diagnostics.database_adapter} ping={'ok' if ok else 'fail'}",
    )


def _infra_redis_check(infra: InfrastructureBundle):  # type: ignore[no-untyped-def]
    from production_platform.production.health import HealthCheckResult, HealthStatus

    probes = infra.health_checks().get("redis", {})
    status_raw = str(probes.get("status", "skip"))
    if status_raw == "pass":
        status = HealthStatus.PASS
    elif status_raw == "fail":
        status = HealthStatus.FAIL
    else:
        status = HealthStatus.SKIP
    return HealthCheckResult(
        name="redis_stack",
        status=status,
        message=(
            f"status={status_raw} cache={infra.diagnostics.cache_adapter} "
            f"fallback={infra.diagnostics.redis_fallback_active}"
        ),
    )
