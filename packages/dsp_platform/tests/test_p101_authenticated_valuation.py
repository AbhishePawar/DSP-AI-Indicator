"""P1-01 — authenticated data → ValuationEngine → IV/MoS (server authority)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from data_engine import (
    FinancialStatementProvenance,
    FinancialStatementService,
    InMemoryAuthenticatedQuoteAdapter,
    InMemoryAuthenticatedStatementAdapter,
    MarketQuoteProvenance,
    MarketQuoteService,
    NullAuthenticatedQuoteAdapter,
    NullAuthenticatedStatementAdapter,
    build_quote_from_mapping,
    build_statements_from_mapping,
)
from dsp_platform import (
    DATA_UNAVAILABLE,
    AuthenticatedValuationError,
    CompositionRequest,
    PlatformOrchestrator,
    load_authenticated_valuation_bundle,
)
from dsp_platform.composition.authenticated_valuation import signals_from_assessment
from dsp_platform.financial_statements import reset_financial_statement_service_for_tests
from dsp_platform.market_quotes import reset_market_quote_service_for_tests
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
from investment_recommendation import ValuationSignals
from valuation import ValuationEngine


TICKER = "TEST"
FIXED_RETRIEVED = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


def _stmt_provenance() -> FinancialStatementProvenance:
    return FinancialStatementProvenance(
        provider_id="memory_authenticated_statements",
        provider_name="Memory Statements",
        source_type="licensed_vendor",
        retrieved_at=FIXED_RETRIEVED,
        auth_mode="api_key",
    )


def _client_statements() -> FinancialStatements:
    """Client-supplied statements (must not become valuation authority)."""
    period = FinancialPeriod(
        period_type=PeriodType.ANNUAL,
        period_end=date(2024, 12, 31),
        fiscal_year=2024,
        currency=CurrencyRef(CurrencyCode.USD),
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


def _seed_statements(symbol: str = TICKER):
    return build_statements_from_mapping(
        symbol=symbol,
        payload={
            "identity": {
                "symbol": symbol,
                "exchange": "NYSE",
                "company_name": "Test Corp",
                "currency": "USD",
            },
            "reporting_currency": "USD",
            "periods": [
                {
                    "period_type": "annual",
                    "fiscal_year": 2024,
                    "period_end": "2024-12-31",
                    "filing_date": "2025-02-01",
                    "reporting_currency": "USD",
                    "restated": False,
                    "income_statement": {
                        "revenue": 500.0,
                        "net_income": 100.0,
                        "eps_basic": 1.0,
                        "operating_income": 120.0,
                    },
                    "balance_sheet": {
                        "cash": 50.0,
                        "total_assets": 1500.0,
                        "equity": 1000.0,
                        "total_debt": 200.0,
                    },
                    "cash_flow": {
                        "operating_cash_flow": 150.0,
                        "capex": -30.0,
                        "free_cash_flow": 120.0,
                    },
                    "ratios": {},
                },
                {
                    "period_type": "annual",
                    "fiscal_year": 2023,
                    "period_end": "2023-12-31",
                    "reporting_currency": "USD",
                    "income_statement": {
                        "revenue": 450.0,
                        "net_income": 90.0,
                        "eps_basic": 0.9,
                    },
                    "balance_sheet": {"equity": 900.0, "total_assets": 1400.0},
                    "cash_flow": {
                        "operating_cash_flow": 130.0,
                        "capex": -25.0,
                    },
                    "ratios": {},
                },
            ],
        },
        provenance=_stmt_provenance(),
    )


def _seed_quote(
    symbol: str = TICKER,
    *,
    price: float = 8.0,
    shares: float = 100.0,
    market_cap: float | None = None,
    currency: str = "USD",
):
    return build_quote_from_mapping(
        symbol=symbol,
        payload={
            "exchange": "NYSE",
            "currency": currency,
            "current_price": price,
            "previous_close": price,
            "market_cap": market_cap if market_cap is not None else price * shares,
            "shares_outstanding": shares,
        },
        provenance=MarketQuoteProvenance(
            provider_id="memory_authenticated_quote",
            provider_name="Memory Quote",
            source_type="licensed_vendor",
            retrieved_at=FIXED_RETRIEVED,
            auth_mode="api_key",
        ),
    )


@pytest.fixture
def seeded_services():
    stmt_adapter = InMemoryAuthenticatedStatementAdapter(api_key="test-key")
    stmt_adapter.put(_seed_statements())
    quote_adapter = InMemoryAuthenticatedQuoteAdapter(api_key="test-key")
    quote_adapter.put(_seed_quote())
    stmt_service = FinancialStatementService(stmt_adapter)
    quote_service = MarketQuoteService(quote_adapter)
    reset_financial_statement_service_for_tests(stmt_service)
    reset_market_quote_service_for_tests(quote_service)
    yield stmt_service, quote_service
    reset_financial_statement_service_for_tests(None)
    reset_market_quote_service_for_tests(None)


def test_load_bundle_positive(seeded_services) -> None:
    bundle = load_authenticated_valuation_bundle(TICKER)
    assert bundle.ticker == TICKER
    assert bundle.current_market_price == pytest.approx(8.0)
    assert bundle.shares_outstanding == pytest.approx(100.0)
    assert bundle.reporting_currency == "USD"
    assert bundle.period_kind == "annual"
    assert bundle.financial_snapshot.latest.total_equity == pytest.approx(1000.0)
    assert bundle.statement_provenance["provider_id"]
    assert bundle.quote_provenance["provider_id"]


def test_valuation_engine_iv_and_mos_deterministic(seeded_services) -> None:
    bundle = load_authenticated_valuation_bundle(TICKER)
    assessment = ValuationEngine(clock=lambda: FIXED_RETRIEVED).analyze(
        bundle.financial_snapshot,
        bundle.market_snapshot,
    )
    assert assessment.valuation_range.mid is not None
    signals = signals_from_assessment(
        assessment,
        current_market_price=bundle.current_market_price,
        shares_outstanding=bundle.shares_outstanding,
    )
    assert signals.intrinsic_value_per_share is not None
    assert signals.intrinsic_value_per_share > 0
    assert signals.current_market_price == pytest.approx(8.0)
    assert signals.margin_of_safety is not None
    assessment2 = ValuationEngine(clock=lambda: FIXED_RETRIEVED).analyze(
        bundle.financial_snapshot,
        bundle.market_snapshot,
    )
    signals2 = signals_from_assessment(
        assessment2,
        current_market_price=bundle.current_market_price,
        shares_outstanding=bundle.shares_outstanding,
    )
    assert signals2.intrinsic_value_per_share == pytest.approx(
        signals.intrinsic_value_per_share
    )
    assert signals2.margin_of_safety == pytest.approx(signals.margin_of_safety)


def test_pipeline_authenticated_path_produces_server_iv(seeded_services) -> None:
    request = CompositionRequest(
        financial_statements=_client_statements(),
        current_market_price=999.0,  # client price must not win over auth quote
        ticker=TICKER,
        company="Test Corp",
    )
    result = PlatformOrchestrator(platform_version="0.7.0").execute(request)
    assert result.ok is True
    signals = result.valuation_signals or result.valuation
    assert signals is not None
    iv = getattr(signals, "intrinsic_value_per_share", None)
    price = getattr(signals, "current_market_price", None)
    mos = getattr(signals, "margin_of_safety", None)
    assert iv is not None and iv > 0
    assert price == pytest.approx(8.0)  # authenticated quote, not client 999
    assert mos is not None
    valuation_outcome = next(s for s in result.stages if s.stage == "valuation")
    assert any("P1-01" in w for w in valuation_outcome.warnings)
    financial_outcome = next(s for s in result.stages if s.stage == "financial")
    assert any("P1-01" in w for w in financial_outcome.warnings)


def test_client_iv_mos_recommendation_cannot_override(seeded_services) -> None:
    forged_iv = 9999.0
    forged_mos = 0.99
    forged_request = CompositionRequest(
        financial_statements=_client_statements(),
        current_market_price=8.0,
        ticker=TICKER,
        valuation_signals=ValuationSignals(
            intrinsic_value_per_share=forged_iv,
            current_market_price=8.0,
            margin_of_safety=forged_mos,
            confidence=0.99,
        ),
    )
    result = PlatformOrchestrator(platform_version="0.7.0").execute(forged_request)
    assert result.ok is True
    signals = result.valuation_signals or result.valuation
    iv = getattr(signals, "intrinsic_value_per_share", None)
    mos = getattr(signals, "margin_of_safety", None)
    assert iv != forged_iv
    assert iv is not None
    assert mos != forged_mos
    assert result.investment_recommendation is not None


def test_missing_financial_statements_fail_closed() -> None:
    quote_adapter = InMemoryAuthenticatedQuoteAdapter(api_key="test-key")
    quote_adapter.put(_seed_quote())
    reset_market_quote_service_for_tests(MarketQuoteService(quote_adapter))
    reset_financial_statement_service_for_tests(
        FinancialStatementService(InMemoryAuthenticatedStatementAdapter(api_key="k"))
    )
    try:
        with pytest.raises(AuthenticatedValuationError, match="Data unavailable"):
            load_authenticated_valuation_bundle(TICKER)
    finally:
        reset_financial_statement_service_for_tests(None)
        reset_market_quote_service_for_tests(None)


def test_missing_market_price_fail_closed() -> None:
    stmt_adapter = InMemoryAuthenticatedStatementAdapter(api_key="test-key")
    stmt_adapter.put(_seed_statements())
    reset_financial_statement_service_for_tests(FinancialStatementService(stmt_adapter))
    reset_market_quote_service_for_tests(
        MarketQuoteService(InMemoryAuthenticatedQuoteAdapter(api_key="k"))
    )
    try:
        with pytest.raises(AuthenticatedValuationError, match="Data unavailable"):
            load_authenticated_valuation_bundle(TICKER)
    finally:
        reset_financial_statement_service_for_tests(None)
        reset_market_quote_service_for_tests(None)


def test_wrong_ticker_fail_closed(seeded_services) -> None:
    with pytest.raises(AuthenticatedValuationError, match="Data unavailable"):
        load_authenticated_valuation_bundle("OTHER")


def test_currency_mismatch_fail_closed(seeded_services) -> None:
    quote_adapter = InMemoryAuthenticatedQuoteAdapter(api_key="test-key")
    quote_adapter.put(_seed_quote(currency="EUR"))
    reset_market_quote_service_for_tests(MarketQuoteService(quote_adapter))
    with pytest.raises(AuthenticatedValuationError, match="currency"):
        load_authenticated_valuation_bundle(TICKER)


def test_null_provider_rejected() -> None:
    reset_financial_statement_service_for_tests(
        FinancialStatementService(NullAuthenticatedStatementAdapter())
    )
    reset_market_quote_service_for_tests(
        MarketQuoteService(NullAuthenticatedQuoteAdapter())
    )
    try:
        with pytest.raises(AuthenticatedValuationError, match="Data unavailable"):
            load_authenticated_valuation_bundle(TICKER)
    finally:
        reset_financial_statement_service_for_tests(None)
        reset_market_quote_service_for_tests(None)


def test_production_pipeline_fails_without_authenticated_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    reset_financial_statement_service_for_tests(
        FinancialStatementService(NullAuthenticatedStatementAdapter())
    )
    reset_market_quote_service_for_tests(
        MarketQuoteService(NullAuthenticatedQuoteAdapter())
    )
    try:
        request = CompositionRequest(
            financial_statements=_client_statements(),
            current_market_price=70.0,
            ticker=TICKER,
        )
        result = PlatformOrchestrator(platform_version="0.7.0").execute(request)
        assert result.ok is False
        assert result.metadata.failed_stage in {"financial", "valuation"}
        assert any(DATA_UNAVAILABLE in e for e in result.errors)
        assert result.investment_recommendation is None
    finally:
        reset_financial_statement_service_for_tests(None)
        reset_market_quote_service_for_tests(None)


def test_unauthenticated_memory_adapter_rejected() -> None:
    """Memory adapters without api_key are not authenticated."""
    stmt = InMemoryAuthenticatedStatementAdapter(api_key=None)
    stmt.put(_seed_statements())
    quote = InMemoryAuthenticatedQuoteAdapter(api_key=None)
    quote.put(_seed_quote())
    reset_financial_statement_service_for_tests(FinancialStatementService(stmt))
    reset_market_quote_service_for_tests(MarketQuoteService(quote))
    try:
        with pytest.raises(AuthenticatedValuationError, match="Data unavailable"):
            load_authenticated_valuation_bundle(TICKER)
    finally:
        reset_financial_statement_service_for_tests(None)
        reset_market_quote_service_for_tests(None)


def test_invalid_period_rejected() -> None:
    with pytest.raises(Exception):
        # Contract/validation rejects implausible fiscal years at build time,
        # or bundle loader rejects them — either is fail-closed.
        bad = build_statements_from_mapping(
            symbol=TICKER,
            payload={
                "identity": {"symbol": TICKER, "currency": "USD"},
                "reporting_currency": "USD",
                "periods": [
                    {
                        "period_type": "annual",
                        "fiscal_year": 1800,
                        "period_end": "1800-12-31",
                        "reporting_currency": "USD",
                        "income_statement": {"net_income": 1.0},
                        "balance_sheet": {"equity": 1.0},
                        "cash_flow": {},
                        "ratios": {},
                    }
                ],
            },
            provenance=_stmt_provenance(),
        )
        load_authenticated_valuation_bundle(
            TICKER,
            get_statements=lambda _s: bad,
            get_quote=lambda _s: _seed_quote(),
        )
