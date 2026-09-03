"""P1-02 — financial statement integrity on authenticated valuation path."""

from __future__ import annotations

from datetime import UTC, datetime

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
from dsp_platform import (
    AuthenticatedValuationError,
    load_authenticated_valuation_bundle,
)
from dsp_platform.composition.financial_integrity import (
    normalize_periods_to_actual,
    unit_scale_factor,
)
from dsp_platform.financial_statements import (
    reset_financial_statement_service_for_tests,
)
from dsp_platform.market_quotes import reset_market_quote_service_for_tests
from dsp_platform.share_counts import (
    install_memory_share_count_for_tests,
    reset_share_count_service_for_tests,
)

TICKER = "TEST"
FIXED = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


def _prov() -> FinancialStatementProvenance:
    return FinancialStatementProvenance(
        provider_id="memory_authenticated_statements",
        provider_name="Memory",
        source_type="licensed_vendor",
        retrieved_at=FIXED,
        auth_mode="api_key",
    )


def _period(
    *,
    revenue: float = 500.0,
    net_income: float = 100.0,
    eps: float = 1.0,
    equity: float = 1000.0,
    assets: float = 1500.0,
    liabilities: float = 500.0,
    ocf: float = 150.0,
    capex: float = -30.0,
    fcf: float = 120.0,
    basis: str = "consolidated",
    unit: str = "actual",
    period_type: str = "annual",
    fiscal_year: int = 2024,
    fiscal_quarter: int | None = None,
    period_end: str = "2024-12-31",
    operating_income: float = 120.0,
) -> dict:
    return {
        "period_type": period_type,
        "fiscal_year": fiscal_year,
        "fiscal_quarter": fiscal_quarter,
        "period_end": period_end,
        "reporting_currency": "USD",
        "statement_basis": basis,
        "unit_scale": unit,
        "income_statement": {
            "revenue": revenue,
            "net_income": net_income,
            "eps_basic": eps,
            "operating_income": operating_income,
        },
        "balance_sheet": {
            "cash": 50.0,
            "total_assets": assets,
            "total_liabilities": liabilities,
            "equity": equity,
        },
        "cash_flow": {
            "operating_cash_flow": ocf,
            "capex": capex,
            "free_cash_flow": fcf,
        },
        "ratios": {},
    }


def _statements(periods: list[dict], *, currency: str = "USD"):
    return build_statements_from_mapping(
        symbol=TICKER,
        payload={
            "identity": {
                "symbol": TICKER,
                "exchange": "NYSE",
                "company_name": "Test Corp",
                "currency": currency,
            },
            "reporting_currency": currency,
            "periods": periods,
        },
        provenance=_prov(),
    )


def _quote(
    *,
    price: float = 8.0,
    shares: float = 100.0,
    currency: str = "USD",
    market_cap: float | None = None,
):
    return build_quote_from_mapping(
        symbol=TICKER,
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
            provider_name="Memory",
            source_type="licensed_vendor",
            retrieved_at=FIXED,
            auth_mode="api_key",
        ),
    )


def _seed_share_count(*, shares: float = 100.0, exchange: str = "NYSE") -> None:
    install_memory_share_count_for_tests(
        build_share_count_from_mapping(
            symbol=TICKER,
            payload={"exchange": exchange, "shares": shares},
            provenance=ShareCountProvenance(
                provider_id="memory_authenticated_share_count",
                provider_name="TEST-ONLY synthetic share count fixture",
                source_type="licensed_vendor",
                retrieved_at=FIXED,
                auth_mode="api_key",
                metadata={"evidence_class": "test_fixture"},
            ),
        )
    )


def _seed(periods: list[dict], quote=None, *, share_count_shares: float = 100.0):
    stmt = InMemoryAuthenticatedStatementAdapter(api_key="k")
    stmt.put(_statements(periods))
    q = InMemoryAuthenticatedQuoteAdapter(api_key="k")
    q.put(quote or _quote())
    reset_financial_statement_service_for_tests(FinancialStatementService(stmt))
    reset_market_quote_service_for_tests(MarketQuoteService(q))
    _seed_share_count(shares=share_count_shares)


@pytest.fixture(autouse=True)
def _cleanup_services():
    yield
    reset_financial_statement_service_for_tests(None)
    reset_market_quote_service_for_tests(None)
    reset_share_count_service_for_tests(None)


def test_valid_consolidated_passes() -> None:
    _seed([_period()])
    bundle = load_authenticated_valuation_bundle(TICKER)
    assert bundle.statement_basis == "consolidated"
    assert bundle.unit_scale == "actual"
    assert bundle.financial_snapshot.latest.total_equity == pytest.approx(1000.0)


def test_valid_standalone_passes() -> None:
    _seed([_period(basis="standalone")])
    bundle = load_authenticated_valuation_bundle(TICKER)
    assert bundle.statement_basis == "standalone"


def test_mixed_basis_rejected() -> None:
    _seed(
        [
            _period(basis="consolidated"),
            _period(
                basis="standalone",
                fiscal_year=2023,
                period_end="2023-12-31",
                net_income=90.0,
                eps=0.9,
                fcf=105.0,
                ocf=130.0,
                capex=-25.0,
            ),
        ]
    )
    with pytest.raises(AuthenticatedValuationError, match="consolidated/standalone"):
        load_authenticated_valuation_bundle(TICKER)


def test_missing_basis_rejected() -> None:
    p = _period()
    del p["statement_basis"]
    _seed([p])
    with pytest.raises(AuthenticatedValuationError, match="statement_basis"):
        load_authenticated_valuation_bundle(TICKER)


def test_unit_normalization_crore_equals_lakh() -> None:
    # ₹100 crore == ₹1,000 lakh == ₹1,000,000,000 actual
    crore_period = _period(
        revenue=100.0,
        net_income=10.0,
        eps=1.0,
        unit="crore",
        equity=200.0,
        assets=300.0,
        liabilities=100.0,
        ocf=15.0,
        capex=-3.0,
        fcf=12.0,
        operating_income=12.0,
    )
    # shares for EPS consistency: NI/EPS = 10/1 = 10 in crore units → after scale NI=1e8, need shares still 100 for quote
    # Use eps scaled conceptually: after normalize NI=10*1e7=1e8, eps stays 1.0 → derived shares huge.
    # Better: keep eps consistent with ACTUAL after scale by setting eps = NI_actual/shares.
    # For crore: NI=10 crore = 1e8, shares=100 → eps should be 1e6
    crore_period["income_statement"]["eps_basic"] = 1_000_000.0
    crore_period["income_statement"]["net_income"] = 10.0
    _seed([crore_period], quote=_quote(shares=100.0, price=8.0, market_cap=800.0))
    # market_cap 800 vs price*shares 800 OK; but equity etc in crore
    bundle_c = load_authenticated_valuation_bundle(TICKER)
    assert bundle_c.financial_snapshot.latest.revenue == pytest.approx(1_000_000_000.0)
    assert bundle_c.financial_snapshot.latest.net_income == pytest.approx(100_000_000.0)

    reset_financial_statement_service_for_tests(None)
    reset_market_quote_service_for_tests(None)

    lakh_period = _period(
        revenue=10_000.0,  # 10000 lakh = 100 crore
        net_income=1_000.0,  # 1000 lakh = 10 crore
        eps=1_000_000.0,
        unit="lakh",
        equity=20_000.0,
        assets=30_000.0,
        liabilities=10_000.0,
        ocf=1_500.0,
        capex=-300.0,
        fcf=1_200.0,
        operating_income=1_200.0,
    )
    _seed([lakh_period], quote=_quote(shares=100.0, price=8.0, market_cap=800.0))
    bundle_l = load_authenticated_valuation_bundle(TICKER)
    assert bundle_l.financial_snapshot.latest.revenue == pytest.approx(
        bundle_c.financial_snapshot.latest.revenue
    )
    assert bundle_l.financial_snapshot.latest.net_income == pytest.approx(
        bundle_c.financial_snapshot.latest.net_income
    )


def test_unit_scale_factor_invariants() -> None:
    assert unit_scale_factor("crore") * 100 == pytest.approx(
        unit_scale_factor("lakh") * 10_000
    )
    assert unit_scale_factor("millions") * 5 == pytest.approx(
        unit_scale_factor("thousands") * 5_000
    )


def test_mixed_units_rejected() -> None:
    _seed(
        [
            _period(unit="millions"),
            _period(
                unit="actual",
                fiscal_year=2023,
                period_end="2023-12-31",
                net_income=90.0,
                eps=0.9,
                fcf=105.0,
                ocf=130.0,
                capex=-25.0,
            ),
        ]
    )
    with pytest.raises(AuthenticatedValuationError, match="unit"):
        load_authenticated_valuation_bundle(TICKER)


def test_currency_mismatch_rejected() -> None:
    _seed([_period()], quote=_quote(currency="INR"))
    with pytest.raises(AuthenticatedValuationError, match="currency"):
        load_authenticated_valuation_bundle(TICKER)


def test_wrong_ticker_rejected() -> None:
    _seed([_period()])
    with pytest.raises(AuthenticatedValuationError, match="Data unavailable"):
        load_authenticated_valuation_bundle("OTHER")


def test_inconsistent_eps_shares_rejected() -> None:
    # NI=100, eps=1 ⇒ implied shares=100, but ShareCountSnapshot is 10.
    _seed(
        [_period(net_income=100.0, eps=1.0)],
        quote=_quote(shares=10.0, market_cap=80.0),
        share_count_shares=10.0,
    )
    with pytest.raises(AuthenticatedValuationError, match="share"):
        load_authenticated_valuation_bundle(TICKER)


def test_fcf_inconsistency_rejected() -> None:
    _seed([_period(ocf=150.0, capex=-30.0, fcf=999.0)])
    with pytest.raises(AuthenticatedValuationError, match="FCF"):
        load_authenticated_valuation_bundle(TICKER)


def test_negative_capex_normalized_for_valuation() -> None:
    _seed([_period(capex=-30.0, fcf=120.0, ocf=150.0)])
    bundle = load_authenticated_valuation_bundle(TICKER)
    # FundamentalStatement capex must be positive magnitude for ValuationEngine.
    assert bundle.financial_snapshot.latest.capital_expenditures == pytest.approx(30.0)


def test_balance_sheet_imbalance_rejected() -> None:
    _seed([_period(assets=1500.0, liabilities=100.0, equity=1000.0)])
    with pytest.raises(AuthenticatedValuationError, match="balance sheet"):
        load_authenticated_valuation_bundle(TICKER)


def test_duplicate_annual_period_rejected() -> None:
    _seed(
        [
            _period(
                period_type="annual",
                fiscal_year=2024,
                period_end="2024-12-31",
                fcf=120.0,
            ),
            _period(
                period_type="annual",
                fiscal_year=2024,
                period_end="2024-12-30",
                fcf=120.0,
            ),
        ]
    )
    with pytest.raises(AuthenticatedValuationError, match="duplicate"):
        load_authenticated_valuation_bundle(TICKER)


def test_quarterly_only_refused_for_authenticated_valuation() -> None:
    _seed(
        [
            _period(
                period_type="quarterly",
                fiscal_quarter=1,
                period_end="2024-03-31",
                fcf=120.0,
            ),
        ]
    )
    with pytest.raises(AuthenticatedValuationError, match="quarterly-only"):
        load_authenticated_valuation_bundle(TICKER)


def test_negative_revenue_rejected() -> None:
    _seed([_period(revenue=-10.0, operating_income=-5.0)])
    with pytest.raises(AuthenticatedValuationError, match="revenue"):
        load_authenticated_valuation_bundle(TICKER)


def test_missing_statements_rejected() -> None:
    q = InMemoryAuthenticatedQuoteAdapter(api_key="k")
    q.put(_quote())
    reset_market_quote_service_for_tests(MarketQuoteService(q))
    reset_financial_statement_service_for_tests(
        FinancialStatementService(InMemoryAuthenticatedStatementAdapter(api_key="k"))
    )
    with pytest.raises(AuthenticatedValuationError, match="Data unavailable"):
        load_authenticated_valuation_bundle(TICKER)


def test_normalize_periods_deterministic() -> None:
    bundle = _statements(
        [
            _period(
                unit="millions",
                revenue=5.0,
                net_income=1.0,
                eps=10_000.0,
                equity=10.0,
                assets=15.0,
                liabilities=5.0,
                ocf=1.5,
                capex=-0.3,
                fcf=1.2,
                operating_income=1.2,
            )
        ]
    )
    scaled = normalize_periods_to_actual(bundle.periods, source_unit="millions")
    scaled2 = normalize_periods_to_actual(bundle.periods, source_unit="millions")
    assert _sf(scaled[0].revenue) == pytest.approx(_sf(scaled2[0].revenue))
    assert _sf(scaled[0].revenue) == pytest.approx(5_000_000.0)


def _sf(field) -> float | None:
    if not field.available or field.value is None:
        return None
    return float(field.value)


def test_annual_and_quarterly_not_mixed_silently() -> None:
    # Homogeneous selector prefers annual; quarterly ignored — not mixed calc.
    _seed(
        [
            _period(period_type="annual"),
            _period(
                period_type="quarterly",
                fiscal_quarter=4,
                period_end="2024-09-30",
                revenue=999999.0,
                net_income=1.0,
                eps=0.01,
                fcf=120.0,
            ),
        ]
    )
    bundle = load_authenticated_valuation_bundle(TICKER)
    assert bundle.period_kind == "annual"
    assert bundle.financial_snapshot.latest.revenue == pytest.approx(500.0)
