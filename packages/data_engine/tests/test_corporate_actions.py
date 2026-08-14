"""EPIC-D003 authenticated corporate actions tests."""

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
    CorporateActionField,
    CorporateActionProvenance,
    CorporateActionProviderRegistry,
    CorporateActionQuery,
    CorporateActionService,
    InMemoryAuthenticatedCorporateActionAdapter,
    InMemoryCache,
    InvalidProviderDataError,
    NullAuthenticatedCorporateActionAdapter,
    ProviderRequestError,
    RateLimiter,
    RetryPolicy,
    build_actions_from_mapping,
    validate_authenticated_corporate_actions,
)


def _instrument(symbol: str = "AAPL") -> Instrument:
    return Instrument(symbol=symbol, asset_class=AssetClass.EQUITY, currency="USD")


def _seeded_bundle(symbol: str = "AAPL"):
    return build_actions_from_mapping(
        symbol=symbol,
        payload={
            "identity": {
                "symbol": symbol,
                "exchange": "NASDAQ",
                "company_name": "Apple Inc",
                "provider_company_id": "AAPL-USD",
            },
            "events": [
                {
                    "action_id": "div-2024-05",
                    "action_type": "dividend",
                    "symbol": symbol,
                    "ex_date": "2024-05-10",
                    "record_date": "2024-05-13",
                    "payment_date": "2024-05-16",
                    "currency": "USD",
                    "amount": 0.25,
                },
                {
                    "action_id": "split-2020-08",
                    "action_type": "stock_split",
                    "symbol": symbol,
                    "effective_date": "2020-08-31",
                    "ratio_from": 1,
                    "ratio_to": 4,
                },
                {
                    "action_id": "buyback-2023-01",
                    "action_type": "buyback",
                    "symbol": symbol,
                    "announcement_date": "2023-01-15",
                    "effective_date": "2023-02-01",
                    "shares": 1_000_000,
                },
            ],
        },
        provenance=CorporateActionProvenance(
            provider_id="memory_authenticated_corporate_actions",
            provider_name="Memory",
            source_type="licensed_vendor",
            retrieved_at=datetime.now(tz=UTC),
            auth_mode="api_key",
        ),
    )


class TestValidation:
    def test_rejects_fabricated_source_type(self) -> None:
        bundle = _seeded_bundle()
        bad = replace(
            bundle,
            provenance=replace(bundle.provenance, source_type="dummy"),
        )
        with pytest.raises(InvalidProviderDataError):
            validate_authenticated_corporate_actions(bad)

    def test_rejects_unknown_action_type(self) -> None:
        with pytest.raises(InvalidProviderDataError):
            build_actions_from_mapping(
                symbol="AAPL",
                payload={
                    "events": [
                        {
                            "action_id": "x1",
                            "action_type": "fabricated_split",
                            "effective_date": "2024-01-01",
                        }
                    ]
                },
                provenance=CorporateActionProvenance(
                    provider_id="x",
                    provider_name="X",
                    source_type="licensed_vendor",
                    retrieved_at=datetime.now(tz=UTC),
                ),
            )

    def test_rejects_available_null(self) -> None:
        bundle = _seeded_bundle()
        event = bundle.events[0]
        bad_event = replace(
            event, amount=CorporateActionField(value=None, available=True)
        )
        bad = replace(bundle, events=(bad_event,) + bundle.events[1:])
        with pytest.raises(InvalidProviderDataError):
            validate_authenticated_corporate_actions(bad)


class TestNullAdapter:
    def test_returns_none(self) -> None:
        adapter = NullAuthenticatedCorporateActionAdapter()
        assert adapter.get_actions(CorporateActionQuery(_instrument())) is None
        health = adapter.health()
        assert health.healthy is True
        assert health.authenticated is False


class TestMemoryAdapterAndService:
    def test_requires_api_key(self) -> None:
        adapter = InMemoryAuthenticatedCorporateActionAdapter(api_key=None)
        adapter.put(_seeded_bundle())
        with pytest.raises(ProviderRequestError):
            adapter.get_actions(CorporateActionQuery(_instrument()))

    def test_service_cache_and_metrics(self) -> None:
        adapter = InMemoryAuthenticatedCorporateActionAdapter(api_key="secret")
        adapter.put(_seeded_bundle())
        service = CorporateActionService(
            adapter,
            cache=InMemoryCache(),
            cache_ttl_seconds=60,
            rate_limiter=RateLimiter(requests_per_minute=120),
            retry=RetryPolicy(max_attempts=2, backoff_seconds=0.0),
        )
        first = service.get_actions(CorporateActionQuery(_instrument()))
        second = service.get_actions(CorporateActionQuery(_instrument()))
        assert first is not None
        assert first.events[0].action_type == "dividend"
        assert first.events[0].amount.value == Decimal("0.25")
        assert second is not None
        assert second.provenance.cache_hit is True
        assert service.metrics.cache_hits == 1
        assert service.metrics.successes == 2

    def test_historical_filter_and_determinism(self) -> None:
        adapter = InMemoryAuthenticatedCorporateActionAdapter(api_key="secret")
        adapter.put(_seeded_bundle())
        service = CorporateActionService(adapter)
        splits = service.get_actions(
            CorporateActionQuery(_instrument(), action_type="stock_split")
        )
        assert splits is not None
        assert len(splits.events) == 1
        assert splits.events[0].effective_date == date(2020, 8, 31)

        ranged = service.get_actions(
            CorporateActionQuery(
                _instrument(),
                start_date=date(2023, 1, 1),
                end_date=date(2024, 12, 31),
            )
        )
        assert ranged is not None
        ids = [e.action_id for e in ranged.events]
        again = service.get_actions(
            CorporateActionQuery(
                _instrument(),
                start_date=date(2023, 1, 1),
                end_date=date(2024, 12, 31),
            )
        )
        assert again is not None
        assert [e.action_id for e in again.events] == ids

    def test_unknown_symbol_unavailable(self) -> None:
        adapter = InMemoryAuthenticatedCorporateActionAdapter(api_key="secret")
        adapter.put(_seeded_bundle("AAPL"))
        service = CorporateActionService(adapter)
        assert service.get_actions(CorporateActionQuery(_instrument("MSFT"))) is None
        assert service.metrics.unavailable == 1


class TestCircuitBreaker:
    def test_opens_after_failures(self) -> None:
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=60)

        class Boom(InMemoryAuthenticatedCorporateActionAdapter):
            def get_actions(self, query):  # type: ignore[override]
                raise ProviderRequestError("boom")

        service = CorporateActionService(
            Boom(api_key="x"),
            circuit_breaker=breaker,
            retry=RetryPolicy(max_attempts=1, backoff_seconds=0),
        )
        with pytest.raises(ProviderRequestError):
            service.get_actions(CorporateActionQuery(_instrument()))
        with pytest.raises(ProviderRequestError):
            service.get_actions(CorporateActionQuery(_instrument()))
        with pytest.raises(CircuitOpenError):
            service.get_actions(CorporateActionQuery(_instrument()))


class TestRegistry:
    def test_register_and_get(self) -> None:
        reg = CorporateActionProviderRegistry()
        adapter = NullAuthenticatedCorporateActionAdapter()
        reg.register(adapter, default=True)
        assert reg.get().provider_id == "null_corporate_actions"
        assert "null_corporate_actions" in reg.list_ids()
