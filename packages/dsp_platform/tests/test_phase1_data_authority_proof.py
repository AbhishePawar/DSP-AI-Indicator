"""Phase 1 verification — production data authority proof (CASE B).

Architecture is already hardened (P1-01). This file closes the coverage gap:

* forged client market price must not change MoS / IV / recommendation when
  authenticated server quote+statements are present;
* forged client financial line items (revenue, NI, EPS, shares, FCF, OCF,
  cash, debt, AR, Inv, AP) must not become FinancialAnalysis authority.

No production-code changes — regression proof only.
"""

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
    ShareCountProvenance,
    build_quote_from_mapping,
    build_share_count_from_mapping,
    build_statements_from_mapping,
)
from data_engine.evidence_classes import (
    G2_CLEARING_CLASS,
    NEVER_CLEARS_G2,
    TEST_FIXTURE,
    may_clear_g2,
)
from dsp_platform import (
    DATA_UNAVAILABLE,
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
FIXED_RETRIEVED = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


def _client_statements() -> FinancialStatements:
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


def _forged_client_statements() -> FinancialStatements:
    period = FinancialPeriod(
        period_type=PeriodType.ANNUAL,
        period_end=date(2024, 12, 31),
        fiscal_year=2024,
        currency=CurrencyRef(CurrencyCode.USD),
    )
    return FinancialStatements(
        period=period,
        income_statement=IncomeStatement(
            revenue=999_999.0,
            net_income=99_999.0,
            eps=999.0,
            diluted_eps=999.0,
            weighted_shares=1.0,
        ),
        balance_sheet=BalanceSheet(
            cash=0.01,
            accounts_receivable=99_999.0,
            inventory=99_999.0,
            accounts_payable=0.01,
            short_term_debt=99_999.0,
            long_term_debt=99_999.0,
            equity=1.0,
            total_equity=1.0,
            total_assets=2.0,
        ),
        cash_flow=CashFlowStatement(
            operating_cash_flow=0.01,
            free_cash_flow=0.01,
            capex=-0.01,
        ),
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
                    "income_statement": {
                        "revenue": 500.0,
                        "net_income": 100.0,
                        "eps_basic": 1.0,
                        "operating_income": 120.0,
                    },
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
        provenance=FinancialStatementProvenance(
            provider_id="memory_authenticated_statements",
            provider_name="Memory Statements",
            source_type="licensed_vendor",
            retrieved_at=FIXED_RETRIEVED,
            auth_mode="api_key",
        ),
    )


def _seed_quote(symbol: str = TICKER, *, price: float = 8.0, shares: float = 100.0):
    return build_quote_from_mapping(
        symbol=symbol,
        payload={
            "exchange": "NYSE",
            "currency": "USD",
            "current_price": price,
            "previous_close": price,
            "market_cap": price * shares,
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
def seeded_auth_services():
    stmt_adapter = InMemoryAuthenticatedStatementAdapter(api_key="phase1-key")
    stmt_adapter.put(_seed_statements())
    quote_adapter = InMemoryAuthenticatedQuoteAdapter(api_key="phase1-key")
    quote_adapter.put(_seed_quote())
    reset_financial_statement_service_for_tests(FinancialStatementService(stmt_adapter))
    reset_market_quote_service_for_tests(MarketQuoteService(quote_adapter))
    install_memory_share_count_for_tests(
        build_share_count_from_mapping(
            symbol=TICKER,
            payload={"exchange": "NYSE", "shares": 100.0},
            provenance=ShareCountProvenance(
                provider_id="memory_authenticated_share_count",
                provider_name="TEST-ONLY synthetic share count fixture",
                source_type="licensed_vendor",
                retrieved_at=FIXED_RETRIEVED,
                auth_mode="api_key",
                metadata={"evidence_class": "test_fixture"},
            ),
        )
    )
    yield
    reset_financial_statement_service_for_tests(None)
    reset_market_quote_service_for_tests(None)
    reset_share_count_service_for_tests(None)


def _signals(result):
    return result.valuation_signals or result.valuation


def test_market_price_forgery_ignored_when_auth_present(seeded_auth_services) -> None:
    """Mandatory: forged current_market_price must not change authoritative price/MoS."""
    legit = PlatformOrchestrator(platform_version="0.7.0").execute(
        CompositionRequest(
            financial_statements=_client_statements(),
            current_market_price=8.0,
            ticker=TICKER,
        )
    )
    forged = PlatformOrchestrator(platform_version="0.7.0").execute(
        CompositionRequest(
            financial_statements=_client_statements(),
            current_market_price=999_999.0,
            ticker=TICKER,
        )
    )
    assert legit.ok and forged.ok
    s1, s2 = _signals(legit), _signals(forged)
    assert s1.current_market_price == pytest.approx(8.0)
    assert s2.current_market_price == pytest.approx(8.0)
    assert s1.intrinsic_value_per_share == pytest.approx(s2.intrinsic_value_per_share)
    assert s1.margin_of_safety == pytest.approx(s2.margin_of_safety)
    assert forged.investment_recommendation is not None
    assert legit.investment_recommendation is not None
    assert (
        legit.investment_recommendation.recommendation
        == forged.investment_recommendation.recommendation
    )


def test_financial_line_item_forgery_ignored_when_auth_present(
    seeded_auth_services,
) -> None:
    """Client revenue/NI/EPS/shares/FCF/OCF/cash/debt/AR/Inv/AP must not win."""
    bundle = load_authenticated_valuation_bundle(TICKER)
    auth_revenue = bundle.financial_snapshot.latest.revenue

    legit = PlatformOrchestrator(platform_version="0.7.0").execute(
        CompositionRequest(
            financial_statements=_client_statements(),
            current_market_price=8.0,
            ticker=TICKER,
        )
    )
    forged = PlatformOrchestrator(platform_version="0.7.0").execute(
        CompositionRequest(
            financial_statements=_forged_client_statements(),
            current_market_price=999_999.0,
            ticker=TICKER,
        )
    )
    assert legit.ok and forged.ok

    fa_forged = forged.financial_analysis
    assert fa_forged is not None
    assert fa_forged.income.revenue.revenue == pytest.approx(auth_revenue)
    assert fa_forged.income.revenue.revenue != pytest.approx(999_999.0)

    s1, s2 = _signals(legit), _signals(forged)
    assert s1.current_market_price == pytest.approx(8.0)
    assert s2.current_market_price == pytest.approx(8.0)
    assert s1.intrinsic_value_per_share == pytest.approx(s2.intrinsic_value_per_share)
    assert s1.margin_of_safety == pytest.approx(s2.margin_of_safety)

    fin_warnings = next(s.warnings for s in forged.stages if s.stage == "financial")
    val_warnings = next(s.warnings for s in forged.stages if s.stage == "valuation")
    assert any(
        "P1-01" in w and "authenticated server statements" in w for w in fin_warnings
    )
    assert any(
        "P1-01" in w and "authenticated server data bundle" in w for w in val_warnings
    )


def test_production_rejects_client_only_financials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production: rich client payload without auth providers → fail closed."""
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    reset_financial_statement_service_for_tests(
        FinancialStatementService(InMemoryAuthenticatedStatementAdapter(api_key="k"))
    )
    reset_market_quote_service_for_tests(
        MarketQuoteService(InMemoryAuthenticatedQuoteAdapter(api_key="k"))
    )
    try:
        result = PlatformOrchestrator(platform_version="0.7.0").execute(
            CompositionRequest(
                financial_statements=_forged_client_statements(),
                current_market_price=70.0,
                ticker=TICKER,
            )
        )
        assert result.ok is False
        assert any(DATA_UNAVAILABLE in e for e in result.errors)
        assert result.investment_recommendation is None
    finally:
        reset_financial_statement_service_for_tests(None)
        reset_market_quote_service_for_tests(None)


def test_fixture_evidence_cannot_clear_g2() -> None:
    assert may_clear_g2(TEST_FIXTURE) is False
    assert TEST_FIXTURE in NEVER_CLEARS_G2
    for cls in (
        "public_web",
        "public_filing",
        "test_fixture",
        "credentials_unavailable",
        "memory",
        "seed",
        "offline",
        "mock",
    ):
        assert may_clear_g2(cls) is False
        assert cls in NEVER_CLEARS_G2
    assert may_clear_g2(G2_CLEARING_CLASS) is True
    assert G2_CLEARING_CLASS == "real_live_authenticated_provider"
