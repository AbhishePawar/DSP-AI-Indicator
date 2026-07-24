"""Tests for Yahoo Finance provider registration and end-to-end wiring.

These prove two things without any network access:

1. ``register_yahoo_finance`` wires ``YahooFinanceAdapter`` into the
   existing, unmodified ``ProviderFactory``/``ProviderRegistry`` exactly
   as any other provider would be.
2. ``MarketDataService`` can retrieve a price series through that
   registry, going through the full adapter -> normalizer -> contracts
   flow, without knowing ``YahooFinanceAdapter`` exists.
"""

from collections.abc import Mapping
from datetime import date
from typing import Any

import pytest

from contracts.domain.instrument import Instrument
from contracts.domain.price_series import PriceSeries
from contracts.enums import BarFrequency
from data_engine.adapters.yahoo_finance.adapter import YahooFinanceAdapter
from data_engine.adapters.yahoo_finance.registration import (
    YAHOO_FINANCE_METADATA,
    build_yahoo_finance_adapter,
    register_yahoo_finance,
)
from data_engine.cache import InMemoryCache
from data_engine.models import PriceSeriesRequest
from data_engine.providers import DataCapability, ProviderFactory, ProviderRegistry
from data_engine.services import MarketDataService


class _FakeHttpClient:
    """Stub ``JsonHttpClient`` returning a canned three-bar chart payload."""

    def get_json(
        self, url: str, *, params: Mapping[str, str] | None = None
    ) -> Mapping[str, Any]:
        return {
            "chart": {
                "result": [
                    {
                        "timestamp": [1704240000, 1704326400, 1704412800],
                        "indicators": {
                            "quote": [
                                {
                                    "open": [185.0, 186.0, 187.0],
                                    "high": [186.5, 187.5, 188.5],
                                    "low": [184.5, 185.5, 186.5],
                                    "close": [186.0, 187.0, 188.0],
                                    "volume": [1_000_000, 1_100_000, 1_200_000],
                                }
                            ],
                            "adjclose": [{"adjclose": [185.9, 186.9, 187.9]}],
                        },
                    }
                ],
                "error": None,
            }
        }


class TestBuildYahooFinanceAdapter:
    def test_builds_a_yahoo_finance_adapter(self) -> None:
        adapter = build_yahoo_finance_adapter({})

        assert isinstance(adapter, YahooFinanceAdapter)
        assert adapter.provider_name == "yahoo_finance"


class TestRegisterYahooFinance:
    def test_registers_builder_and_adapter_using_existing_infrastructure(
        self,
    ) -> None:
        factory = ProviderFactory()
        registry = ProviderRegistry()

        adapter = register_yahoo_finance(factory, registry)

        assert factory.is_registered("yahoo_finance")
        assert isinstance(adapter, YahooFinanceAdapter)
        assert registry.get("yahoo_finance") is adapter
        assert registry.get_metadata("yahoo_finance") == YAHOO_FINANCE_METADATA

    def test_registered_provider_is_discoverable_by_capability(self) -> None:
        factory = ProviderFactory()
        registry = ProviderRegistry()
        register_yahoo_finance(factory, registry)

        matches = registry.filter_by_capability(DataCapability.MARKET_DATA)

        assert matches == ("yahoo_finance",)


class TestMarketDataServiceThroughRegistry:
    """Validates the full end-to-end flow from the sprint's success criteria.

    Uses a ``YahooFinanceAdapter`` constructed with an injected fake HTTP
    client (rather than ``register_yahoo_finance``'s default, real
    ``UrllibJsonHttpClient``) so the request never touches the network,
    while still exercising the adapter, normalizer, and validation
    pipeline exactly as production wiring would.
    """

    @pytest.fixture
    def registry_with_yahoo_finance(self) -> ProviderRegistry:
        registry = ProviderRegistry()
        adapter = YahooFinanceAdapter(http_client=_FakeHttpClient())
        registry.register(adapter, YAHOO_FINANCE_METADATA)
        return registry

    def test_service_retrieves_price_series_without_knowing_the_provider(
        self, registry_with_yahoo_finance: ProviderRegistry, instrument: Instrument
    ) -> None:
        service = MarketDataService(
            providers=registry_with_yahoo_finance,
            cache=InMemoryCache(),
            default_provider="yahoo_finance",
        )
        request = PriceSeriesRequest(
            instrument=instrument,
            frequency=BarFrequency.DAILY,
            start=date(2024, 1, 1),
            end=date(2024, 1, 5),
        )

        series = service.get_price_series(request)

        assert isinstance(series, PriceSeries)
        assert len(series.bars) == 3

    def test_service_selects_yahoo_finance_via_preferred_capability_lookup(
        self, registry_with_yahoo_finance: ProviderRegistry
    ) -> None:
        adapter = registry_with_yahoo_finance.select_preferred(
            DataCapability.MARKET_DATA
        )

        assert adapter.provider_name == "yahoo_finance"
