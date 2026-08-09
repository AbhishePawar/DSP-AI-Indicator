"""Investment-engine functional honesty — fail-closed scoring defects (CV-001/005)."""

from __future__ import annotations

from datetime import date

import pytest

from financial import (
    CurrencyCode,
    CurrencyRef,
    FinancialPeriod,
    FinancialStatements,
    IncomeStatement,
    IncomeStatementEngine,
    PeriodType,
    UnitScale,
)
from financial.metadata import StatementMetadata
from investment_recommendation import (
    InvestmentRecommendationAction,
    action_from_score,
)
from investment_recommendation.valuation_signals import ValuationSignals
from management_quality.rules import evaluate_capital_allocation


def _period(
    *,
    end: date,
    period_type: PeriodType = PeriodType.ANNUAL,
    fy: int | None = None,
    fq: int | None = None,
) -> FinancialPeriod:
    return FinancialPeriod(
        period_type=period_type,
        period_end=end,
        fiscal_year=fy,
        fiscal_quarter=fq,
        currency=CurrencyRef(CurrencyCode.USD),
    )


def _income(revenue: float) -> IncomeStatement:
    return IncomeStatement(
        revenue=revenue,
        cogs=40.0,
        gross_profit=revenue - 40.0,
        operating_expenses=20.0,
        ebit=40.0,
        ebitda=45.0,
        interest_expense=1.0,
        pretax_income=39.0,
        tax=10.0,
        net_income=29.0,
        weighted_shares=10.0,
        eps=2.9,
    )


def _stmt(income: IncomeStatement, period: FinancialPeriod) -> FinancialStatements:
    return FinancialStatements(
        period=period,
        income_statement=income,
        statement_metadata=StatementMetadata(unit_scale=UnitScale.MILLIONS),
    )


def test_action_from_score_none_is_unavailable_not_hold() -> None:
    assert action_from_score(None) is InvestmentRecommendationAction.UNAVAILABLE
    assert action_from_score(None) is not InvestmentRecommendationAction.HOLD


def test_mos_unavailable_and_score_none_never_hold() -> None:
    """Missing IV/price → MoS unavailable; None score → UNAVAILABLE action."""
    from investment_recommendation.adapters import extract_margin_of_safety

    mos = extract_margin_of_safety(
        ValuationSignals(
            intrinsic_value_per_share=None,
            current_market_price=None,
            confidence=0.0,
        ),
        business_quality_confidence=None,
    )
    assert mos.classification == "unavailable"
    assert mos.margin_of_safety is None
    assert mos.valuation_score is None
    assert action_from_score(mos.valuation_score) is InvestmentRecommendationAction.UNAVAILABLE


def test_revenue_cagr_ignores_quarterly_period_count() -> None:
    """Four quarterly points must not produce a multi-year CAGR."""
    engine = IncomeStatementEngine()
    incomes = [
        _income(100.0),
        _income(110.0),
        _income(120.0),
        _income(130.0),
    ]
    stmts = [
        _stmt(
            incomes[0],
            _period(end=date(2024, 3, 31), period_type=PeriodType.QUARTERLY, fy=2024, fq=1),
        ),
        _stmt(
            incomes[1],
            _period(end=date(2024, 6, 30), period_type=PeriodType.QUARTERLY, fy=2024, fq=2),
        ),
        _stmt(
            incomes[2],
            _period(end=date(2024, 9, 30), period_type=PeriodType.QUARTERLY, fy=2024, fq=3),
        ),
        _stmt(
            incomes[3],
            _period(end=date(2024, 12, 31), period_type=PeriodType.QUARTERLY, fy=2024, fq=4),
        ),
    ]
    metrics = engine._revenue(incomes, stmts, [])  # noqa: SLF001
    assert metrics.cagr is None
    assert metrics.yoy_growth is None


def test_revenue_cagr_uses_annual_fiscal_years() -> None:
    engine = IncomeStatementEngine()
    incomes = [_income(100.0), _income(110.0), _income(121.0)]
    stmts = [
        _stmt(incomes[0], _period(end=date(2022, 12, 31), fy=2022)),
        _stmt(incomes[1], _period(end=date(2023, 12, 31), fy=2023)),
        _stmt(incomes[2], _period(end=date(2024, 12, 31), fy=2024)),
    ]
    metrics = engine._revenue(incomes, stmts, [])  # noqa: SLF001
    assert metrics.cagr is not None
    assert abs(metrics.cagr - 0.10) < 1e-6
    assert metrics.yoy_growth is not None


def test_dilution_does_not_use_debt_reduction_discipline() -> None:
    class _Score:
        def __init__(self, value: float) -> None:
            self.value = value
            self.status = "assessed"

    class _CA:
        debt_reduction_discipline = _Score(0.95)

    class _BQ:
        capital_allocation = _CA()
        competitive_position = None

    class _FA:
        ratios = None

    component = evaluate_capital_allocation(_FA(), _BQ(), weight=1.0)
    # Debt-reduction alone must not be scored as dilution / capital allocation.
    assert component.score.value is None or component.status == "insufficient_data"


def test_eps_cagr_positive_annual_series() -> None:
    engine = IncomeStatementEngine()
    incomes = [
        IncomeStatement(
            revenue=100.0,
            net_income=10.0,
            eps=1.0,
            diluted_eps=0.90,
            weighted_shares=100.0,
        ),
        IncomeStatement(
            revenue=121.0,
            net_income=12.1,
            eps=1.21,
            diluted_eps=1.089,
            weighted_shares=100.0,
        ),
    ]
    stmts = [
        _stmt(incomes[0], _period(end=date(2022, 12, 31), fy=2022)),
        _stmt(incomes[1], _period(end=date(2024, 12, 31), fy=2024)),
    ]
    result = engine.analyze(stmts)
    assert result.profitability.eps_cagr_basis == "diluted"
    assert result.profitability.eps_cagr is not None
    assert abs(result.profitability.eps_cagr - 0.10) < 1e-5
    assert result.profitability.share_dilution_rate == 0.0


def test_eps_cagr_negative_to_positive_unavailable() -> None:
    engine = IncomeStatementEngine()
    incomes = [
        IncomeStatement(revenue=100.0, eps=-1.0, diluted_eps=-1.0, weighted_shares=100.0),
        IncomeStatement(revenue=110.0, eps=1.0, diluted_eps=1.0, weighted_shares=100.0),
    ]
    stmts = [
        _stmt(incomes[0], _period(end=date(2022, 12, 31), fy=2022)),
        _stmt(incomes[1], _period(end=date(2024, 12, 31), fy=2024)),
    ]
    result = engine.analyze(stmts)
    assert result.profitability.eps_cagr is None
    assert result.profitability.eps_cagr_basis == "unavailable"


def test_share_dilution_from_weighted_shares_not_buybacks() -> None:
    engine = IncomeStatementEngine()
    incomes = [
        IncomeStatement(revenue=100.0, weighted_shares=100.0, eps=1.0),
        IncomeStatement(revenue=110.0, weighted_shares=120.0, eps=1.1),
    ]
    stmts = [
        _stmt(incomes[0], _period(end=date(2022, 12, 31), fy=2022)),
        _stmt(incomes[1], _period(end=date(2024, 12, 31), fy=2024)),
    ]
    result = engine.analyze(stmts)
    assert result.profitability.share_dilution_rate == pytest.approx(0.20)
    assert result.profitability.dilution_discipline is not None
    assert result.profitability.dilution_discipline < 0.85
