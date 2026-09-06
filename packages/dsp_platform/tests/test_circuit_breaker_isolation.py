"""Cross-service circuit isolation and TCS stale-share regression (Stage 1M-B-FIX)."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine import (
    CircuitBreaker,
    FinancialStatementService,
    InMemoryAuthenticatedQuoteAdapter,
    InMemoryAuthenticatedStatementAdapter,
    MarketQuoteProvenance,
    MarketQuoteService,
    ProviderRequestError,
    RetryPolicy,
    ShareCountService,
    StatementQuery,
    build_quote_from_mapping,
    build_statements_from_mapping,
)
from data_engine.financial_statement.models import FinancialStatementProvenance
from dsp_platform import (
    DATA_UNAVAILABLE,
    AuthenticatedValuationError,
    CompositionRequest,
    PlatformOrchestrator,
    load_authenticated_valuation_bundle,
)
from dsp_platform.financial_statements import reset_financial_statement_service_for_tests
from dsp_platform.market_quotes import reset_market_quote_service_for_tests
from dsp_platform.promoted_share_count import (
    DEFAULT_PROMOTED_SHARE_COUNT_DIR,
    SHARES_OUTSTANDING_IDENTITY_MISMATCH,
    SHARES_OUTSTANDING_STALE,
    DurablePromotedShareCountAdapter,
    ShareCountResolutionError,
    sign_promoted_snapshot,
)
from dsp_platform.share_counts import reset_share_count_service_for_tests
from financial import (
    BalanceSheet,
    CashFlowStatement,
    CurrencyCode,
    CurrencyRef,
    FinancialPeriod,
    FinancialStatements,
    IncomeStatement,
    PeriodType,
    UnitScale,
)
from financial.metadata import StatementMetadata

_PROMOTED_JSON = DEFAULT_PROMOTED_SHARE_COUNT_DIR / "INE467B01029_XNSE.json"
_HORIZON = datetime(2026, 9, 5, 14, 6, tzinfo=UTC)
_TCS_PRICE = 2304.0
_NO_RETRY = RetryPolicy(max_attempts=1, backoff_seconds=0.0)


def _tcs_instrument() -> Instrument:
    return Instrument(
        symbol="TCS",
        asset_class=AssetClass.EQUITY,
        currency="INR",
        exchange="NSE",
        isin="INE467B01029",
        name="Tata Consultancy Services",
    )


def _aapl_instrument() -> Instrument:
    return Instrument(
        symbol="AAPL",
        asset_class=AssetClass.EQUITY,
        currency="USD",
        exchange="NASDAQ",
        isin="US0378331005",
    )


def _payload() -> dict:
    return json.loads(_PROMOTED_JSON.read_text(encoding="utf-8"))


def _seed_tcs_statements():
    ni = 10.0
    return build_statements_from_mapping(
        symbol="TCS",
        payload={
            "identity": {
                "symbol": "TCS",
                "exchange": "NSE",
                "company_name": "Tata Consultancy Services",
                "currency": "INR",
                "isin": "INE467B01029",
            },
            "reporting_currency": "INR",
            "statement_basis": "consolidated",
            "unit_scale": "actual",
            "periods": [
                {
                    "period_type": "annual",
                    "fiscal_year": 2026,
                    "period_end": "2026-03-31",
                    "filing_date": "2026-04-15",
                    "reporting_currency": "INR",
                    "restated": False,
                    "income_statement": {
                        "revenue": ni * 5,
                        "net_income": ni,
                        "eps_basic": 10.0,
                        "operating_income": ni * 1.2,
                    },
                    "balance_sheet": {
                        "cash": ni,
                        "total_assets": ni * 15,
                        "total_liabilities": ni * 5,
                        "equity": ni * 10,
                        "total_debt": ni * 2,
                    },
                    "cash_flow": {
                        "operating_cash_flow": ni * 1.5,
                        "capex": -ni * 0.3,
                        "free_cash_flow": ni * 1.2,
                    },
                    "ratios": {},
                }
            ],
        },
        provenance=FinancialStatementProvenance(
            provider_id="memory_authenticated_statements",
            provider_name="Memory Statements",
            source_type="licensed_vendor",
            retrieved_at=_HORIZON,
            auth_mode="api_key",
        ),
    )


def _seed_quote(*, symbol: str, price: float, exchange: str, isin: str, currency: str):
    return build_quote_from_mapping(
        symbol=symbol,
        payload={
            "exchange": exchange,
            "currency": currency,
            "current_price": price,
            "previous_close": price,
        },
        provenance=MarketQuoteProvenance(
            provider_id="memory_authenticated_quote",
            provider_name="Memory Quote",
            source_type="licensed_vendor",
            retrieved_at=_HORIZON,
            auth_mode="api_key",
            metadata={"isin": isin, "exchange": exchange},
        ),
    )


def _stale_promoted_adapter(tmp_path: Path) -> DurablePromotedShareCountAdapter:
    payload = _payload()
    payload["complete_through"] = "2026-08-01"
    payload.pop("integrity", None)
    (tmp_path / "stale.json").write_text(
        json.dumps(sign_promoted_snapshot(payload)), encoding="utf-8"
    )
    return DurablePromotedShareCountAdapter(directory=tmp_path, now=lambda: _HORIZON)


def _client_statements() -> FinancialStatements:
    period = FinancialPeriod(
        period_type=PeriodType.ANNUAL,
        period_end=date(2024, 12, 31),
        fiscal_year=2024,
        currency=CurrencyRef(CurrencyCode.INR),
    )
    return FinancialStatements(
        period=period,
        income_statement=IncomeStatement(
            revenue=1.0,
            net_income=1.0,
            eps=0.01,
            weighted_shares=100.0,
        ),
        balance_sheet=BalanceSheet(equity=1.0, total_equity=1.0, total_assets=2.0),
        cash_flow=CashFlowStatement(operating_cash_flow=1.0, capex=-0.1),
        statement_metadata=StatementMetadata(unit_scale=UnitScale.ACTUAL),
    )


def _reset_all() -> None:
    reset_financial_statement_service_for_tests(None)
    reset_market_quote_service_for_tests(None)
    reset_share_count_service_for_tests(None)


class TestCrossServiceIsolation:
    def test_share_count_stale_does_not_open_market_quote_breaker(self) -> None:
        quote_breaker = CircuitBreaker(name="market quote")
        share_breaker = CircuitBreaker(name="share count")
        quote = InMemoryAuthenticatedQuoteAdapter(api_key="k")
        quote.put(
            _seed_quote(
                symbol="TCS",
                price=_TCS_PRICE,
                exchange="NSE",
                isin="INE467B01029",
                currency="INR",
            )
        )
        quote_service = MarketQuoteService(
            quote, circuit_breaker=quote_breaker, retry=_NO_RETRY
        )

        class Stale:
            provider_id = "stale_share_count"

            def get_share_count(self, instrument: Instrument):
                _ = instrument
                raise ShareCountResolutionError(
                    SHARES_OUTSTANDING_STALE,
                    "corporate-action coverage does not reach retrieved_at",
                )

            def health(self):
                return quote.health()

        share_service = ShareCountService(
            Stale(), circuit_breaker=share_breaker, retry=_NO_RETRY
        )
        assert quote_service.get_quote(_tcs_instrument()) is not None
        with pytest.raises(ShareCountResolutionError):
            share_service.get_share_count(_tcs_instrument())
        assert quote_breaker.failure_count == 0
        assert quote_breaker.is_open is False
        assert share_breaker.failure_count == 0
        assert share_breaker.is_open is False

    def test_market_quote_provider_failure_does_not_open_share_count_breaker(self) -> None:
        quote_breaker = CircuitBreaker(name="market quote")
        share_breaker = CircuitBreaker(name="share count")

        class Boom(InMemoryAuthenticatedQuoteAdapter):
            def get_quote(self, instrument: Instrument):  # type: ignore[override]
                _ = instrument
                raise ProviderRequestError("HTTP 503")

        quote_service = MarketQuoteService(
            Boom(api_key="x"), circuit_breaker=quote_breaker, retry=_NO_RETRY
        )
        share_service = ShareCountService(
            DurablePromotedShareCountAdapter(
                directory=Path("/missing"), now=lambda: _HORIZON
            ),
            circuit_breaker=share_breaker,
            retry=_NO_RETRY,
        )
        with pytest.raises(ProviderRequestError):
            quote_service.get_quote(_tcs_instrument())
        assert share_service.get_share_count(_tcs_instrument()) is None
        assert quote_breaker.failure_count == 1
        assert share_breaker.failure_count == 0
        assert share_breaker.is_open is False

    def test_financial_statement_failure_does_not_open_share_count_breaker(self) -> None:
        stmt_breaker = CircuitBreaker(name="financial statements")
        share_breaker = CircuitBreaker(name="share count")

        class Boom(InMemoryAuthenticatedStatementAdapter):
            def get_statements(self, query):  # type: ignore[override]
                _ = query
                raise ProviderRequestError("HTTP 502")

        stmt_service = FinancialStatementService(
            Boom(api_key="x"), circuit_breaker=stmt_breaker, retry=_NO_RETRY
        )
        share_service = ShareCountService(
            DurablePromotedShareCountAdapter(
                directory=Path("/missing"), now=lambda: _HORIZON
            ),
            circuit_breaker=share_breaker,
            retry=_NO_RETRY,
        )
        with pytest.raises(ProviderRequestError):
            stmt_service.get_statements(StatementQuery(_tcs_instrument()))
        assert share_service.get_share_count(_tcs_instrument()) is None
        assert stmt_breaker.failure_count == 1
        assert share_breaker.failure_count == 0
        assert share_breaker.is_open is False


class TestCrossSymbolNoMarketQuoteContamination:
    def test_tcs_and_aapl_stale_do_not_increment_market_quote_breaker(self) -> None:
        quote_adapter = InMemoryAuthenticatedQuoteAdapter(api_key="k")
        quote_adapter.put(
            _seed_quote(
                symbol="TCS",
                price=_TCS_PRICE,
                exchange="NSE",
                isin="INE467B01029",
                currency="INR",
            )
        )
        quote_adapter.put(
            _seed_quote(
                symbol="AAPL",
                price=190.0,
                exchange="NASDAQ",
                isin="US0378331005",
                currency="USD",
            )
        )
        quote_service = MarketQuoteService(
            quote_adapter,
            circuit_breaker=CircuitBreaker(name="market quote"),
            retry=_NO_RETRY,
        )
        class StaleAny:
            provider_id = "stale_share_count"

            def get_share_count(self, instrument: Instrument):
                _ = instrument
                raise ShareCountResolutionError(
                    SHARES_OUTSTANDING_STALE,
                    "corporate-action coverage does not reach retrieved_at",
                )

            def health(self):
                return quote_adapter.health()

        share_service = ShareCountService(
            StaleAny(),
            circuit_breaker=CircuitBreaker(name="share count"),
            retry=_NO_RETRY,
        )
        assert quote_service.get_quote(_tcs_instrument()) is not None
        assert quote_service.get_quote(_aapl_instrument()) is not None
        with pytest.raises(ShareCountResolutionError, match=SHARES_OUTSTANDING_STALE):
            share_service.get_share_count(_tcs_instrument())
        with pytest.raises(ShareCountResolutionError, match=SHARES_OUTSTANDING_STALE):
            share_service.get_share_count(_aapl_instrument())
        assert quote_service._breaker.failure_count == 0
        assert quote_service._breaker.is_open is False
        assert share_service._breaker.failure_count == 0
        assert share_service._breaker.is_open is False


class TestTcsStaleShareCountRegression:
    def test_quote_ok_stale_shares_fail_closed_without_poisoning_breakers(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DSP_ENVIRONMENT", "production")
        stmt = InMemoryAuthenticatedStatementAdapter(api_key="test-key")
        stmt.put(_seed_tcs_statements())
        quote = InMemoryAuthenticatedQuoteAdapter(api_key="test-key")
        quote.put(
            _seed_quote(
                symbol="TCS",
                price=_TCS_PRICE,
                exchange="NSE",
                isin="INE467B01029",
                currency="INR",
            )
        )
        quote_service = MarketQuoteService(quote, retry=_NO_RETRY)
        share_service = ShareCountService(
            _stale_promoted_adapter(tmp_path), retry=_NO_RETRY
        )
        stmt_service = FinancialStatementService(stmt, retry=_NO_RETRY)
        reset_financial_statement_service_for_tests(stmt_service)
        reset_market_quote_service_for_tests(quote_service)
        reset_share_count_service_for_tests(share_service)
        try:
            live_quote = quote_service.get_quote(_tcs_instrument())
            assert live_quote is not None
            assert live_quote.current_price.value == Decimal(str(_TCS_PRICE))
            assert live_quote.shares_outstanding.value is None

            with pytest.raises(AuthenticatedValuationError) as first:
                load_authenticated_valuation_bundle(
                    "TCS", exchange="NSE", currency="INR"
                )
            assert SHARES_OUTSTANDING_STALE in str(first.value)
            assert "CircuitOpenError" not in str(first.value)
            assert DATA_UNAVAILABLE in str(first.value)

            assert share_service._breaker.failure_count == 0
            assert share_service._breaker.is_open is False
            assert quote_service._breaker.failure_count == 0
            assert quote_service._breaker.is_open is False
            assert stmt_service._breaker.is_open is False

            with pytest.raises(AuthenticatedValuationError) as second:
                load_authenticated_valuation_bundle(
                    "TCS", exchange="NSE", currency="INR"
                )
            assert SHARES_OUTSTANDING_STALE in str(second.value)
            assert "circuit breaker open" not in str(second.value).lower()

            result = PlatformOrchestrator(platform_version="test").execute(
                CompositionRequest(
                    ticker="TCS",
                    exchange="NSE",
                    current_market_price=_TCS_PRICE,
                    financial_statements=_client_statements(),
                )
            )
            assert result.ok is False
            joined = " ".join(result.errors or [])
            assert SHARES_OUTSTANDING_STALE in joined
            assert "CircuitOpenError" not in joined
            assert "circuit breaker open" not in joined.lower()
            signals = result.valuation_signals
            iv = getattr(signals, "intrinsic_value_per_share", None) if signals else None
            assert iv is None
            assert live_quote.current_price.value == Decimal(str(_TCS_PRICE))
            assert share_service._breaker.failure_count == 0
            assert share_service._breaker.is_open is False
            assert quote_service._breaker.is_open is False
        finally:
            _reset_all()

    def test_identity_mismatch_still_fail_closed_without_breaker(
        self, tmp_path: Path
    ) -> None:
        payload = _payload()
        payload.pop("integrity", None)
        (tmp_path / "ok.json").write_text(
            json.dumps(sign_promoted_snapshot(payload)), encoding="utf-8"
        )
        adapter = DurablePromotedShareCountAdapter(
            directory=tmp_path, now=lambda: _HORIZON
        )
        service = ShareCountService(adapter, retry=_NO_RETRY)
        with pytest.raises(
            ShareCountResolutionError, match=SHARES_OUTSTANDING_IDENTITY_MISMATCH
        ):
            service.get_share_count(
                Instrument(
                    symbol="TCS",
                    asset_class=AssetClass.EQUITY,
                    currency="INR",
                    exchange="NYSE",
                    isin="INE467B01029",
                )
            )
        assert service._breaker.failure_count == 0
        assert service._breaker.is_open is False
