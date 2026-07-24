"""Tests for data_engine.services.

These tests prove the ports/adapters/providers/cache wiring works
end-to-end using an in-test fake adapter — never a real provider or
network call, consistent with this sprint's architecture-only scope.
"""

from datetime import date

import pytest

from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from contracts.domain.price_series import PriceSeries
from contracts.enums import BarFrequency, StatementPeriodType
from data_engine.adapters import BaseAdapter
from data_engine.cache import InMemoryCache
from data_engine.exceptions import DataEngineError
from data_engine.models import FundamentalsRequest, PriceSeriesRequest
from data_engine.ports import FundamentalsDataPort, MarketDataPort
from data_engine.providers import (
    ProviderCapabilities,
    ProviderMetadata,
    ProviderRegistry,
)
from data_engine.services import FundamentalsDataService, MarketDataService


class CountingFakeAdapter(BaseAdapter, MarketDataPort):
    """Fake adapter that counts how many times it was called.

    Used to verify the service checks the cache before calling the
    provider, without depending on any real data source.
    """

    def __init__(self, series: PriceSeries) -> None:
        self._series = series
        self.call_count = 0

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
        self.call_count += 1
        return self._series


@pytest.fixture
def adapter(sample_price_series: PriceSeries) -> CountingFakeAdapter:
    return CountingFakeAdapter(sample_price_series)


@pytest.fixture
def providers(adapter: CountingFakeAdapter) -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(
        adapter,
        ProviderMetadata(
            provider_id="fake_vendor",
            name="Fake Vendor",
            capabilities=ProviderCapabilities.from_flags(market_data=True),
        ),
    )
    return registry


@pytest.fixture
def request_(
    instrument: Instrument, date_range: tuple[date, date]
) -> PriceSeriesRequest:
    start, end = date_range
    return PriceSeriesRequest(
        instrument=instrument,
        frequency=BarFrequency.DAILY,
        start=start,
        end=end,
        provider_name="fake_vendor",
    )


class TestMarketDataService:
    """Tests for the MarketDataService application-layer composition."""

    def test_cache_miss_calls_provider_and_populates_cache(
        self,
        adapter: CountingFakeAdapter,
        providers: ProviderRegistry,
        request_: PriceSeriesRequest,
        sample_price_series: PriceSeries,
    ) -> None:
        cache: InMemoryCache[str, PriceSeries] = InMemoryCache()
        service = MarketDataService(providers=providers, cache=cache)

        result = service.get_price_series(request_)

        assert result == sample_price_series
        assert adapter.call_count == 1

    def test_cache_hit_does_not_call_provider_again(
        self,
        adapter: CountingFakeAdapter,
        providers: ProviderRegistry,
        request_: PriceSeriesRequest,
    ) -> None:
        cache: InMemoryCache[str, PriceSeries] = InMemoryCache()
        service = MarketDataService(providers=providers, cache=cache)

        service.get_price_series(request_)
        service.get_price_series(request_)

        assert adapter.call_count == 1

    def test_no_provider_name_and_no_default_raises(
        self,
        providers: ProviderRegistry,
        instrument: Instrument,
        date_range: tuple[date, date],
    ) -> None:
        start, end = date_range
        request = PriceSeriesRequest(
            instrument=instrument,
            frequency=BarFrequency.DAILY,
            start=start,
            end=end,
        )
        cache: InMemoryCache[str, PriceSeries] = InMemoryCache()
        service = MarketDataService(providers=providers, cache=cache)

        with pytest.raises(DataEngineError, match="No provider_name"):
            service.get_price_series(request)

    def test_default_provider_is_used_when_request_omits_one(
        self,
        adapter: CountingFakeAdapter,
        providers: ProviderRegistry,
        instrument: Instrument,
        date_range: tuple[date, date],
        sample_price_series: PriceSeries,
    ) -> None:
        start, end = date_range
        request = PriceSeriesRequest(
            instrument=instrument, frequency=BarFrequency.DAILY, start=start, end=end
        )
        cache: InMemoryCache[str, PriceSeries] = InMemoryCache()
        service = MarketDataService(
            providers=providers, cache=cache, default_provider="fake_vendor"
        )

        result = service.get_price_series(request)

        assert result == sample_price_series

    def test_unregistered_provider_raises_key_error(
        self, request_: PriceSeriesRequest
    ) -> None:
        empty_registry = ProviderRegistry()
        cache: InMemoryCache[str, PriceSeries] = InMemoryCache()
        service = MarketDataService(providers=empty_registry, cache=cache)

        with pytest.raises(KeyError):
            service.get_price_series(request_)


class CountingFakeFundamentalsAdapter(BaseAdapter, FundamentalsDataPort):
    def __init__(self, statements: tuple[FundamentalStatement, ...]) -> None:
        self._statements = statements
        self.call_count = 0

    @property
    def provider_name(self) -> str:
        return "fake_fundamentals"

    def get_fundamental_statements(
        self,
        instrument: Instrument,
        period_type: StatementPeriodType,
        *,
        limit: int | None = None,
    ) -> tuple[FundamentalStatement, ...]:
        self.call_count += 1
        return self._statements


@pytest.fixture
def sample_statements(instrument: Instrument) -> tuple[FundamentalStatement, ...]:
    return (
        FundamentalStatement(
            instrument=instrument,
            period_end=date(2023, 12, 31),
            period_type=StatementPeriodType.ANNUAL,
            fiscal_year=2023,
            currency="USD",
            revenue=100.0,
        ),
        FundamentalStatement(
            instrument=instrument,
            period_end=date(2024, 12, 31),
            period_type=StatementPeriodType.ANNUAL,
            fiscal_year=2024,
            currency="USD",
            revenue=120.0,
        ),
    )


class TestFundamentalsDataService:
    def test_cache_miss_and_hit(
        self,
        instrument: Instrument,
        sample_statements: tuple[FundamentalStatement, ...],
    ) -> None:
        adapter = CountingFakeFundamentalsAdapter(sample_statements)
        registry = ProviderRegistry()
        registry.register(
            adapter,
            ProviderMetadata(
                provider_id="fake_fundamentals",
                name="Fake Fundamentals",
                capabilities=ProviderCapabilities.from_flags(fundamentals=True),
            ),
        )
        cache: InMemoryCache[str, tuple[FundamentalStatement, ...]] = InMemoryCache()
        service = FundamentalsDataService(
            providers=registry, cache=cache, default_provider="fake_fundamentals"
        )
        request = FundamentalsRequest(
            instrument=instrument, period_type=StatementPeriodType.ANNUAL
        )

        first = service.get_fundamental_statements(request)
        second = service.get_fundamental_statements(request)

        assert adapter.call_count == 1
        assert first[0].period_end == date(2024, 12, 31)
        assert first == second

    def test_wrong_port_raises(
        self, instrument: Instrument, providers: ProviderRegistry
    ) -> None:
        cache: InMemoryCache[str, tuple[FundamentalStatement, ...]] = InMemoryCache()
        service = FundamentalsDataService(
            providers=providers, cache=cache, default_provider="fake_vendor"
        )
        request = FundamentalsRequest(
            instrument=instrument, period_type=StatementPeriodType.ANNUAL
        )
        with pytest.raises(DataEngineError, match="does not support fundamentals"):
            service.get_fundamental_statements(request)
