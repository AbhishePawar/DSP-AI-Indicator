"""Registered derivation formulas.

Each formula_id is explicit. Missing preferred inputs must not silently
switch to an alternate formula — callers choose the formula_id.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from financial.derivation.models import PeriodRule

__all__ = [
    "FORMULA_ASSET_TURNOVER",
    "FORMULA_AVERAGE_BALANCE",
    "FORMULA_AVERAGE_EQUITY",
    "FORMULA_CASH_CONVERSION_CYCLE",
    "FORMULA_CASH_CONVERSION_RATIO",
    "FORMULA_CASH_RATIO",
    "FORMULA_CURRENT_RATIO",
    "FORMULA_DAYS_INVENTORY_OUTSTANDING",
    "FORMULA_DAYS_PAYABLES_OUTSTANDING",
    "FORMULA_DAYS_SALES_OUTSTANDING",
    "FORMULA_DEBT_COVERAGE",
    "FORMULA_DEBT_TO_ASSETS",
    "FORMULA_DEBT_TO_EQUITY",
    "FORMULA_DIVIDEND_COVERAGE",
    "FORMULA_EPS_GROWTH",
    "FORMULA_FCF",
    "FORMULA_FCF_MARGIN",
    "FORMULA_FIXED_ASSET_TURNOVER",
    "FORMULA_GROSS_MARGIN",
    "FORMULA_GROSS_MARGIN_FROM_COGS",
    "FORMULA_INVENTORY_TURNOVER",
    "FORMULA_INVESTED_CAPITAL",
    "FORMULA_NET_DEBT",
    "FORMULA_NET_DEBT_TO_EBITDA",
    "FORMULA_NET_MARGIN",
    "FORMULA_NOPAT",
    "FORMULA_OPERATING_MARGIN",
    "FORMULA_PAYABLE_TURNOVER",
    "FORMULA_QUICK_RATIO",
    "FORMULA_RECEIVABLE_TURNOVER",
    "FORMULA_REVENUE_GROWTH",
    "FORMULA_ROA",
    "FORMULA_ROCE",
    "FORMULA_ROE",
    "FORMULA_ROIC",
    "FORMULA_TOTAL_DEBT",
    "FORMULA_WORKING_CAPITAL",
    "FORMULA_WORKING_CAPITAL_RATIO",
    "FORMULA_WORKING_CAPITAL_TURNOVER",
    "FormulaSpec",
    "get_formula",
]

FORMULA_AVERAGE_BALANCE = "average_balance"
FORMULA_AVERAGE_EQUITY = "average_equity"
FORMULA_ROE = "roe"
FORMULA_ROCE = "roce"
FORMULA_GROSS_MARGIN = "gross_margin"
FORMULA_GROSS_MARGIN_FROM_COGS = "gross_margin_from_cogs"
FORMULA_OPERATING_MARGIN = "operating_margin"
FORMULA_NET_MARGIN = "net_margin"
FORMULA_TOTAL_DEBT = "total_debt"
FORMULA_DEBT_TO_EQUITY = "debt_to_equity"
FORMULA_WORKING_CAPITAL = "working_capital"
FORMULA_CURRENT_RATIO = "current_ratio"
FORMULA_WORKING_CAPITAL_RATIO = "working_capital_ratio"
FORMULA_QUICK_RATIO = "quick_ratio"
FORMULA_CASH_RATIO = "cash_ratio"
FORMULA_WORKING_CAPITAL_TURNOVER = "working_capital_turnover"
FORMULA_FCF = "fcf"
FORMULA_ROA = "roa"
FORMULA_NOPAT = "nopat"
FORMULA_INVESTED_CAPITAL = "invested_capital"
FORMULA_ROIC = "roic"
FORMULA_DEBT_TO_ASSETS = "debt_to_assets"
FORMULA_NET_DEBT = "net_debt"
FORMULA_NET_DEBT_TO_EBITDA = "net_debt_to_ebitda"
FORMULA_DEBT_COVERAGE = "debt_coverage"
FORMULA_ASSET_TURNOVER = "asset_turnover"
FORMULA_INVENTORY_TURNOVER = "inventory_turnover"
FORMULA_RECEIVABLE_TURNOVER = "receivable_turnover"
FORMULA_PAYABLE_TURNOVER = "payable_turnover"
FORMULA_FIXED_ASSET_TURNOVER = "fixed_asset_turnover"
FORMULA_DAYS_SALES_OUTSTANDING = "days_sales_outstanding"
FORMULA_DAYS_INVENTORY_OUTSTANDING = "days_inventory_outstanding"
FORMULA_DAYS_PAYABLES_OUTSTANDING = "days_payables_outstanding"
FORMULA_CASH_CONVERSION_CYCLE = "cash_conversion_cycle"
FORMULA_FCF_MARGIN = "fcf_margin"
FORMULA_CASH_CONVERSION_RATIO = "cash_conversion_ratio"
FORMULA_DIVIDEND_COVERAGE = "dividend_coverage"
FORMULA_REVENUE_GROWTH = "revenue_growth"
FORMULA_EPS_GROWTH = "eps_growth"


def _finite_div(numer: float, denom: float) -> float | None:
    if denom == 0:
        return None
    result = numer / denom
    if not math.isfinite(result):
        return None
    return result


def _finite(value: float) -> float | None:
    if not math.isfinite(value):
        return None
    return value


@dataclass(frozen=True, slots=True)
class FormulaSpec:
    formula_id: str
    formula: str
    required_inputs: tuple[str, ...]
    period_rule: PeriodRule
    compute: Callable[[Mapping[str, float]], float | None]
    output_kind: str = "amount"


def _average_balance(values: Mapping[str, float]) -> float | None:
    return _finite(
        (values["beginning_balance"] + values["ending_balance"]) / 2.0
    )


def _average_equity(values: Mapping[str, float]) -> float | None:
    return _finite(
        (values["beginning_equity"] + values["ending_equity"]) / 2.0
    )


def _roe(values: Mapping[str, float]) -> float | None:
    average_equity = _average_equity(values)
    if average_equity is None:
        return None
    return _finite_div(values["net_income"], average_equity)


def _roce(values: Mapping[str, float]) -> float | None:
    capital_employed = values["total_assets"] - values["current_liabilities"]
    return _finite_div(values["ebit"], capital_employed)


def _gross_margin(values: Mapping[str, float]) -> float | None:
    return _finite_div(values["gross_profit"], values["revenue"])


def _gross_margin_from_cogs(values: Mapping[str, float]) -> float | None:
    return _finite_div(values["revenue"] - values["cogs"], values["revenue"])


def _operating_margin(values: Mapping[str, float]) -> float | None:
    return _finite_div(values["ebit"], values["revenue"])


def _net_margin(values: Mapping[str, float]) -> float | None:
    return _finite_div(values["net_income"], values["revenue"])


def _total_debt(values: Mapping[str, float]) -> float | None:
    return _finite(values["short_term_debt"] + values["long_term_debt"])


def _debt_to_equity(values: Mapping[str, float]) -> float | None:
    return _finite_div(values["total_debt"], values["equity"])


def _working_capital(values: Mapping[str, float]) -> float | None:
    return _finite(values["current_assets"] - values["current_liabilities"])


def _current_ratio(values: Mapping[str, float]) -> float | None:
    return _finite_div(values["current_assets"], values["current_liabilities"])


def _quick_ratio(values: Mapping[str, float]) -> float | None:
    return _finite_div(
        values["current_assets"] - values["inventory"],
        values["current_liabilities"],
    )


def _cash_ratio(values: Mapping[str, float]) -> float | None:
    return _finite_div(
        values["cash"] + values["short_term_investments"],
        values["current_liabilities"],
    )


def _working_capital_turnover(values: Mapping[str, float]) -> float | None:
    return _finite_div(values["revenue"], values["working_capital"])


def _roa(values: Mapping[str, float]) -> float | None:
    return _finite_div(values["net_income"], values["total_assets"])


def _nopat(values: Mapping[str, float]) -> float | None:
    tax_rate = _finite_div(values["tax"], values["pretax_income"])
    if tax_rate is None:
        return None
    effective = max(0.0, min(0.6, tax_rate))
    return _finite(values["ebit"] * (1.0 - effective))


def _invested_capital(values: Mapping[str, float]) -> float | None:
    return _finite(values["equity"] + values["total_debt"] - values["cash"])


def _roic(values: Mapping[str, float]) -> float | None:
    return _finite_div(values["nopat"], values["invested_capital"])


def _debt_to_assets(values: Mapping[str, float]) -> float | None:
    return _finite_div(values["total_debt"], values["total_assets"])


def _net_debt(values: Mapping[str, float]) -> float | None:
    return _finite(values["total_debt"] - values["cash"])


def _net_debt_to_ebitda(values: Mapping[str, float]) -> float | None:
    return _finite_div(values["net_debt"], values["ebitda"])


def _debt_coverage(values: Mapping[str, float]) -> float | None:
    return _finite_div(values["operating_cash_flow"], values["total_debt"])


def _asset_turnover(values: Mapping[str, float]) -> float | None:
    return _finite_div(values["revenue"], values["average_total_assets"])


def _inventory_turnover(values: Mapping[str, float]) -> float | None:
    return _finite_div(abs(values["cogs"]), values["average_inventory"])


def _receivable_turnover(values: Mapping[str, float]) -> float | None:
    return _finite_div(values["revenue"], values["average_receivables"])


def _payable_turnover(values: Mapping[str, float]) -> float | None:
    return _finite_div(abs(values["cogs"]), values["average_payables"])


def _fixed_asset_turnover(values: Mapping[str, float]) -> float | None:
    return _finite_div(values["revenue"], values["ppe"])


def _days_sales_outstanding(values: Mapping[str, float]) -> float | None:
    return _finite_div(365.0, values["receivable_turnover"])


def _days_inventory_outstanding(values: Mapping[str, float]) -> float | None:
    return _finite_div(365.0, values["inventory_turnover"])


def _days_payables_outstanding(values: Mapping[str, float]) -> float | None:
    return _finite_div(365.0, values["payable_turnover"])


def _cash_conversion_cycle(values: Mapping[str, float]) -> float | None:
    return _finite(
        values["days_sales_outstanding"]
        + values["days_inventory_outstanding"]
        - values["days_payables_outstanding"]
    )


def _fcf_margin(values: Mapping[str, float]) -> float | None:
    return _finite_div(values["fcf"], values["revenue"])


def _cash_conversion_ratio(values: Mapping[str, float]) -> float | None:
    return _finite_div(values["fcf"], values["operating_cash_flow"])


def _dividend_coverage(values: Mapping[str, float]) -> float | None:
    return _finite_div(values["fcf"], abs(values["dividends_paid"]))


def _fcf(values: Mapping[str, float]) -> float | None:
    return _finite(values["operating_cash_flow"] - abs(values["capex"]))


def _revenue_growth(values: Mapping[str, float]) -> float | None:
    return _finite_div(
        values["current_revenue"] - values["prior_revenue"],
        values["prior_revenue"],
    )


def _eps_growth(values: Mapping[str, float]) -> float | None:
    return _finite_div(
        values["current_eps"] - values["prior_eps"],
        values["prior_eps"],
    )


_REGISTRY: dict[str, FormulaSpec] = {
    FORMULA_AVERAGE_BALANCE: FormulaSpec(
        formula_id=FORMULA_AVERAGE_BALANCE,
        formula="(beginning_balance + ending_balance) / 2",
        required_inputs=("beginning_balance", "ending_balance"),
        period_rule=PeriodRule.SAME_PERIOD_TYPE,
        compute=_average_balance,
        output_kind="amount",
    ),
    FORMULA_AVERAGE_EQUITY: FormulaSpec(
        formula_id=FORMULA_AVERAGE_EQUITY,
        formula="(beginning_equity + ending_equity) / 2",
        required_inputs=("beginning_equity", "ending_equity"),
        period_rule=PeriodRule.SAME_PERIOD_TYPE,
        compute=_average_equity,
        output_kind="amount",
    ),
    FORMULA_ROE: FormulaSpec(
        formula_id=FORMULA_ROE,
        formula="net_income / ((beginning_equity + ending_equity) / 2)",
        required_inputs=("net_income", "beginning_equity", "ending_equity"),
        period_rule=PeriodRule.SAME_PERIOD_TYPE,
        compute=_roe,
        output_kind="ratio",
    ),
    FORMULA_ROCE: FormulaSpec(
        formula_id=FORMULA_ROCE,
        formula="ebit / (total_assets - current_liabilities)",
        required_inputs=("ebit", "total_assets", "current_liabilities"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_roce,
        output_kind="ratio",
    ),
    FORMULA_GROSS_MARGIN: FormulaSpec(
        formula_id=FORMULA_GROSS_MARGIN,
        formula="gross_profit / revenue",
        required_inputs=("gross_profit", "revenue"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_gross_margin,
        output_kind="ratio",
    ),
    FORMULA_GROSS_MARGIN_FROM_COGS: FormulaSpec(
        formula_id=FORMULA_GROSS_MARGIN_FROM_COGS,
        formula="(revenue - cogs) / revenue",
        required_inputs=("revenue", "cogs"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_gross_margin_from_cogs,
        output_kind="ratio",
    ),
    FORMULA_OPERATING_MARGIN: FormulaSpec(
        formula_id=FORMULA_OPERATING_MARGIN,
        formula="ebit / revenue",
        required_inputs=("ebit", "revenue"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_operating_margin,
        output_kind="ratio",
    ),
    FORMULA_NET_MARGIN: FormulaSpec(
        formula_id=FORMULA_NET_MARGIN,
        formula="net_income / revenue",
        required_inputs=("net_income", "revenue"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_net_margin,
        output_kind="ratio",
    ),
    FORMULA_TOTAL_DEBT: FormulaSpec(
        formula_id=FORMULA_TOTAL_DEBT,
        formula="short_term_debt + long_term_debt",
        required_inputs=("short_term_debt", "long_term_debt"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_total_debt,
        output_kind="amount",
    ),
    FORMULA_DEBT_TO_EQUITY: FormulaSpec(
        formula_id=FORMULA_DEBT_TO_EQUITY,
        formula="total_debt / equity",
        required_inputs=("total_debt", "equity"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_debt_to_equity,
        output_kind="ratio",
    ),
    FORMULA_WORKING_CAPITAL: FormulaSpec(
        formula_id=FORMULA_WORKING_CAPITAL,
        formula="current_assets - current_liabilities",
        required_inputs=("current_assets", "current_liabilities"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_working_capital,
        output_kind="amount",
    ),
    FORMULA_CURRENT_RATIO: FormulaSpec(
        formula_id=FORMULA_CURRENT_RATIO,
        formula="current_assets / current_liabilities",
        required_inputs=("current_assets", "current_liabilities"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_current_ratio,
        output_kind="ratio",
    ),
    FORMULA_WORKING_CAPITAL_RATIO: FormulaSpec(
        formula_id=FORMULA_WORKING_CAPITAL_RATIO,
        formula="current_assets / current_liabilities",
        required_inputs=("current_assets", "current_liabilities"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_current_ratio,
        output_kind="ratio",
    ),
    FORMULA_QUICK_RATIO: FormulaSpec(
        formula_id=FORMULA_QUICK_RATIO,
        formula="(current_assets - inventory) / current_liabilities",
        required_inputs=("current_assets", "inventory", "current_liabilities"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_quick_ratio,
        output_kind="ratio",
    ),
    FORMULA_CASH_RATIO: FormulaSpec(
        formula_id=FORMULA_CASH_RATIO,
        formula="(cash + short_term_investments) / current_liabilities",
        required_inputs=("cash", "short_term_investments", "current_liabilities"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_cash_ratio,
        output_kind="ratio",
    ),
    FORMULA_WORKING_CAPITAL_TURNOVER: FormulaSpec(
        formula_id=FORMULA_WORKING_CAPITAL_TURNOVER,
        formula="revenue / working_capital",
        required_inputs=("revenue", "working_capital"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_working_capital_turnover,
        output_kind="ratio",
    ),
    FORMULA_ROA: FormulaSpec(
        formula_id=FORMULA_ROA,
        formula="net_income / total_assets",
        required_inputs=("net_income", "total_assets"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_roa,
        output_kind="ratio",
    ),
    FORMULA_NOPAT: FormulaSpec(
        formula_id=FORMULA_NOPAT,
        formula="ebit * (1 - clamp(tax / pretax_income, 0, 0.6))",
        required_inputs=("ebit", "tax", "pretax_income"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_nopat,
        output_kind="amount",
    ),
    FORMULA_INVESTED_CAPITAL: FormulaSpec(
        formula_id=FORMULA_INVESTED_CAPITAL,
        formula="equity + total_debt - cash",
        required_inputs=("equity", "total_debt", "cash"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_invested_capital,
        output_kind="amount",
    ),
    FORMULA_ROIC: FormulaSpec(
        formula_id=FORMULA_ROIC,
        formula="nopat / invested_capital",
        required_inputs=("nopat", "invested_capital"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_roic,
        output_kind="ratio",
    ),
    FORMULA_DEBT_TO_ASSETS: FormulaSpec(
        formula_id=FORMULA_DEBT_TO_ASSETS,
        formula="total_debt / total_assets",
        required_inputs=("total_debt", "total_assets"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_debt_to_assets,
        output_kind="ratio",
    ),
    FORMULA_NET_DEBT: FormulaSpec(
        formula_id=FORMULA_NET_DEBT,
        formula="total_debt - cash",
        required_inputs=("total_debt", "cash"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_net_debt,
        output_kind="amount",
    ),
    FORMULA_NET_DEBT_TO_EBITDA: FormulaSpec(
        formula_id=FORMULA_NET_DEBT_TO_EBITDA,
        formula="net_debt / ebitda",
        required_inputs=("net_debt", "ebitda"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_net_debt_to_ebitda,
        output_kind="ratio",
    ),
    FORMULA_DEBT_COVERAGE: FormulaSpec(
        formula_id=FORMULA_DEBT_COVERAGE,
        formula="operating_cash_flow / total_debt",
        required_inputs=("operating_cash_flow", "total_debt"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_debt_coverage,
        output_kind="ratio",
    ),
    FORMULA_ASSET_TURNOVER: FormulaSpec(
        formula_id=FORMULA_ASSET_TURNOVER,
        formula="revenue / average_total_assets",
        required_inputs=("revenue", "average_total_assets"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_asset_turnover,
        output_kind="ratio",
    ),
    FORMULA_INVENTORY_TURNOVER: FormulaSpec(
        formula_id=FORMULA_INVENTORY_TURNOVER,
        formula="|cogs| / average_inventory",
        required_inputs=("cogs", "average_inventory"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_inventory_turnover,
        output_kind="ratio",
    ),
    FORMULA_RECEIVABLE_TURNOVER: FormulaSpec(
        formula_id=FORMULA_RECEIVABLE_TURNOVER,
        formula="revenue / average_receivables",
        required_inputs=("revenue", "average_receivables"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_receivable_turnover,
        output_kind="ratio",
    ),
    FORMULA_PAYABLE_TURNOVER: FormulaSpec(
        formula_id=FORMULA_PAYABLE_TURNOVER,
        formula="|cogs| / average_payables",
        required_inputs=("cogs", "average_payables"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_payable_turnover,
        output_kind="ratio",
    ),
    FORMULA_FIXED_ASSET_TURNOVER: FormulaSpec(
        formula_id=FORMULA_FIXED_ASSET_TURNOVER,
        formula="revenue / ppe",
        required_inputs=("revenue", "ppe"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_fixed_asset_turnover,
        output_kind="ratio",
    ),
    FORMULA_DAYS_SALES_OUTSTANDING: FormulaSpec(
        formula_id=FORMULA_DAYS_SALES_OUTSTANDING,
        formula="365 / receivable_turnover",
        required_inputs=("receivable_turnover",),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_days_sales_outstanding,
        output_kind="ratio",
    ),
    FORMULA_DAYS_INVENTORY_OUTSTANDING: FormulaSpec(
        formula_id=FORMULA_DAYS_INVENTORY_OUTSTANDING,
        formula="365 / inventory_turnover",
        required_inputs=("inventory_turnover",),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_days_inventory_outstanding,
        output_kind="ratio",
    ),
    FORMULA_DAYS_PAYABLES_OUTSTANDING: FormulaSpec(
        formula_id=FORMULA_DAYS_PAYABLES_OUTSTANDING,
        formula="365 / payable_turnover",
        required_inputs=("payable_turnover",),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_days_payables_outstanding,
        output_kind="ratio",
    ),
    FORMULA_CASH_CONVERSION_CYCLE: FormulaSpec(
        formula_id=FORMULA_CASH_CONVERSION_CYCLE,
        formula="days_sales_outstanding + days_inventory_outstanding - days_payables_outstanding",
        required_inputs=(
            "days_sales_outstanding",
            "days_inventory_outstanding",
            "days_payables_outstanding",
        ),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_cash_conversion_cycle,
        output_kind="ratio",
    ),
    FORMULA_FCF_MARGIN: FormulaSpec(
        formula_id=FORMULA_FCF_MARGIN,
        formula="fcf / revenue",
        required_inputs=("fcf", "revenue"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_fcf_margin,
        output_kind="ratio",
    ),
    FORMULA_CASH_CONVERSION_RATIO: FormulaSpec(
        formula_id=FORMULA_CASH_CONVERSION_RATIO,
        formula="fcf / operating_cash_flow",
        required_inputs=("fcf", "operating_cash_flow"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_cash_conversion_ratio,
        output_kind="ratio",
    ),
    FORMULA_DIVIDEND_COVERAGE: FormulaSpec(
        formula_id=FORMULA_DIVIDEND_COVERAGE,
        formula="fcf / |dividends_paid|",
        required_inputs=("fcf", "dividends_paid"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_dividend_coverage,
        output_kind="ratio",
    ),
    FORMULA_FCF: FormulaSpec(
        formula_id=FORMULA_FCF,
        formula="operating_cash_flow - abs(capex)",
        required_inputs=("operating_cash_flow", "capex"),
        period_rule=PeriodRule.SAME_PERIOD,
        compute=_fcf,
        output_kind="amount",
    ),
    FORMULA_REVENUE_GROWTH: FormulaSpec(
        formula_id=FORMULA_REVENUE_GROWTH,
        formula="(current_revenue - prior_revenue) / prior_revenue",
        required_inputs=("current_revenue", "prior_revenue"),
        period_rule=PeriodRule.GROWTH,
        compute=_revenue_growth,
        output_kind="ratio",
    ),
    FORMULA_EPS_GROWTH: FormulaSpec(
        formula_id=FORMULA_EPS_GROWTH,
        formula="(current_eps - prior_eps) / prior_eps",
        required_inputs=("current_eps", "prior_eps"),
        period_rule=PeriodRule.GROWTH,
        compute=_eps_growth,
        output_kind="ratio",
    ),
}


def get_formula(formula_id: str) -> FormulaSpec | None:
    return _REGISTRY.get(formula_id)
