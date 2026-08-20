"""Health and readiness checks for the platform façade.

Checks are offline: they inspect configuration, feature flags, and
(optionally) an injected provider registry. They never perform live
HTTP or call external APIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from dsp_platform.config import FeatureFlags, PlatformConfig, ProviderSettings
from dsp_platform.exceptions import PlatformError
from dsp_platform.facade import DSPPlatform

__all__ = [
    "CheckStatus",
    "HealthCheckResult",
    "PlatformHealthReport",
    "PlatformHealthService",
]


class CheckStatus(StrEnum):
    """Outcome of a single health check."""

    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


@dataclass(frozen=True, slots=True)
class HealthCheckResult:
    """Result of one named readiness check."""

    name: str
    status: CheckStatus
    message: str


@dataclass(frozen=True, slots=True)
class PlatformHealthReport:
    """Aggregated readiness report for the platform.

    Attributes:
        ready: ``True`` when every *blocking* non-skipped check passed.
            ``investment_data_provider`` may fail without clearing readiness so
            auth/API boot is independent of Upstox/FMP credentials (P1-03 still
            fail-closes on investment use paths).
        status: Overall status (``pass`` if ready else ``fail``).
        checks: Individual check results.
        checked_at: UTC timestamp of the report.
    """

    ready: bool
    status: CheckStatus
    checks: tuple[HealthCheckResult, ...]
    checked_at: datetime


# Capability probes that must remain visible but must not block API readiness.
# Client authentication and process health must boot without investment tokens.
_NON_BLOCKING_READY_CHECKS = frozenset({"investment_data_provider"})


class ProviderRegistryView(Protocol):
    """Minimal registry surface inspected by offline health checks."""

    def list_names(self) -> list[str]: ...

    def get(self, provider_id: str) -> object: ...

    def get_metadata(self, provider_id: str) -> object: ...


class PlatformHealthService:
    """Offline health / readiness probe.

    Args:
        config: Immutable platform configuration to validate.
        platform: Optional façade instance (wiring presence check).
        provider_registry: Optional registry duck-type exposing
            ``list_names``, ``get``, and ``get_metadata`` (typically a
            ``data_engine.ProviderRegistry``). Never contacted over the
            network — only local registration is inspected.
        required_providers: Provider ids that must be registered when a
            registry is supplied. Defaults to enabled provider ids from
            ``config.providers``.
    """

    def __init__(
        self,
        *,
        config: PlatformConfig,
        platform: DSPPlatform | None = None,
        provider_registry: ProviderRegistryView | None = None,
        required_providers: tuple[str, ...] | None = None,
    ) -> None:
        self._config = config
        self._platform = platform
        self._registry = provider_registry
        self._required = required_providers

    def check(self) -> PlatformHealthReport:
        """Run all readiness checks and return an aggregated report."""
        composition = self._check_composition_pipeline()
        checks: list[HealthCheckResult] = [
            self._check_configuration(),
            self._check_feature_flags(),
            self._check_provider_settings(),
            self._check_provider_registry(),
            composition,
            self._check_investment_data_provider(),
            self._check_wiring(
                canonical_ready=composition.status is CheckStatus.PASS
            ),
        ]
        blocking_failed = any(
            c.status is CheckStatus.FAIL
            and c.name not in _NON_BLOCKING_READY_CHECKS
            for c in checks
        )
        # Surface any failure (including investment) in overall status while
        # keeping readiness gated only on blocking checks.
        any_failed = any(c.status is CheckStatus.FAIL for c in checks)
        status = CheckStatus.FAIL if any_failed else CheckStatus.PASS
        return PlatformHealthReport(
            ready=not blocking_failed,
            status=status,
            checks=tuple(checks),
            checked_at=datetime.now(tz=UTC),
        )

    def assert_ready(self) -> PlatformHealthReport:
        """Run checks and raise ``PlatformError`` if not ready."""
        report = self.check()
        if not report.ready:
            failed = [c.name for c in report.checks if c.status is CheckStatus.FAIL]
            msg = f"platform not ready: failed checks={failed}"
            raise PlatformError(msg)
        return report

    def _check_configuration(self) -> HealthCheckResult:
        try:
            # Re-validate nested models by reconstructing from fields.
            _ = PlatformConfig(
                environment=self._config.environment,
                providers=self._config.providers,
                cache=self._config.cache,
                timeouts=self._config.timeouts,
                features=self._config.features,
                secrets=self._config.secrets,
            )
        except PlatformError as exc:
            return HealthCheckResult(
                name="configuration",
                status=CheckStatus.FAIL,
                message=str(exc),
            )
        return HealthCheckResult(
            name="configuration",
            status=CheckStatus.PASS,
            message=f"environment={self._config.environment.value}",
        )

    def _check_feature_flags(self) -> HealthCheckResult:
        features = self._config.features
        if not isinstance(features, FeatureFlags):
            return HealthCheckResult(
                name="feature_flags",
                status=CheckStatus.FAIL,
                message="features must be FeatureFlags",
            )
        return HealthCheckResult(
            name="feature_flags",
            status=CheckStatus.PASS,
            message=(
                f"fundamentals={features.include_fundamentals}, "
                f"economic={features.include_economic}, "
                f"valuation={features.include_valuation}, "
                f"allow_partial={features.allow_partial}"
            ),
        )

    def _check_provider_settings(self) -> HealthCheckResult:
        providers = self._config.providers
        if not isinstance(providers, ProviderSettings):
            return HealthCheckResult(
                name="provider_settings",
                status=CheckStatus.FAIL,
                message="providers must be ProviderSettings",
            )
        enabled: list[str] = []
        if providers.enable_market:
            enabled.append(providers.market_provider_id)
        if providers.enable_fundamentals:
            enabled.append(providers.fundamentals_provider_id)
        if providers.enable_economic:
            enabled.append(providers.economic_provider_id)
        return HealthCheckResult(
            name="provider_settings",
            status=CheckStatus.PASS,
            message=f"enabled={enabled}",
        )

    def _check_provider_registry(self) -> HealthCheckResult:
        if self._registry is None:
            return HealthCheckResult(
                name="provider_registry",
                status=CheckStatus.SKIP,
                message="no registry injected",
            )
        required = self._required
        if required is None:
            required = _enabled_provider_ids(self._config.providers)
        missing: list[str] = []
        try:
            names = {n.lower() for n in self._registry.list_names()}
            for provider_id in required:
                key = provider_id.strip().lower()
                if key not in names:
                    missing.append(provider_id)
                    continue
                # Touch metadata to confirm registration integrity.
                self._registry.get(provider_id)
                self._registry.get_metadata(provider_id)
        except Exception as exc:  # noqa: BLE001 — surface as health failure
            return HealthCheckResult(
                name="provider_registry",
                status=CheckStatus.FAIL,
                message=f"registry inspection failed: {exc}",
            )
        if missing:
            return HealthCheckResult(
                name="provider_registry",
                status=CheckStatus.FAIL,
                message=f"missing required providers: {missing}",
            )
        return HealthCheckResult(
            name="provider_registry",
            status=CheckStatus.PASS,
            message=f"required providers present: {list(required)}",
        )

    def _check_composition_pipeline(self) -> HealthCheckResult:
        """Readiness of the canonical composition path served by ``/analyse``.

        ``/analyse`` runs ``DSPPlatform.compose_intelligence`` →
        ``PlatformOrchestrator`` → ``run_execution_pipeline``, which needs no
        legacy ``InvestmentAnalysisService``. Offline only: verifies the
        capability is enabled and the canonical stage graph is importable.
        """
        if self._platform is None:
            return HealthCheckResult(
                name="composition_pipeline",
                status=CheckStatus.SKIP,
                message="no platform instance injected",
            )
        if not callable(getattr(self._platform, "compose_intelligence", None)):
            return HealthCheckResult(
                name="composition_pipeline",
                status=CheckStatus.FAIL,
                message="platform does not expose compose_intelligence",
            )
        configuration = getattr(self._platform, "configuration", None)
        has_capability = getattr(configuration, "has_capability", None)
        if callable(has_capability) and not has_capability("compose_intelligence"):
            return HealthCheckResult(
                name="composition_pipeline",
                status=CheckStatus.FAIL,
                message="capability disabled: 'compose_intelligence'",
            )
        try:
            from dsp_platform.composition.orchestrator import PlatformOrchestrator
            from dsp_platform.composition.pipeline import EXECUTION_ORDER
            from dsp_platform.composition.versions import (
                COMPOSITION_PIPELINE_VERSION,
            )
        except Exception as exc:  # noqa: BLE001 — surface as health failure
            return HealthCheckResult(
                name="composition_pipeline",
                status=CheckStatus.FAIL,
                message=f"canonical composition pipeline unavailable: {exc}",
            )
        if not callable(getattr(PlatformOrchestrator, "execute", None)):
            return HealthCheckResult(
                name="composition_pipeline",
                status=CheckStatus.FAIL,
                message="orchestrator does not expose execute",
            )
        if not EXECUTION_ORDER:
            return HealthCheckResult(
                name="composition_pipeline",
                status=CheckStatus.FAIL,
                message="canonical composition pipeline has no stages",
            )
        return HealthCheckResult(
            name="composition_pipeline",
            status=CheckStatus.PASS,
            message=(
                f"pipeline={COMPOSITION_PIPELINE_VERSION}, "
                f"stages={len(EXECUTION_ORDER)}"
            ),
        )

    def _check_investment_data_provider(self) -> HealthCheckResult:
        """P1-03 — report whether authenticated investment connectors resolve.

        Failure is recorded for ops visibility but does not block overall
        platform readiness (see ``_NON_BLOCKING_READY_CHECKS``). Investment
        routes still fail closed via adapter factories when credentials are
        missing. Adapters are constructed offline (no provider I/O); only
        class names / env-var names are reported.
        """
        try:
            from dsp_platform.composition.authenticated_valuation import (
                production_investment_connectors,
                production_requires_authenticated_bundle,
            )
        except Exception as exc:  # noqa: BLE001 — surface as health failure
            return HealthCheckResult(
                name="investment_data_provider",
                status=CheckStatus.FAIL,
                message=f"production profile unavailable: {exc}",
            )
        if not production_requires_authenticated_bundle():
            return HealthCheckResult(
                name="investment_data_provider",
                status=CheckStatus.SKIP,
                message="non-production environment",
            )
        try:
            selected = production_investment_connectors()
        except Exception as exc:  # noqa: BLE001 — fail closed, never fabricate
            return HealthCheckResult(
                name="investment_data_provider",
                status=CheckStatus.FAIL,
                message=f"{type(exc).__name__}: {exc}",
            )
        detail = ", ".join(f"{k}={v}" for k, v in sorted(selected.items()))
        return HealthCheckResult(
            name="investment_data_provider",
            status=CheckStatus.PASS,
            message=f"authenticated adapters: {detail}" if detail else "configured",
        )

    def _check_wiring(self, *, canonical_ready: bool = False) -> HealthCheckResult:
        if self._platform is None:
            return HealthCheckResult(
                name="dependency_wiring",
                status=CheckStatus.SKIP,
                message="no platform instance injected",
            )
        try:
            analysis = self._platform.analysis_service
        except Exception as exc:  # noqa: BLE001 — surface as health failure
            if canonical_ready:
                return HealthCheckResult(
                    name="dependency_wiring",
                    status=CheckStatus.SKIP,
                    message=(
                        "legacy analysis service not wired; canonical "
                        "composition pipeline serves analysis"
                    ),
                )
            return HealthCheckResult(
                name="dependency_wiring",
                status=CheckStatus.FAIL,
                message=f"cannot access analysis service: {exc}",
            )
        if not callable(getattr(analysis, "analyze_recommendation", None)):
            return HealthCheckResult(
                name="dependency_wiring",
                status=CheckStatus.FAIL,
                message="analysis service lacks analyze_recommendation",
            )
        return HealthCheckResult(
            name="dependency_wiring",
            status=CheckStatus.PASS,
            message="analysis service wired",
        )


def _enabled_provider_ids(providers: ProviderSettings) -> tuple[str, ...]:
    ids: list[str] = []
    if providers.enable_market:
        ids.append(providers.market_provider_id)
    if providers.enable_fundamentals:
        ids.append(providers.fundamentals_provider_id)
    if providers.enable_economic:
        ids.append(providers.economic_provider_id)
    return tuple(ids)
