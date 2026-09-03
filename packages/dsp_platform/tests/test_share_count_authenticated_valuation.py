"""Authenticated valuation consumes ShareCountSnapshot only."""

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
    NullShareCountAdapter,
    ShareCountBasis,
    ShareCountProvenance,
    ShareCountService,
    build_quote_from_mapping,
    build_share_count_from_mapping,
    build_statements_from_mapping,
)
from dsp_platform import (
    DATA_UNAVAILABLE,
    AuthenticatedValuationError,
    CompositionRequest,
    PlatformOrchestrator,
    load_authenticated_valuation_bundle,
)
from dsp_platform.financial_statements import (
    reset_financial_statement_service_for_tests,
)
from dsp_platform.market_quotes import reset_market_quote_service_for_tests
from dsp_platform.share_counts import (
    install_memory_share_count_for_tests,
    reset_share_count_service_for_tests,
)
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

TICKER = "TEST"
FIXED = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


def _stmt_provenance() -> FinancialStatementProvenance:
    return FinancialStatementProvenance(
        provider_id="memory_authenticated_statements",
        provider_name="Memory Statements",
        source_type="licensed_vendor",
        retrieved_at=FIXED,
        auth_mode="api_key",
    )


def _seed_statements(
    symbol: str = TICKER,
    *,
    isin: str | None = None,
    exchange: str = "NYSE",
    net_income: float = 100.0,
    eps_basic: float = 1.0,
    extra_income: dict | None = None,
):
    income = {
        "revenue": 500.0,
        "net_income": net_income,
        "eps_basic": eps_basic,
        "operating_income": 120.0,
    }
    if extra_income:
        income.update(extra_income)
    identity = {
        "symbol": symbol,
        "exchange": exchange,
        "company_name": "Test Corp",
        "currency": "USD",
    }
    if isin:
        identity["isin"] = isin
    return build_statements_from_mapping(
        symbol=symbol,
        payload={
            "identity": identity,
            "reporting_currency": "USD",
            "statement_basis": "consolidated",
            "unit_scale": "actual",
            "periods": [
                {
                    "period_type": "annual",
                    "fiscal_year": 2024,
                    "period_end": "2024-12-31",
                    "filing_date": "2025-02-01",
                    "reporting_currency": "USD",
                    "restated": False,
                    "income_statement": income,
                    "balance_sheet": {
                        "cash": 50.0,
                        "total_assets": 1500.0,
                        "total_liabilities": 500.0,
                        "equity": 1000.0,
                        "total_debt": 200.0,
                    },
                    "cash_flow": {
                        "operating_cash_flow": 150.0,
                        "capex": -30.0,
                        "free_cash_flow": 120.0,
                    },
                    "ratios": {},
                }
            ],
        },
        provenance=_stmt_provenance(),
    )


def _seed_quote(
    symbol: str = TICKER,
    *,
    price: float = 8.0,
    shares: float | None = 999.0,
    market_cap: float | None = None,
    volume: float | None = None,
    extra: dict | None = None,
):
    payload = {
        "exchange": "NYSE",
        "currency": "USD",
        "current_price": price,
        "previous_close": price,
        "market_cap": market_cap if market_cap is not None else price * 100.0,
        "shares_outstanding": shares,
        "volume": volume,
    }
    if extra:
        payload.update(extra)
    return build_quote_from_mapping(
        symbol=symbol,
        payload=payload,
        provenance=MarketQuoteProvenance(
            provider_id="memory_authenticated_quote",
            provider_name="Memory Quote",
            source_type="licensed_vendor",
            retrieved_at=FIXED,
            auth_mode="api_key",
        ),
    )


def _test_share_count(
    *,
    symbol: str = TICKER,
    shares: float | None = 100.0,
    exchange: str | None = "NYSE",
    isin: str | None = None,
    basis: ShareCountBasis = ShareCountBasis.CURRENT_OUTSTANDING,
    provider_id: str = "memory_authenticated_share_count",
    metadata: dict | None = None,
):
    """TEST-ONLY synthetic authenticated ShareCountSnapshot. Not a real company."""
    return build_share_count_from_mapping(
        symbol=symbol,
        payload={"exchange": exchange, "isin": isin, "shares": shares},
        provenance=ShareCountProvenance(
            provider_id=provider_id,
            provider_name="TEST-ONLY synthetic share count fixture",
            source_type="licensed_vendor",
            retrieved_at=FIXED,
            auth_mode="api_key",
            metadata=metadata or {"evidence_class": "test_fixture"},
        ),
        basis=basis,
    )


def _install_quote_statements(*, quote=None, statements=None) -> None:
    stmt_adapter = InMemoryAuthenticatedStatementAdapter(api_key="test-key")
    stmt_adapter.put(statements or _seed_statements())
    quote_adapter = InMemoryAuthenticatedQuoteAdapter(api_key="test-key")
    quote_adapter.put(quote or _seed_quote())
    reset_financial_statement_service_for_tests(FinancialStatementService(stmt_adapter))
    reset_market_quote_service_for_tests(MarketQuoteService(quote_adapter))


@pytest.fixture
def cleanup_services():
    yield
    reset_financial_statement_service_for_tests(None)
    reset_market_quote_service_for_tests(None)
    reset_share_count_service_for_tests(None)


def test_quote_and_statements_without_share_count_fail_closed(cleanup_services) -> None:
    _install_quote_statements()
    reset_share_count_service_for_tests(ShareCountService(NullShareCountAdapter()))
    with pytest.raises(
        AuthenticatedValuationError,
        match=r"authenticated shares outstanding unavailable",
    ):
        load_authenticated_valuation_bundle(TICKER)


def test_missing_share_count_produces_no_iv_mos(
    cleanup_services, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    _install_quote_statements()
    reset_share_count_service_for_tests(ShareCountService(NullShareCountAdapter()))
    request = CompositionRequest(
        financial_statements=FinancialStatements(
            period=FinancialPeriod(
                period_type=PeriodType.ANNUAL,
                period_end=date(2024, 12, 31),
                fiscal_year=2024,
                currency=CurrencyRef(CurrencyCode.USD),
            ),
            income_statement=IncomeStatement(revenue=1.0, net_income=1.0, eps=0.01),
            balance_sheet=BalanceSheet(equity=1.0, total_equity=1.0, total_assets=2.0),
            cash_flow=CashFlowStatement(operating_cash_flow=1.0, capex=-0.1),
            statement_metadata=StatementMetadata(unit_scale=UnitScale.ACTUAL),
        ),
        current_market_price=8.0,
        ticker=TICKER,
    )
    result = PlatformOrchestrator(platform_version="0.7.0").execute(request)
    assert result.ok is False
    assert any(DATA_UNAVAILABLE in e for e in result.errors)
    assert result.investment_recommendation is None
    signals = result.valuation_signals or result.valuation
    if signals is not None:
        assert getattr(signals, "intrinsic_value_per_share", None) is None
        assert getattr(signals, "margin_of_safety", None) is None


def test_synthetic_share_count_builds_bundle(cleanup_services) -> None:
    _install_quote_statements(quote=_seed_quote(shares=999.0))
    snap = _test_share_count(shares=100.0)
    install_memory_share_count_for_tests(snap)
    bundle = load_authenticated_valuation_bundle(TICKER)
    assert bundle.shares_outstanding == pytest.approx(100.0)
    assert bundle.shares_outstanding != pytest.approx(999.0)
    assert bundle.share_count_provenance["provider_id"] == (
        "memory_authenticated_share_count"
    )
    assert bundle.quote_provenance["provider_id"] == "memory_authenticated_quote"
    assert (
        bundle.share_count_provenance["provider_id"]
        != bundle.quote_provenance["provider_id"]
    )


def test_quote_shares_cannot_override_snapshot(cleanup_services) -> None:
    _install_quote_statements(quote=_seed_quote(shares=1.0))
    install_memory_share_count_for_tests(_test_share_count(shares=100.0))
    bundle = load_authenticated_valuation_bundle(TICKER)
    assert bundle.shares_outstanding == pytest.approx(100.0)


def test_statement_eps_cannot_populate_shares(cleanup_services) -> None:
    # NI=100, EPS=1 ⇒ implied 100 shares — must not fill when ShareCountPort is Null.
    _install_quote_statements(
        quote=_seed_quote(shares=None),
        statements=_seed_statements(net_income=100.0, eps_basic=1.0),
    )
    reset_share_count_service_for_tests(ShareCountService(NullShareCountAdapter()))
    with pytest.raises(AuthenticatedValuationError, match="shares outstanding"):
        load_authenticated_valuation_bundle(TICKER)


def test_price_market_cap_cannot_populate_shares(cleanup_services) -> None:
    _install_quote_statements(
        quote=_seed_quote(shares=None, price=10.0, market_cap=1_000.0),
    )
    reset_share_count_service_for_tests(ShareCountService(NullShareCountAdapter()))
    with pytest.raises(AuthenticatedValuationError, match="shares outstanding"):
        load_authenticated_valuation_bundle(TICKER)


def test_weighted_average_basis_cannot_populate_valuation_shares(
    cleanup_services,
) -> None:
    _install_quote_statements()
    install_memory_share_count_for_tests(
        _test_share_count(shares=100.0, basis=ShareCountBasis.WEIGHTED_AVERAGE_DILUTED)
    )
    with pytest.raises(AuthenticatedValuationError, match="shares outstanding"):
        load_authenticated_valuation_bundle(TICKER)


def test_volume_and_shareholding_cannot_populate_shares(cleanup_services) -> None:
    _install_quote_statements(
        quote=_seed_quote(
            shares=None,
            volume=50_000_000.0,
            extra={"dividend_yield": 0.12},
        )
    )
    reset_share_count_service_for_tests(ShareCountService(NullShareCountAdapter()))
    with pytest.raises(AuthenticatedValuationError, match="shares outstanding"):
        load_authenticated_valuation_bundle(TICKER)


def test_equity_capital_cannot_populate_shares(cleanup_services) -> None:
    _install_quote_statements(
        statements=_seed_statements(extra_income={"equity_capital": 50.0}),
        quote=_seed_quote(shares=None),
    )
    reset_share_count_service_for_tests(ShareCountService(NullShareCountAdapter()))
    with pytest.raises(AuthenticatedValuationError, match="shares outstanding"):
        load_authenticated_valuation_bundle(TICKER)


def test_open_interest_cannot_populate_shares(cleanup_services) -> None:
    _install_quote_statements(
        quote=_seed_quote(shares=None, extra={"oi": 12_345.0}),
    )
    reset_share_count_service_for_tests(ShareCountService(NullShareCountAdapter()))
    with pytest.raises(AuthenticatedValuationError, match="shares outstanding"):
        load_authenticated_valuation_bundle(TICKER)


def test_isin_mismatch_fails_closed(cleanup_services) -> None:
    _install_quote_statements(
        statements=_seed_statements(isin="US1111111111"),
    )
    install_memory_share_count_for_tests(
        _test_share_count(shares=100.0, isin="INE467B01029")
    )
    with pytest.raises(AuthenticatedValuationError, match="ISIN"):
        load_authenticated_valuation_bundle(TICKER)


def test_matching_isin_accepted(cleanup_services) -> None:
    _install_quote_statements(statements=_seed_statements(isin="US0000000001"))
    install_memory_share_count_for_tests(
        _test_share_count(shares=100.0, isin="US0000000001")
    )
    bundle = load_authenticated_valuation_bundle(TICKER)
    assert bundle.shares_outstanding == pytest.approx(100.0)


def test_exchange_mismatch_fails_closed(cleanup_services) -> None:
    _install_quote_statements()
    install_memory_share_count_for_tests(
        _test_share_count(shares=100.0, exchange="NSE")
    )
    with pytest.raises(AuthenticatedValuationError, match="exchange"):
        load_authenticated_valuation_bundle(TICKER, exchange="NYSE")


def test_share_count_provenance_has_no_secrets(cleanup_services) -> None:
    _install_quote_statements()
    install_memory_share_count_for_tests(
        _test_share_count(
            shares=100.0,
            metadata={
                "evidence_class": "test_fixture",
                "api_key": "should-not-leak",
                "endpoint": "/internal/shares",
            },
        )
    )
    bundle = load_authenticated_valuation_bundle(TICKER)
    blob = str(bundle.to_trace_dict())
    assert "should-not-leak" not in blob
    assert bundle.share_count_provenance["provider_id"]
    assert "api_key" not in (bundle.share_count_provenance.get("metadata") or {})
