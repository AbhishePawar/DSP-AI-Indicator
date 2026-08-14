"""EPIC-D004 authenticated historical time-series tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass

from data_engine import (
    CircuitBreaker,
    CircuitOpenError,
    HistoricalField,
    HistoricalProvenance,
    HistoricalSeriesProviderRegistry,
    HistoricalSeriesQuery,
    HistoricalSeriesService,
    InMemoryAuthenticatedHistoricalAdapter,
    InMemoryCache,
    InvalidProviderDataError,
    NullAuthenticatedHistoricalAdapter,
    ProviderRequestError,
    RateLimiter,
    RetryPolicy,
    build_historical_bundle_from_mapping,
    validate_authenticated_historical_bundle,
)


def _instrument(symbol: str = "AAPL") -> Instrument:
    return Instrument(symbol=symbol, asset_class=AssetClass.EQUITY, currency="USD")


def _ohlcv_bundle(symbol: str = "AAPL"):
    return build_historical_bundle_from_mapping(
        symbol=symbol,
        payload={
            "identity": {
                "symbol": symbol,
                "exchange": "NASDAQ",
                "currency": "USD",
                "provider_company_id": "AAPL-USD",
            },
            "series_kind": "ohlcv",
            "frequency": "daily",
            "bars": [
                {
                    "date": "2024-01-02",
                    "open": 100,
                    "high": 105,
                    "low": 99,
                    "close": 104,
                    "volume": 1_000_000,
                },
                {
                    "date": "2024-01-03",
                    "open": 104,
                    "high": 106,
                    "low": 103,
                    "close": 105,
                    "volume": 1_100_000,
                },
                {
                    "date": "2024-01-04",
                    "open": 105,
                    "high": 107,
                    "low": 104,
                    "close": 106,
                    "volume": 900_000,
                },
            ],
        },
        provenance=HistoricalProvenance(
            provider_id="memory_authenticated_historical",
            provider_name="Memory",
            source_type="licensed_vendor",
            retrieved_at=datetime.now(tz=UTC),
            auth_mode="api_key",
        ),
    )


def _market_cap_bundle(symbol: str = "AAPL"):
    return build_historical_bundle_from_mapping(
        symbol=symbol,
        payload={
            "identity": {"symbol": symbol, "currency": "USD"},
            "series_kind": "market_cap",
            "points": [
                {"date": "2024-01-02", "value": 2_800_000_000_000},
                {"date": "2024-01-03", "value": 2_850_000_000_000},
            ],
        },
        provenance=HistoricalProvenance(
            provider_id="memory_authenticated_historical",
            provider_name="Memory",
            source_type="licensed_vendor",
            retrieved_at=datetime.now(tz=UTC),
            auth_mode="api_key",
        ),
    )


class TestValidation:
    def test_rejects_fabricated_source_type(self) -> None:
        bundle = _ohlcv_bundle()
        bad = replace(
            bundle,
            provenance=replace(bundle.provenance, source_type="dummy"),
        )
        with pytest.raises(InvalidProviderDataError):
            validate_authenticated_historical_bundle(bad)

    def test_rejects_ohlc_inconsistency(self) -> None:
        with pytest.raises(InvalidProviderDataError):
            build_historical_bundle_from_mapping(
                symbol="AAPL",
                payload={
                    "series_kind": "ohlcv",
                    "frequency": "daily",
                    "bars": [
                        {
                            "date": "2024-01-02",
                            "open": 100,
                            "high": 90,
                            "low": 99,
                            "close": 104,
                            "volume": 1,
                        }
                    ],
                },
                provenance=HistoricalProvenance(
                    provider_id="x",
                    provider_name="X",
                    source_type="licensed_vendor",
                    retrieved_at=datetime.now(tz=UTC),
                ),
            )

    def test_rejects_available_null(self) -> None:
        bundle = _ohlcv_bundle()
        bar = bundle.bars[0]
        bad_bar = replace(bar, close=HistoricalField(value=None, available=True))
        bad = replace(bundle, bars=(bad_bar,) + bundle.bars[1:])
        with pytest.raises(InvalidProviderDataError):
            validate_authenticated_historical_bundle(bad)


class TestNullAdapter:
    def test_returns_none(self) -> None:
        adapter = NullAuthenticatedHistoricalAdapter()
        assert (
            adapter.get_series(
                HistoricalSeriesQuery(_instrument(), series_kind="ohlcv")
            )
            is None
        )
        health = adapter.health()
        assert health.healthy is True
        assert health.authenticated is False


class TestMemoryAdapterAndService:
    def test_requires_api_key(self) -> None:
        adapter = InMemoryAuthenticatedHistoricalAdapter(api_key=None)
        adapter.put(_ohlcv_bundle())
        with pytest.raises(ProviderRequestError):
            adapter.get_series(
                HistoricalSeriesQuery(_instrument(), series_kind="ohlcv")
            )

    def test_service_cache_and_metrics(self) -> None:
        adapter = InMemoryAuthenticatedHistoricalAdapter(api_key="secret")
        adapter.put(_ohlcv_bundle())
        service = HistoricalSeriesService(
            adapter,
            cache=InMemoryCache(),
            cache_ttl_seconds=60,
            rate_limiter=RateLimiter(requests_per_minute=120),
            retry=RetryPolicy(max_attempts=2, backoff_seconds=0.0),
        )
        q = HistoricalSeriesQuery(_instrument(), series_kind="ohlcv")
        first = service.get_series(q)
        second = service.get_series(q)
        assert first is not None
        assert first.bars[0].close.value == Decimal("104")
        assert second is not None
        assert second.provenance.cache_hit is True
        assert service.metrics.cache_hits == 1
        assert service.metrics.successes == 2

    def test_date_range_and_determinism(self) -> None:
        adapter = InMemoryAuthenticatedHistoricalAdapter(api_key="secret")
        adapter.put(_ohlcv_bundle())
        service = HistoricalSeriesService(adapter)
        ranged = service.get_series(
            HistoricalSeriesQuery(
                _instrument(),
                series_kind="ohlcv",
                start_date=date(2024, 1, 3),
                end_date=date(2024, 1, 4),
            )
        )
        assert ranged is not None
        assert [b.bar_date for b in ranged.bars] == [
            date(2024, 1, 3),
            date(2024, 1, 4),
        ]
        again = service.get_series(
            HistoricalSeriesQuery(
                _instrument(),
                series_kind="ohlcv",
                start_date=date(2024, 1, 3),
                end_date=date(2024, 1, 4),
            )
        )
        assert again is not None
        assert [b.bar_date for b in again.bars] == [
            b.bar_date for b in ranged.bars
        ]

    def test_market_cap_series(self) -> None:
        adapter = InMemoryAuthenticatedHistoricalAdapter(api_key="secret")
        adapter.put(_market_cap_bundle())
        service = HistoricalSeriesService(adapter)
        result = service.get_series(
            HistoricalSeriesQuery(_instrument(), series_kind="market_cap")
        )
        assert result is not None
        assert len(result.points) == 2
        assert result.points[0].value.value == Decimal("2800000000000")

    def test_unknown_symbol_unavailable(self) -> None:
        adapter = InMemoryAuthenticatedHistoricalAdapter(api_key="secret")
        adapter.put(_ohlcv_bundle("AAPL"))
        service = HistoricalSeriesService(adapter)
        assert (
            service.get_series(
                HistoricalSeriesQuery(_instrument("MSFT"), series_kind="ohlcv")
            )
            is None
        )
        assert service.metrics.unavailable == 1


class TestCircuitBreaker:
    def test_opens_after_failures(self) -> None:
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=60)

        class Boom(InMemoryAuthenticatedHistoricalAdapter):
            def get_series(self, query):  # type: ignore[override]
                raise ProviderRequestError("boom")

        service = HistoricalSeriesService(
            Boom(api_key="x"),
            circuit_breaker=breaker,
            retry=RetryPolicy(max_attempts=1, backoff_seconds=0),
        )
        q = HistoricalSeriesQuery(_instrument(), series_kind="ohlcv")
        with pytest.raises(ProviderRequestError):
            service.get_series(q)
        with pytest.raises(ProviderRequestError):
            service.get_series(q)
        with pytest.raises(CircuitOpenError):
            service.get_series(q)


class TestRegistry:
    def test_register_and_get(self) -> None:
        reg = HistoricalSeriesProviderRegistry()
        adapter = NullAuthenticatedHistoricalAdapter()
        reg.register(adapter, default=True)
        assert reg.get().provider_id == "null_historical_series"
        assert "null_historical_series" in reg.list_ids()
