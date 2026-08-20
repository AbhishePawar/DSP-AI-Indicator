"""Financial derivation policy: REPORTED / CALCULATED / UNAVAILABLE.

Uses U4-shaped TCS/INR statement figures from the Upstox fundamentals
fixtures (not live market guesses): revenue 150000, net income 30000,
total equity 120000.
"""

from __future__ import annotations

from datetime import date

from financial import (
    DERIVATION_ENGINE_VERSION,
    FORMULA_AVERAGE_BALANCE,
    FORMULA_CASH_RATIO,
    FORMULA_CURRENT_RATIO,
    FORMULA_FCF,
    FORMULA_FCF_MARGIN,
    FORMULA_GROSS_MARGIN,
    FORMULA_GROSS_MARGIN_FROM_COGS,
    FORMULA_NET_DEBT,
    FORMULA_QUICK_RATIO,
    FORMULA_ROE,
    FORMULA_WORKING_CAPITAL,
    FORMULA_WORKING_CAPITAL_TURNOVER,
    CurrencyCode,
    CurrencyRef,
    DerivationInput,
    FinancialEngine,
    FinancialValueStatus,
    PeriodType,
    UnitScale,
    as_reported,
    derive,
)
from financial.balance_sheet import BalanceSheet
from financial.income_statement import IncomeStatement
from financial.metadata import StatementMetadata
from financial.models import FinancialStatements
from financial.period import FinancialPeriod

_FY23 = date(2023, 3, 31)
_FY24 = date(2024, 3, 31)

# U4-shaped authenticated INR annual figures (test_u4_upstox_fundamentals).
_TCS_NI = 30_000.0
_TCS_REVENUE = 150_000.0
_TCS_EQUITY_END = 120_000.0
_TCS_EQUITY_BEGIN = 100_000.0
_TCS_COGS = 40_000.0
_TCS_GP = 110_000.0


def _tcs_period(end: date, fy: int) -> FinancialPeriod:
    return FinancialPeriod(
        period_type=PeriodType.ANNUAL,
        period_end=end,
        fiscal_year=fy,
        currency=CurrencyRef(code=CurrencyCode.INR),
        source="u4-shaped-fixture",
    )


def _tcs_statements() -> FinancialStatements:
    return FinancialStatements(
        period=_tcs_period(_FY24, 2024),
        income_statement=IncomeStatement(
            revenue=_TCS_REVENUE,
            cogs=_TCS_COGS,
            gross_profit=_TCS_GP,
            net_income=_TCS_NI,
        ),
        balance_sheet=BalanceSheet(total_equity=_TCS_EQUITY_END, equity=_TCS_EQUITY_END),
        statement_metadata=StatementMetadata(
            unit_scale=UnitScale.ACTUAL,
            currency=CurrencyRef(code=CurrencyCode.INR),
            source="u4-shaped-fixture",
        ),
    )


def _reported(
    field_id: str,
    value: float | None,
    *,
    period_end: date = _FY24,
    period_type: PeriodType | str | None = PeriodType.ANNUAL,
    unit_scale: UnitScale | str | None = UnitScale.ACTUAL,
    currency: CurrencyCode | str | None = CurrencyCode.INR,
    accounting_basis: str | None = "consolidated",
    status: FinancialValueStatus = FinancialValueStatus.REPORTED,
) -> DerivationInput:
    return DerivationInput(
        field_id=field_id,
        value=value,
        status=status,
        period_type=period_type,
        period_end=period_end,
        unit_scale=unit_scale,
        currency=currency,
        accounting_basis=accounting_basis,
        source="u4-shaped-fixture",
    )


class TestFinancialDerivationPolicy:
    def test_valid_deterministic_calculation_is_calculated(self) -> None:
        stmt = _tcs_statements()
        result = derive(
            FORMULA_ROE,
            {
                "net_income": _reported("net_income", stmt.income_statement.net_income),
                "beginning_equity": _reported(
                    "beginning_equity", _TCS_EQUITY_BEGIN, period_end=_FY23
                ),
                "ending_equity": _reported(
                    "ending_equity", stmt.balance_sheet.total_equity
                ),
            },
        )
        assert result.status is FinancialValueStatus.CALCULATED
        assert result.value == _TCS_NI / ((_TCS_EQUITY_BEGIN + _TCS_EQUITY_END) / 2.0)
        assert result.formula_id == FORMULA_ROE
        assert result.calculation_version == DERIVATION_ENGINE_VERSION
        assert result.unavailable_reason is None

    def test_missing_required_input_is_unavailable(self) -> None:
        result = derive(
            FORMULA_ROE,
            {
                "net_income": _reported("net_income", _TCS_NI),
                "ending_equity": _reported("ending_equity", _TCS_EQUITY_END),
            },
        )
        assert result.status is FinancialValueStatus.UNAVAILABLE
        assert result.value is None
        assert result.unavailable_reason == "missing_input"

    def test_missing_beginning_equity_is_unavailable_not_guessed(self) -> None:
        result = derive(
            FORMULA_ROE,
            {
                "net_income": _reported("net_income", _TCS_NI),
                "beginning_equity": _reported("beginning_equity", None, period_end=_FY23),
                "ending_equity": _reported("ending_equity", _TCS_EQUITY_END),
            },
        )
        assert result.status is FinancialValueStatus.UNAVAILABLE
        assert result.value is None

    def test_zero_denominator_is_unavailable(self) -> None:
        result = derive(
            FORMULA_GROSS_MARGIN,
            {
                "gross_profit": _reported("gross_profit", _TCS_GP),
                "revenue": _reported("revenue", 0.0),
            },
        )
        assert result.status is FinancialValueStatus.UNAVAILABLE
        assert result.value is None
        assert result.unavailable_reason == "division_by_zero"

    def test_period_mismatch_is_unavailable(self) -> None:
        result = derive(
            FORMULA_GROSS_MARGIN,
            {
                "gross_profit": _reported("gross_profit", _TCS_GP),
                "revenue": _reported(
                    "revenue", _TCS_REVENUE, period_type=PeriodType.QUARTERLY
                ),
            },
        )
        assert result.status is FinancialValueStatus.UNAVAILABLE
        assert result.unavailable_reason == "period_mismatch"

    def test_accounting_basis_mismatch_is_unavailable(self) -> None:
        result = derive(
            FORMULA_GROSS_MARGIN,
            {
                "gross_profit": _reported("gross_profit", _TCS_GP),
                "revenue": _reported(
                    "revenue", _TCS_REVENUE, accounting_basis="standalone"
                ),
            },
        )
        assert result.status is FinancialValueStatus.UNAVAILABLE
        assert result.unavailable_reason == "accounting_basis_mismatch"

    def test_unknown_unit_mismatch_is_unavailable(self) -> None:
        result = derive(
            FORMULA_WORKING_CAPITAL,
            {
                "current_assets": _reported("current_assets", 80_000.0),
                "current_liabilities": _reported(
                    "current_liabilities", 20_000.0, unit_scale="widgets"
                ),
            },
        )
        assert result.status is FinancialValueStatus.UNAVAILABLE
        assert result.unavailable_reason == "unit_mismatch"

    def test_explicit_unit_conversion_is_calculated(self) -> None:
        result = derive(
            FORMULA_WORKING_CAPITAL,
            {
                "current_assets": _reported(
                    "current_assets", 80.0, unit_scale=UnitScale.THOUSANDS
                ),
                "current_liabilities": _reported(
                    "current_liabilities", 0.02, unit_scale=UnitScale.MILLIONS
                ),
            },
        )
        assert result.status is FinancialValueStatus.CALCULATED
        assert result.value == 60_000.0
        assert result.unit_scale == "actual"
        assert result.compatibility["converted_to_actual"] is True

    def test_currency_mismatch_is_unavailable(self) -> None:
        result = derive(
            FORMULA_GROSS_MARGIN,
            {
                "gross_profit": _reported("gross_profit", _TCS_GP),
                "revenue": _reported(
                    "revenue", _TCS_REVENUE, currency=CurrencyCode.USD
                ),
            },
        )
        assert result.status is FinancialValueStatus.UNAVAILABLE
        assert result.unavailable_reason == "currency_mismatch"

    def test_provider_value_remains_reported(self) -> None:
        item = _reported("net_income", _TCS_NI)
        result = as_reported(item)
        assert result.status is FinancialValueStatus.REPORTED
        assert result.value == _TCS_NI
        assert result.formula is None
        assert result.formula_id is None
        assert result.inputs[0]["field_id"] == "net_income"
        assert result.inputs[0]["status"] == "reported"

    def test_calculated_value_cannot_be_mislabeled_as_reported(self) -> None:
        calculated = derive(
            FORMULA_GROSS_MARGIN,
            {
                "gross_profit": _reported("gross_profit", _TCS_GP),
                "revenue": _reported("revenue", _TCS_REVENUE),
            },
        )
        assert calculated.status is FinancialValueStatus.CALCULATED
        relabeled = as_reported(
            DerivationInput(
                field_id="gross_margin",
                value=calculated.value,
                status=FinancialValueStatus.CALCULATED,
                period_type=PeriodType.ANNUAL,
                period_end=_FY24,
                currency=CurrencyCode.INR,
                accounting_basis="consolidated",
                source="derivation",
            )
        )
        assert relabeled.status is FinancialValueStatus.UNAVAILABLE
        assert relabeled.unavailable_reason == "calculated_cannot_be_reported"
        assert relabeled.value is None

    def test_provenance_records_formula_and_inputs(self) -> None:
        result = derive(
            FORMULA_ROE,
            {
                "net_income": _reported("net_income", _TCS_NI),
                "beginning_equity": _reported(
                    "beginning_equity", _TCS_EQUITY_BEGIN, period_end=_FY23
                ),
                "ending_equity": _reported("ending_equity", _TCS_EQUITY_END),
            },
        )
        payload = result.to_dict()
        assert payload["status"] == "calculated"
        assert payload["formula"] == (
            "net_income / ((beginning_equity + ending_equity) / 2)"
        )
        ids = {item["field_id"] for item in payload["inputs"]}
        assert ids == {"net_income", "beginning_equity", "ending_equity"}
        assert all(item["status"] == "reported" for item in payload["inputs"])
        assert payload["calculation_version"] == DERIVATION_ENGINE_VERSION

    def test_alternate_gross_margin_formula_is_explicit_not_fallback(self) -> None:
        preferred = derive(
            FORMULA_GROSS_MARGIN,
            {
                "gross_profit": _reported("gross_profit", None),
                "revenue": _reported("revenue", _TCS_REVENUE),
            },
        )
        assert preferred.status is FinancialValueStatus.UNAVAILABLE
        alternate = derive(
            FORMULA_GROSS_MARGIN_FROM_COGS,
            {
                "revenue": _reported("revenue", _TCS_REVENUE),
                "cogs": _reported("cogs", _TCS_COGS),
            },
        )
        assert alternate.status is FinancialValueStatus.CALCULATED
        assert alternate.value == (_TCS_REVENUE - _TCS_COGS) / _TCS_REVENUE
        assert alternate.formula_id == FORMULA_GROSS_MARGIN_FROM_COGS

    def test_fcf_requires_both_ocf_and_capex(self) -> None:
        missing = derive(
            FORMULA_FCF,
            {"operating_cash_flow": _reported("operating_cash_flow", 40_000.0)},
        )
        assert missing.status is FinancialValueStatus.UNAVAILABLE
        ok = derive(
            FORMULA_FCF,
            {
                "operating_cash_flow": _reported("operating_cash_flow", 40_000.0),
                "capex": _reported("capex", -8_000.0),
            },
        )
        assert ok.status is FinancialValueStatus.CALCULATED
        assert ok.value == 32_000.0

    def test_financial_engine_exposes_derivation(self) -> None:
        engine = FinancialEngine()
        reported = engine.reported_value(_reported("total_equity", _TCS_EQUITY_END))
        assert reported.status is FinancialValueStatus.REPORTED
        calculated = engine.derive(
            FORMULA_WORKING_CAPITAL,
            {
                "current_assets": _reported("current_assets", 80_000.0),
                "current_liabilities": _reported("current_liabilities", 20_000.0),
            },
        )
        assert calculated.status is FinancialValueStatus.CALCULATED
        assert calculated.value == 60_000.0


class TestPhase3LiquidityFormulas:
    """Catalog coverage for liquidity formulas registered in Phase 3."""

    def test_current_ratio_is_calculated(self) -> None:
        result = derive(
            FORMULA_CURRENT_RATIO,
            {
                "current_assets": _reported("current_assets", 80_000.0),
                "current_liabilities": _reported("current_liabilities", 20_000.0),
            },
        )
        assert result.status is FinancialValueStatus.CALCULATED
        assert result.value == 4.0
        assert result.formula_id == FORMULA_CURRENT_RATIO

    def test_current_ratio_missing_assets_unavailable(self) -> None:
        result = derive(
            FORMULA_CURRENT_RATIO,
            {
                "current_assets": _reported("current_assets", None),
                "current_liabilities": _reported("current_liabilities", 20_000.0),
            },
        )
        assert result.status is FinancialValueStatus.UNAVAILABLE
        assert result.value is None
        assert result.unavailable_reason == "missing_input"

    def test_current_ratio_zero_liabilities_unavailable(self) -> None:
        result = derive(
            FORMULA_CURRENT_RATIO,
            {
                "current_assets": _reported("current_assets", 80_000.0),
                "current_liabilities": _reported("current_liabilities", 0.0),
            },
        )
        assert result.status is FinancialValueStatus.UNAVAILABLE
        assert result.value is None
        assert result.unavailable_reason == "division_by_zero"

    def test_current_ratio_currency_mismatch_unavailable(self) -> None:
        result = derive(
            FORMULA_CURRENT_RATIO,
            {
                "current_assets": _reported("current_assets", 80_000.0),
                "current_liabilities": _reported(
                    "current_liabilities", 20_000.0, currency=CurrencyCode.USD
                ),
            },
        )
        assert result.status is FinancialValueStatus.UNAVAILABLE
        assert result.unavailable_reason == "currency_mismatch"

    def test_quick_ratio_requires_inventory(self) -> None:
        missing = derive(
            FORMULA_QUICK_RATIO,
            {
                "current_assets": _reported("current_assets", 80_000.0),
                "inventory": _reported("inventory", None),
                "current_liabilities": _reported("current_liabilities", 20_000.0),
            },
        )
        assert missing.status is FinancialValueStatus.UNAVAILABLE
        ok = derive(
            FORMULA_QUICK_RATIO,
            {
                "current_assets": _reported("current_assets", 80_000.0),
                "inventory": _reported("inventory", 10_000.0),
                "current_liabilities": _reported("current_liabilities", 20_000.0),
            },
        )
        assert ok.status is FinancialValueStatus.CALCULATED
        assert ok.value == 3.5

    def test_cash_ratio_requires_cash_and_sti(self) -> None:
        missing_sti = derive(
            FORMULA_CASH_RATIO,
            {
                "cash": _reported("cash", 15_000.0),
                "short_term_investments": _reported("short_term_investments", None),
                "current_liabilities": _reported("current_liabilities", 20_000.0),
            },
        )
        assert missing_sti.status is FinancialValueStatus.UNAVAILABLE
        ok = derive(
            FORMULA_CASH_RATIO,
            {
                "cash": _reported("cash", 15_000.0),
                "short_term_investments": _reported("short_term_investments", 5_000.0),
                "current_liabilities": _reported("current_liabilities", 20_000.0),
            },
        )
        assert ok.status is FinancialValueStatus.CALCULATED
        assert ok.value == 1.0

    def test_working_capital_turnover_uses_calculated_wc(self) -> None:
        wc = derive(
            FORMULA_WORKING_CAPITAL,
            {
                "current_assets": _reported("current_assets", 80_000.0),
                "current_liabilities": _reported("current_liabilities", 20_000.0),
            },
        )
        result = derive(
            FORMULA_WORKING_CAPITAL_TURNOVER,
            {
                "revenue": _reported("revenue", _TCS_REVENUE),
                "working_capital": DerivationInput(
                    field_id="working_capital",
                    value=wc.value,
                    status=wc.status,
                    period_type=PeriodType.ANNUAL,
                    period_end=_FY24,
                    unit_scale=UnitScale.ACTUAL,
                    currency=CurrencyCode.INR,
                    accounting_basis="consolidated",
                    source="u4-shaped-fixture",
                ),
            },
        )
        assert result.status is FinancialValueStatus.CALCULATED
        assert result.value == _TCS_REVENUE / 60_000.0
        assert result.formula_id == FORMULA_WORKING_CAPITAL_TURNOVER


class TestF25AverageAndDebtFormulas:
    def test_average_balance_requires_both_periods(self) -> None:
        missing = derive(
            FORMULA_AVERAGE_BALANCE,
            {
                "beginning_balance": _reported("beginning_balance", None),
                "ending_balance": _reported("ending_balance", 100_000.0),
            },
        )
        assert missing.status is FinancialValueStatus.UNAVAILABLE
        ok = derive(
            FORMULA_AVERAGE_BALANCE,
            {
                "beginning_balance": _reported(
                    "beginning_balance", 90_000.0, period_end=_FY23
                ),
                "ending_balance": _reported("ending_balance", 110_000.0),
            },
        )
        assert ok.status is FinancialValueStatus.CALCULATED
        assert ok.value == 100_000.0

    def test_net_debt_requires_cash(self) -> None:
        from financial import FORMULA_TOTAL_DEBT

        debt = derive(
            FORMULA_TOTAL_DEBT,
            {
                "short_term_debt": _reported("short_term_debt", 10_000.0),
                "long_term_debt": _reported("long_term_debt", 40_000.0),
            },
        )
        missing = derive(
            FORMULA_NET_DEBT,
            {
                "total_debt": DerivationInput(
                    field_id="total_debt",
                    value=debt.value,
                    status=debt.status,
                    period_type=PeriodType.ANNUAL,
                    period_end=_FY24,
                    unit_scale=UnitScale.ACTUAL,
                    currency=CurrencyCode.INR,
                    accounting_basis="consolidated",
                    source="u4-shaped-fixture",
                ),
                "cash": _reported("cash", None),
            },
        )
        assert missing.status is FinancialValueStatus.UNAVAILABLE

    def test_fcf_margin_uses_fcf_input(self) -> None:
        fcf = derive(
            FORMULA_FCF,
            {
                "operating_cash_flow": _reported("operating_cash_flow", 40_000.0),
                "capex": _reported("capex", -8_000.0),
            },
        )
        margin = derive(
            FORMULA_FCF_MARGIN,
            {
                "fcf": DerivationInput(
                    field_id="fcf",
                    value=fcf.value,
                    status=fcf.status,
                    period_type=PeriodType.ANNUAL,
                    period_end=_FY24,
                    unit_scale=UnitScale.ACTUAL,
                    currency=CurrencyCode.INR,
                    accounting_basis="consolidated",
                    source="u4-shaped-fixture",
                ),
                "revenue": _reported("revenue", _TCS_REVENUE),
            },
        )
        assert margin.status is FinancialValueStatus.CALCULATED
        assert margin.value == 32_000.0 / _TCS_REVENUE
