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
    CheckStatus,
    Environment,
    PlatformConfig,
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
