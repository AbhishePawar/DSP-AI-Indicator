"""Health and readiness aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Callable

from production_platform.production.configuration import ConfigurationManager
from production_platform.production.interfaces import (
    CachePort,
    LoggingPort,
    MetricsPort,
    SchedulerPort,
    StoragePort,
    TracingPort,
)

__all__ = [
    "HealthCheckResult",
    "HealthManager",
    "HealthReport",
    "HealthStatus",
]


class HealthStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


@dataclass(frozen=True, slots=True)
class HealthCheckResult:
    name: str
    status: HealthStatus
    message: str


@dataclass(frozen=True, slots=True)
class HealthReport:
    ready: bool
    live: bool
    status: HealthStatus
    checks: tuple[HealthCheckResult, ...]
    checked_at: datetime
    service_name: str
    service_version: str


CheckFn = Callable[[], HealthCheckResult]


class HealthManager:
    """Aggregates port presence + custom checks — no business probes."""

    def __init__(
        self,
        *,
        configuration: ConfigurationManager,
        logging: LoggingPort,
        metrics: MetricsPort,
        tracing: TracingPort,
        cache: CachePort,
        storage: StoragePort,
        scheduler: SchedulerPort,
        extra_checks: tuple[CheckFn, ...] = (),
    ) -> None:
        self._configuration = configuration
        self._logging = logging
        self._metrics = metrics
        self._tracing = tracing
        self._cache = cache
        self._storage = storage
        self._scheduler = scheduler
        self._extra = extra_checks

    def liveness(self) -> HealthReport:
        """Process is up — does not require external adapters."""
        cfg = self._configuration.get()
        checks = (
            HealthCheckResult(
                name="process",
                status=HealthStatus.PASS,
                message="production bundle loaded",
            ),
            HealthCheckResult(
                name="configuration",
                status=HealthStatus.PASS,
                message=f"environment={cfg.environment.value}",
            ),
        )
        return HealthReport(
            ready=True,
            live=True,
            status=HealthStatus.PASS,
            checks=checks,
            checked_at=datetime.now(tz=UTC),
            service_name=cfg.service_name,
            service_version=cfg.service_version,
        )

    def readiness(self) -> HealthReport:
        """Ports registered and configuration valid."""
        checks: list[HealthCheckResult] = [
            self._check_configuration(),
            self._check_port("logging", self._logging),
            self._check_port("metrics", self._metrics),
            self._check_port("tracing", self._tracing),
            self._check_port("cache", self._cache),
            self._check_port("storage", self._storage),
            self._check_port("scheduler", self._scheduler),
        ]
        for fn in self._extra:
            checks.append(fn())
        failed = any(c.status is HealthStatus.FAIL for c in checks)
        status = HealthStatus.FAIL if failed else HealthStatus.PASS
        cfg = self._configuration.get()
        return HealthReport(
            ready=not failed,
            live=True,
            status=status,
            checks=tuple(checks),
            checked_at=datetime.now(tz=UTC),
            service_name=cfg.service_name,
            service_version=cfg.service_version,
        )

    def health(self) -> HealthReport:
        """Alias for readiness (operational default)."""
        return self.readiness()

    def _check_configuration(self) -> HealthCheckResult:
        try:
            self._configuration.validate()
        except Exception as exc:  # noqa: BLE001
            return HealthCheckResult(
                name="configuration",
                status=HealthStatus.FAIL,
                message=str(exc),
            )
        cfg = self._configuration.get()
        return HealthCheckResult(
            name="configuration",
            status=HealthStatus.PASS,
            message=f"environment={cfg.environment.value}",
        )

    def _check_port(self, name: str, port: object) -> HealthCheckResult:
        if port is None:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.FAIL,
                message="port not registered",
            )
        return HealthCheckResult(
            name=name,
            status=HealthStatus.PASS,
            message=f"adapter={type(port).__name__}",
        )
