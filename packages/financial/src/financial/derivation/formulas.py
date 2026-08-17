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
    "FORMULA_AVERAGE_EQUITY",
    "FORMULA_DEBT_TO_EQUITY",
    "FORMULA_EPS_GROWTH",
    "FORMULA_FCF",
    "FORMULA_GROSS_MARGIN",
    "FORMULA_GROSS_MARGIN_FROM_COGS",
    "FORMULA_NET_MARGIN",
    "FORMULA_OPERATING_MARGIN",
    "FORMULA_REVENUE_GROWTH",
    "FORMULA_ROCE",
    "FORMULA_ROE",
    "FORMULA_TOTAL_DEBT",
    "FORMULA_WORKING_CAPITAL",
    "FormulaSpec",
    "get_formula",
]

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
FORMULA_FCF = "fcf"
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
