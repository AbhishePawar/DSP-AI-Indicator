"""Tests for data_engine.providers.registry."""

from datetime import date

import pytest

from contracts.domain.instrument import Instrument
from contracts.domain.price_series import PriceSeries
from contracts.enums import BarFrequency
from data_engine.adapters import BaseAdapter
from data_engine.exceptions import DataEngineError
from data_engine.ports import MarketDataPort
from data_engine.providers import (
    DataCapability,
    ProviderCapabilities,
    ProviderMetadata,
    ProviderRegistry,
    ProviderStatus,
)


class FakeMarketDataAdapter(BaseAdapter, MarketDataPort):
    """Minimal in-test fake adapter used only to exercise the registry."""

    def __init__(self, series: PriceSeries) -> None:
        self._series = series

    @property
    def provider_name(self) -> str:
        return "fake_vendor"

    def get_price_series(
        self,
        instrument: Instrument,
        frequency: BarFrequency,
        start: date,
        end: date,
    ) -> PriceSeries:
        return self._series


class TestProviderRegistry:
    """Tests for the ProviderRegistry."""

    def test_starts_empty(self) -> None:
        registry = ProviderRegistry()
        assert len(registry) == 0
        assert registry.list_names() == []

    def test_register_then_get_returns_adapter(
        self, sample_price_series: PriceSeries
    ) -> None:
        registry = ProviderRegistry()
        adapter = FakeMarketDataAdapter(sample_price_series)
        metadata = ProviderMetadata(
            provider_id="fake_vendor",
            name="Fake Vendor",
            capabilities=ProviderCapabilities.from_flags(market_data=True),
        )

        registry.register(adapter, metadata)

        assert registry.get("fake_vendor") is adapter
        assert "fake_vendor" in registry
        assert len(registry) == 1

    def test_get_metadata_returns_registered_metadata(
        self, sample_price_series: PriceSeries
    ) -> None:
        registry = ProviderRegistry()
        adapter = FakeMarketDataAdapter(sample_price_series)
        metadata = ProviderMetadata(provider_id="fake_vendor", name="Fake Vendor")
        registry.register(adapter, metadata)

        assert registry.get_metadata("fake_vendor") == metadata

    def test_get_unregistered_provider_raises_key_error(self) -> None:
        registry = ProviderRegistry()
        with pytest.raises(KeyError):
            registry.get("unknown")

    def test_lookup_is_case_insensitive(
        self, sample_price_series: PriceSeries
    ) -> None:
        registry = ProviderRegistry()
        adapter = FakeMarketDataAdapter(sample_price_series)
        registry.register(
            adapter, ProviderMetadata(provider_id="Fake_Vendor", name="Fake Vendor")
        )

        assert registry.get("fake_vendor") is adapter
        assert registry.get("FAKE_VENDOR") is adapter

    def test_registering_conflicting_adapter_under_same_id_raises(
        self, sample_price_series: PriceSeries
    ) -> None:
        registry = ProviderRegistry()
        first = FakeMarketDataAdapter(sample_price_series)
        second = FakeMarketDataAdapter(sample_price_series)
        registry.register(
            first, ProviderMetadata(provider_id="fake_vendor", name="Fake Vendor")
        )

        with pytest.raises(ValueError, match="already registered"):
            registry.register(
                second,
                ProviderMetadata(provider_id="fake_vendor", name="Fake Vendor"),
            )

    def test_filter_by_capability_returns_only_matching_active_providers(
        self, sample_price_series: PriceSeries
    ) -> None:
        registry = ProviderRegistry()
        registry.register(
            FakeMarketDataAdapter(sample_price_series),
            ProviderMetadata(
                provider_id="market_vendor",
                name="Market Vendor",
                capabilities=ProviderCapabilities.from_flags(market_data=True),
            ),
        )
        registry.register(
            FakeMarketDataAdapter(sample_price_series),
            ProviderMetadata(
                provider_id="news_vendor",
                name="News Vendor",
                capabilities=ProviderCapabilities.from_flags(news=True),
            ),
        )

        assert registry.filter_by_capability(DataCapability.MARKET_DATA) == (
            "market_vendor",
        )

    def test_filter_by_capability_excludes_non_active_providers(
        self, sample_price_series: PriceSeries
    ) -> None:
        registry = ProviderRegistry()
        registry.register(
            FakeMarketDataAdapter(sample_price_series),
            ProviderMetadata(
                provider_id="disabled_vendor",
                name="Disabled Vendor",
                capabilities=ProviderCapabilities.from_flags(market_data=True),
                status=ProviderStatus.DISABLED,
            ),
        )

        assert registry.filter_by_capability(DataCapability.MARKET_DATA) == ()

    def test_select_preferred_picks_lowest_priority(
        self, sample_price_series: PriceSeries
    ) -> None:
        registry = ProviderRegistry()
        preferred = FakeMarketDataAdapter(sample_price_series)
        fallback = FakeMarketDataAdapter(sample_price_series)
        registry.register(
            fallback,
            ProviderMetadata(
                provider_id="fallback_vendor",
                name="Fallback Vendor",
                capabilities=ProviderCapabilities.from_flags(market_data=True),
                priority=10,
            ),
        )
        registry.register(
            preferred,
            ProviderMetadata(
                provider_id="preferred_vendor",
                name="Preferred Vendor",
                capabilities=ProviderCapabilities.from_flags(market_data=True),
                priority=1,
            ),
        )

        assert registry.select_preferred(DataCapability.MARKET_DATA) is preferred

    def test_select_preferred_with_no_priority_sorts_last(
        self, sample_price_series: PriceSeries
    ) -> None:
        registry = ProviderRegistry()
        ranked = FakeMarketDataAdapter(sample_price_series)
        unranked = FakeMarketDataAdapter(sample_price_series)
        registry.register(
            unranked,
            ProviderMetadata(
                provider_id="unranked_vendor",
                name="Unranked Vendor",
                capabilities=ProviderCapabilities.from_flags(market_data=True),
            ),
        )
        registry.register(
            ranked,
            ProviderMetadata(
                provider_id="ranked_vendor",
                name="Ranked Vendor",
                capabilities=ProviderCapabilities.from_flags(market_data=True),
                priority=5,
            ),
        )

        assert registry.select_preferred(DataCapability.MARKET_DATA) is ranked

    def test_select_preferred_raises_when_nothing_matches(self) -> None:
        registry = ProviderRegistry()
        with pytest.raises(DataEngineError, match="No active provider"):
            registry.select_preferred(DataCapability.MARKET_DATA)
