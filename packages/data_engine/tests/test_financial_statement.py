"""EPIC-D002 authenticated financial statement tests."""

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
    FinancialStatementProvenance,
    FinancialStatementProviderRegistry,
    FinancialStatementService,
    InMemoryAuthenticatedStatementAdapter,
    InMemoryCache,
    InvalidProviderDataError,
    NullAuthenticatedStatementAdapter,
    ProviderRequestError,
    RateLimiter,
    RetryPolicy,
    StatementField,
    StatementQuery,
    build_statements_from_mapping,
    validate_authenticated_statements,
)


def _instrument(symbol: str = "AAPL") -> Instrument:
    return Instrument(symbol=symbol, asset_class=AssetClass.EQUITY, currency="USD")


def _seeded_bundle(symbol: str = "AAPL"):
    return build_statements_from_mapping(
        symbol=symbol,
        payload={
            "identity": {
                "symbol": symbol,
                "exchange": "NASDAQ",
                "company_name": "Apple Inc",
                "currency": "USD",
                "provider_company_id": "AAPL-USD",
            },
            "reporting_currency": "USD",
            "periods": [
                {
                    "period_type": "annual",
                    "fiscal_year": 2024,
                    "period_end": "2024-09-28",
                    "filing_date": "2024-11-01",
                    "reporting_currency": "USD",
                    "restated": False,
                    "income_statement": {
                        "revenue": 391_000_000_000,
                        "net_income": 93_000_000_000,
                        "eps": 6.0,
                    },
                    "balance_sheet": {
                        "cash": 60_000_000_000,
                        "total_assets": 350_000_000_000,
                        "equity": 60_000_000_000,
                        "total_debt": 100_000_000_000,
                    },
                    "cash_flow": {
                        "operating_cash_flow": 110_000_000_000,
                        "capex": -10_000_000_000,
                        "free_cash_flow": 100_000_000_000,
                    },
                    "ratios": {
                        "roe": 0.15,
                        "debt_to_equity": 1.6,
                    },
                },
                {
                    "period_type": "annual",
                    "fiscal_year": 2023,
                    "period_end": "2023-09-30",
                    "reporting_currency": "USD",
                    "restated": True,
                    "income_statement": {"revenue": 380_000_000_000},
                    "balance_sheet": {},
                    "cash_flow": {},
                    "ratios": {},
                },
                {
                    "period_type": "quarterly",
                    "fiscal_year": 2024,
                    "fiscal_quarter": 4,
                    "period_end": "2024-09-28",
                    "reporting_currency": "USD",
                    "income_statement": {"revenue": 95_000_000_000},
                    "balance_sheet": {},
                    "cash_flow": {},
                    "ratios": {},
                },
            ],
        },
        provenance=FinancialStatementProvenance(
            provider_id="memory_authenticated_statements",
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
            validate_authenticated_statements(bad)

    def test_rejects_available_null(self) -> None:
        bundle = _seeded_bundle()
        period = bundle.periods[0]
        bad_period = replace(
            period, revenue=StatementField(value=None, available=True)
        )
        bad = replace(bundle, periods=(bad_period,) + bundle.periods[1:])
        with pytest.raises(InvalidProviderDataError):
            validate_authenticated_statements(bad)

    def test_rejects_mixed_currencies(self) -> None:
        with pytest.raises(InvalidProviderDataError):
            build_statements_from_mapping(
                symbol="AAPL",
                payload={
                    "reporting_currency": "USD",
                    "periods": [
                        {
                            "period_type": "annual",
                            "fiscal_year": 2024,
                            "period_end": "2024-09-28",
                            "reporting_currency": "USD",
                            "income_statement": {"revenue": 1},
                        },
                        {
                            "period_type": "annual",
                            "fiscal_year": 2023,
                            "period_end": "2023-09-30",
                            "reporting_currency": "EUR",
                            "income_statement": {"revenue": 1},
                        },
                    ],
                },
                provenance=FinancialStatementProvenance(
                    provider_id="x",
                    provider_name="X",
                    source_type="licensed_vendor",
                    retrieved_at=datetime.now(tz=UTC),
                ),
            )


class TestNullAdapter:
    def test_returns_none(self) -> None:
        adapter = NullAuthenticatedStatementAdapter()
        assert adapter.get_statements(StatementQuery(_instrument())) is None
        health = adapter.health()
        assert health.healthy is True
        assert health.authenticated is False


class TestMemoryAdapterAndService:
    def test_requires_api_key(self) -> None:
        adapter = InMemoryAuthenticatedStatementAdapter(api_key=None)
        adapter.put(_seeded_bundle())
        with pytest.raises(ProviderRequestError):
            adapter.get_statements(StatementQuery(_instrument()))

    def test_service_cache_and_metrics(self) -> None:
        adapter = InMemoryAuthenticatedStatementAdapter(api_key="secret")
        adapter.put(_seeded_bundle())
        service = FinancialStatementService(
            adapter,
            cache=InMemoryCache(),
            cache_ttl_seconds=60,
            rate_limiter=RateLimiter(requests_per_minute=120),
            retry=RetryPolicy(max_attempts=2, backoff_seconds=0.0),
        )
        first = service.get_statements(StatementQuery(_instrument()))
        second = service.get_statements(StatementQuery(_instrument()))
        assert first is not None
        assert first.periods[0].revenue.value == Decimal("391000000000")
        assert second is not None
        assert second.provenance.cache_hit is True
        assert service.metrics.cache_hits == 1
        assert service.metrics.successes == 2

    def test_historical_filter_and_determinism(self) -> None:
        adapter = InMemoryAuthenticatedStatementAdapter(api_key="secret")
        adapter.put(_seeded_bundle())
        service = FinancialStatementService(adapter)
        annual = service.get_statements(
            StatementQuery(_instrument(), period_type="annual", include_restated=False)
        )
        assert annual is not None
        assert all(p.period_type == "annual" for p in annual.periods)
        assert all(not p.restated for p in annual.periods)
        assert annual.periods[0].period_end == date(2024, 9, 28)
        # Deterministic: same query → same period_end order
        again = service.get_statements(
            StatementQuery(_instrument(), period_type="annual", include_restated=False)
        )
        assert again is not None
        assert [p.period_end for p in again.periods] == [
            p.period_end for p in annual.periods
        ]

    def test_unknown_symbol_unavailable(self) -> None:
        adapter = InMemoryAuthenticatedStatementAdapter(api_key="secret")
        adapter.put(_seeded_bundle("AAPL"))
        service = FinancialStatementService(adapter)
        assert service.get_statements(StatementQuery(_instrument("MSFT"))) is None
        assert service.metrics.unavailable == 1

    def test_company_resolution(self) -> None:
        adapter = InMemoryAuthenticatedStatementAdapter(api_key="secret")
        adapter.put(_seeded_bundle())
        identity = adapter.resolve_company(_instrument())
        assert identity is not None
        assert identity.provider_company_id == "AAPL-USD"


class TestCircuitBreaker:
    def test_opens_after_failures(self) -> None:
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=60)

        class Boom(InMemoryAuthenticatedStatementAdapter):
            def get_statements(self, query):  # type: ignore[override]
                raise ProviderRequestError("boom")

        service = FinancialStatementService(
            Boom(api_key="x"),
            circuit_breaker=breaker,
            retry=RetryPolicy(max_attempts=1, backoff_seconds=0),
        )
        with pytest.raises(ProviderRequestError):
            service.get_statements(StatementQuery(_instrument()))
        with pytest.raises(ProviderRequestError):
            service.get_statements(StatementQuery(_instrument()))
        with pytest.raises(CircuitOpenError):
            service.get_statements(StatementQuery(_instrument()))


class TestRegistry:
    def test_register_and_get(self) -> None:
        reg = FinancialStatementProviderRegistry()
        adapter = NullAuthenticatedStatementAdapter()
        reg.register(adapter, default=True)
        assert reg.get().provider_id == "null_financial_statement"
        assert "null_financial_statement" in reg.list_ids()
