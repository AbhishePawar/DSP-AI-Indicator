"""Shared fixtures for Investment Recommendation tests."""

from __future__ import annotations

from datetime import date

import pytest

from business_quality import BusinessQualityEngine
from business_quality_aggregator import BusinessQualityAggregatorEngine
from earnings_quality import EarningsQualityEngine
from economic_moat import EconomicEngine
from financial import (
    BalanceSheet,
    CashFlowStatement,
    CurrencyCode,
    CurrencyRef,
    FinancialAnalysis,
    FinancialEngine,
    FinancialPeriod,
    FinancialStatements,
    IncomeStatement,
    PeriodType,
    UnitScale,
)
from financial.metadata import StatementMetadata
from financial_strength import FinancialStrengthEngine
from growth_quality import GrowthQualityEngine
from investment_recommendation import ValuationSignals
from management_quality import ManagementEngine


@pytest.fixture
def financial_analysis() -> FinancialAnalysis:
    period = FinancialPeriod(
        period_type=PeriodType.ANNUAL,
        period_end=date(2024, 12, 31),
        fiscal_year=2024,
        currency=CurrencyRef(CurrencyCode.USD),
    )
    statements = FinancialStatements(
        period=period,
        income_statement=IncomeStatement(
            revenue=1000.0, cogs=400.0, gross_profit=600.0, ebit=300.0,
            ebitda=350.0, interest_expense=20.0, pretax_income=280.0,
            tax=70.0, net_income=210.0, weighted_shares=100.0, eps=2.1,
        ),
        balance_sheet=BalanceSheet(
            cash=150.0, short_term_investments=50.0, accounts_receivable=120.0,
            inventory=80.0, current_assets=450.0, ppe=400.0, goodwill=50.0,
            intangibles=50.0, total_assets=1000.0, accounts_payable=60.0,
            short_term_debt=50.0, current_liabilities=200.0,
            long_term_debt=200.0, total_liabilities=400.0,
            retained_earnings=300.0, equity=600.0, total_equity=600.0,
        ),
        cash_flow=CashFlowStatement(
            operating_cash_flow=250.0, capex=-80.0, free_cash_flow=170.0,
            dividends_paid=-50.0, share_buybacks=-30.0, debt_issued=10.0,
            debt_repaid=-40.0,
        ),
        statement_metadata=StatementMetadata(unit_scale=UnitScale.MILLIONS),
    )
    return FinancialEngine().analyze_financials(statements)


@pytest.fixture
def business_quality_analysis(financial_analysis: FinancialAnalysis):
    return BusinessQualityEngine().analyze(financial_analysis)


@pytest.fixture
def domain_bundle(financial_analysis, business_quality_analysis):
    em = EconomicEngine().analyze(financial_analysis, business_quality_analysis)
    mq = ManagementEngine().analyze(financial_analysis, business_quality_analysis)
    fs = FinancialStrengthEngine().analyze(
        financial_analysis, business_quality_analysis
    )
    eq = EarningsQualityEngine().analyze(
        financial_analysis, business_quality_analysis
    )
    gq = GrowthQualityEngine().analyze(
        financial_analysis, business_quality_analysis
    )
    bq = BusinessQualityAggregatorEngine().analyze(
        economic_moat=em,
        management_quality=mq,
        financial_strength=fs,
        earnings_quality=eq,
        growth_quality=gq,
    )
    return {
        "business_quality": bq,
        "economic_moat": em,
        "management_quality": mq,
        "financial_strength": fs,
        "earnings_quality": eq,
        "growth_quality": gq,
    }


@pytest.fixture
def undervalued_signals() -> ValuationSignals:
    return ValuationSignals(
        intrinsic_value_per_share=100.0,
        current_market_price=70.0,
        confidence=0.7,
    )


@pytest.fixture
def overvalued_signals() -> ValuationSignals:
    return ValuationSignals(
        intrinsic_value_per_share=100.0,
        current_market_price=140.0,
        confidence=0.7,
    )
