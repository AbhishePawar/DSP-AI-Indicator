"""EPIC-D001 authenticated market quote tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass

from data_engine import (
    CircuitBreaker,
    CircuitOpenError,
    InMemoryAuthenticatedQuoteAdapter,
    InMemoryCache,
    InvalidProviderDataError,
    MarketQuoteProvenance,
    MarketQuoteProviderRegistry,
    MarketQuoteService,
    NullAuthenticatedQuoteAdapter,
    ProviderRequestError,
    QuoteField,
    RateLimiter,
    RetryPolicy,
    build_quote_from_mapping,
    validate_authenticated_quote,
)


def _instrument(symbol: str = "AAPL") -> Instrument:
    return Instrument(symbol=symbol, asset_class=AssetClass.EQUITY, currency="USD")


def _seeded_quote(symbol: str = "AAPL"):
    return build_quote_from_mapping(
        symbol=symbol,
        payload={
            "exchange": "NASDAQ",
            "currency": "USD",
            "current_price": 190.5,
            "open": 189.0,
            "high": 191.0,
            "low": 188.5,
            "previous_close": 188.0,
            "week_52_high": 200.0,
            "week_52_low": 140.0,
            "volume": 1_000_000,
            "average_volume": 900_000,
            "market_cap": 3_000_000_000_000,
            "enterprise_value": 3_100_000_000_000,
            "shares_outstanding": 15_000_000_000,
            "dividend_yield": 0.005,
            "beta": 1.2,
        },
        provenance=MarketQuoteProvenance(
            provider_id="memory_authenticated_quote",
            provider_name="Memory",
            source_type="licensed_vendor",
            retrieved_at=datetime.now(tz=UTC),
            auth_mode="api_key",
        ),
    )


class TestValidation:
    def test_rejects_fabricated_source_type(self) -> None:
        from dataclasses import replace

        quote = _seeded_quote()
        bad = replace(
            quote,
            provenance=replace(quote.provenance, source_type="dummy"),
        )
        with pytest.raises(InvalidProviderDataError):
            validate_authenticated_quote(bad)

    def test_rejects_available_null(self) -> None:
        from dataclasses import replace

        quote = _seeded_quote()
        bad = replace(quote, current_price=QuoteField(value=None, available=True))
        with pytest.raises(InvalidProviderDataError):
            validate_authenticated_quote(bad)


class TestNullAdapter:
    def test_returns_none(self) -> None:
        adapter = NullAuthenticatedQuoteAdapter()
        assert adapter.get_quote(_instrument()) is None
        health = adapter.health()
        assert health.healthy is True
        assert health.authenticated is False


class TestMemoryAdapterAndService:
    def test_requires_api_key(self) -> None:
        adapter = InMemoryAuthenticatedQuoteAdapter(api_key=None)
        adapter.put(_seeded_quote())
        with pytest.raises(ProviderRequestError):
            adapter.get_quote(_instrument())

    def test_service_cache_and_metrics(self) -> None:
        adapter = InMemoryAuthenticatedQuoteAdapter(api_key="secret")
        adapter.put(_seeded_quote())
        service = MarketQuoteService(
            adapter,
            cache=InMemoryCache(),
            cache_ttl_seconds=60,
            rate_limiter=RateLimiter(requests_per_minute=120),
            retry=RetryPolicy(max_attempts=2, backoff_seconds=0.0),
        )
        first = service.get_quote(_instrument())
        second = service.get_quote(_instrument())
        assert first is not None
        assert first.current_price.value == Decimal("190.5")
        assert second is not None
        assert service.metrics.cache_hits == 1
        assert service.metrics.successes == 2
        assert first.provenance.provider_id == "memory_authenticated_quote"

    def test_unknown_symbol_unavailable(self) -> None:
        adapter = InMemoryAuthenticatedQuoteAdapter(api_key="secret")
        adapter.put(_seeded_quote("AAPL"))
        service = MarketQuoteService(adapter)
        assert service.get_quote(_instrument("MSFT")) is None
        assert service.metrics.unavailable == 1


class TestCircuitBreaker:
    def test_opens_after_failures(self) -> None:
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=60)

        class Boom(InMemoryAuthenticatedQuoteAdapter):
            def get_quote(self, instrument: Instrument):  # type: ignore[override]
                raise ProviderRequestError("boom")

        service = MarketQuoteService(
            Boom(api_key="x"),
            circuit_breaker=breaker,
            retry=RetryPolicy(max_attempts=1, backoff_seconds=0),
        )
        with pytest.raises(ProviderRequestError):
            service.get_quote(_instrument())
        with pytest.raises(ProviderRequestError):
            service.get_quote(_instrument())
        with pytest.raises(CircuitOpenError):
            service.get_quote(_instrument())


class TestRegistry:
    def test_register_and_get(self) -> None:
        reg = MarketQuoteProviderRegistry()
        adapter = NullAuthenticatedQuoteAdapter()
        reg.register(adapter, default=True)
        assert reg.get().provider_id == "null_market_quote"
        assert "null_market_quote" in reg.list_ids()
