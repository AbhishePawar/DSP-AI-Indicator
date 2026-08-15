"""Tests for PlatformHealthService."""

from __future__ import annotations

from typing import Any

import pytest

from contracts.domain.instrument import Instrument
from data_engine.adapters import BaseAdapter
from data_engine.ports import MarketDataPort
from data_engine.providers import (
    ProviderCapabilities,
    ProviderMetadata,
    ProviderRegistry,
)
from dsp_platform import (
    DEFAULT_CAPABILITIES,
    CheckStatus,
    Environment,
    PlatformBuilder,
    PlatformConfig,
    PlatformConfiguration,
    PlatformError,
    PlatformHealthService,
    ProviderSettings,
)


class _StubMarket(BaseAdapter, MarketDataPort):
    @property
    def provider_name(self) -> str:
        return "offline_market"

    def get_price_series(self, *args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        raise NotImplementedError("health checks must not call providers")


def _registry_with_market() -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(
        _StubMarket(),
        ProviderMetadata(
            provider_id="offline_market",
            name="Offline Market",
            capabilities=ProviderCapabilities.from_flags(market_data=True, daily=True),
        ),
    )
    return registry


class TestHealthService:
    def test_config_only_ready(self) -> None:
        config = PlatformConfig(environment=Environment.TEST)
        report = PlatformHealthService(config=config).check()
        assert report.ready is True
        assert report.status is CheckStatus.PASS
        by_name = {c.name: c for c in report.checks}
        assert by_name["configuration"].status is CheckStatus.PASS
        assert by_name["feature_flags"].status is CheckStatus.PASS
        assert by_name["provider_registry"].status is CheckStatus.SKIP
        assert by_name["dependency_wiring"].status is CheckStatus.SKIP

    def test_provider_registry_pass(
        self, instrument: Instrument, build_platform
    ) -> None:
        del instrument  # fixture ensures conftest loaded
        config = PlatformConfig(
            environment=Environment.TEST,
            providers=ProviderSettings(
                market_provider_id="offline_market",
                enable_market=True,
                enable_fundamentals=False,
                enable_economic=False,
            ),
        )
        platform = build_platform()
        report = PlatformHealthService(
            config=config,
            platform=platform,
            provider_registry=_registry_with_market(),
        ).check()
        assert report.ready is True
        by_name = {c.name: c for c in report.checks}
        assert by_name["provider_registry"].status is CheckStatus.PASS
        assert by_name["dependency_wiring"].status is CheckStatus.PASS

    def test_missing_provider_fails(self) -> None:
        config = PlatformConfig(
            environment=Environment.TEST,
            providers=ProviderSettings(
                market_provider_id="missing_vendor",
                enable_market=True,
                enable_fundamentals=False,
                enable_economic=False,
            ),
        )
        report = PlatformHealthService(
            config=config,
            provider_registry=_registry_with_market(),
        ).check()
        assert report.ready is False
        assert report.status is CheckStatus.FAIL
        by_name = {c.name: c for c in report.checks}
        assert by_name["provider_registry"].status is CheckStatus.FAIL

    def test_assert_ready_raises(self) -> None:
        config = PlatformConfig(
            environment=Environment.TEST,
            providers=ProviderSettings(
                market_provider_id="missing_vendor",
                enable_market=True,
                enable_fundamentals=False,
                enable_economic=False,
            ),
        )
        service = PlatformHealthService(
            config=config,
            provider_registry=_registry_with_market(),
        )
        with pytest.raises(PlatformError, match="platform not ready"):
            service.assert_ready()

    def test_canonical_platform_ready_without_legacy_analysis_service(self) -> None:
        """The API composition root serves /analyse via compose_intelligence.

        A platform composed with ``require_analysis_service=False`` must report
        ready: the canonical composition pipeline — not the legacy
        Yahoo/FRED ``InvestmentAnalysisService`` — is the production path.
        """
        platform = (
            PlatformBuilder()
            .with_configuration(
                PlatformConfiguration(require_analysis_service=False)
            )
            .auto_ready(True)
            .build()
        )
        report = PlatformHealthService(
            config=PlatformConfig(environment=Environment.TEST),
            platform=platform,
        ).check()
        by_name = {c.name: c for c in report.checks}
        assert by_name["composition_pipeline"].status is CheckStatus.PASS
        assert by_name["dependency_wiring"].status is CheckStatus.SKIP
        assert "canonical" in by_name["dependency_wiring"].message
        assert report.ready is True
        assert report.status is CheckStatus.PASS

    def test_no_analysis_path_at_all_fails(self) -> None:
        """Readiness is not faked: with no canonical path and no legacy service."""
        capabilities = tuple(
            c for c in DEFAULT_CAPABILITIES if c != "compose_intelligence"
        )
        platform = (
            PlatformBuilder()
            .with_configuration(
                PlatformConfiguration(
                    require_analysis_service=False,
                    enabled_capabilities=capabilities,
                )
            )
            .auto_ready(True)
            .build()
        )
        report = PlatformHealthService(
            config=PlatformConfig(environment=Environment.TEST),
            platform=platform,
        ).check()
        by_name = {c.name: c for c in report.checks}
        assert by_name["composition_pipeline"].status is CheckStatus.FAIL
        assert by_name["dependency_wiring"].status is CheckStatus.FAIL
        assert report.ready is False

    def test_legacy_analysis_service_still_passes(self, build_platform) -> None:
        """Injecting the legacy service remains a valid, reported wiring."""
        report = PlatformHealthService(
            config=PlatformConfig(environment=Environment.TEST),
            platform=build_platform(),
        ).check()
        by_name = {c.name: c for c in report.checks}
        assert by_name["dependency_wiring"].status is CheckStatus.PASS
        assert by_name["composition_pipeline"].status is CheckStatus.PASS
        assert report.ready is True

    def test_investment_data_provider_skipped_outside_production(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DSP_ENVIRONMENT", raising=False)
        report = PlatformHealthService(
            config=PlatformConfig(environment=Environment.TEST)
        ).check()
        by_name = {c.name: c for c in report.checks}
        assert by_name["investment_data_provider"].status is CheckStatus.SKIP

    def test_investment_data_provider_fails_closed_in_production(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """P1-03 — production without Upstox credentials must not report ready."""
        monkeypatch.setenv("DSP_ENVIRONMENT", "production")
        monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
        monkeypatch.delenv("DSP_UPSTOX_ANALYTICS_TOKEN", raising=False)
        report = PlatformHealthService(
            config=PlatformConfig(environment=Environment.PRODUCTION)
        ).check()
        by_name = {c.name: c for c in report.checks}
        assert by_name["investment_data_provider"].status is CheckStatus.FAIL
        assert report.ready is False

    def test_investment_data_provider_passes_with_upstox_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DSP_ENVIRONMENT", "production")
        monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
        monkeypatch.setenv("DSP_UPSTOX_ANALYTICS_TOKEN", "super-secret-token")
        report = PlatformHealthService(
            config=PlatformConfig(environment=Environment.PRODUCTION)
        ).check()
        by_name = {c.name: c for c in report.checks}
        check = by_name["investment_data_provider"]
        assert check.status is CheckStatus.PASS
        assert "Upstox" in check.message
        # CV-001 / security: adapter class names only, never credentials.
        assert "super-secret-token" not in check.message
        assert all(
            "super-secret-token" not in c.message for c in report.checks
        )

    def test_no_network_on_registry_check(self) -> None:
        """Registry health must not invoke adapter I/O."""
        config = PlatformConfig(
            environment=Environment.TEST,
            providers=ProviderSettings(
                market_provider_id="offline_market",
                enable_market=True,
                enable_fundamentals=False,
                enable_economic=False,
            ),
        )
        # Would raise NotImplementedError if get_price_series were called.
        report = PlatformHealthService(
            config=config,
            provider_registry=_registry_with_market(),
        ).check()
        assert report.ready is True
