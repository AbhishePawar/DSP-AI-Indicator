"""WACC calculation — CAPM cost of equity + after-tax cost of debt."""

from __future__ import annotations

from valuation.dcf_intelligence.assumptions import (
    CapmInputs,
    CapitalStructure,
    CostOfDebtInputs,
)
from valuation.dcf_intelligence.explain import ExplainedValue
from valuation.exceptions import ValuationError

__all__ = ["WaccResult", "compute_wacc"]


class WaccResult:
    """Structured WACC outputs with explainability."""

    __slots__ = (
        "cost_of_equity",
        "cost_of_debt_pre_tax",
        "cost_of_debt_after_tax",
        "equity_weight",
        "debt_weight",
        "wacc",
        "explained",
    )

    def __init__(
        self,
        *,
        cost_of_equity: ExplainedValue,
        cost_of_debt_pre_tax: ExplainedValue,
        cost_of_debt_after_tax: ExplainedValue,
        equity_weight: ExplainedValue,
        debt_weight: ExplainedValue,
        wacc: ExplainedValue,
    ) -> None:
        self.cost_of_equity = cost_of_equity
        self.cost_of_debt_pre_tax = cost_of_debt_pre_tax
        self.cost_of_debt_after_tax = cost_of_debt_after_tax
        self.equity_weight = equity_weight
        self.debt_weight = debt_weight
        self.wacc = wacc
        self.explained = (
            cost_of_equity,
            cost_of_debt_pre_tax,
            cost_of_debt_after_tax,
            equity_weight,
            debt_weight,
            wacc,
        )


def _weights(structure: CapitalStructure) -> tuple[float, float]:
    if (
        structure.equity_weight is not None
        and structure.debt_weight is not None
    ):
        return float(structure.equity_weight), float(structure.debt_weight)
    eq = float(structure.equity_market_value)  # type: ignore[arg-type]
    deb = float(structure.debt_market_value)  # type: ignore[arg-type]
    total = eq + deb
    return eq / total, deb / total


def compute_wacc(
    *,
    capm: CapmInputs,
    debt: CostOfDebtInputs,
    structure: CapitalStructure,
    tax_rate: float,
) -> WaccResult:
    """Compute WACC with full explainability.

    Raises:
        ValuationError: If tax rate invalid or WACC non-positive.
    """
    if tax_rate < 0 or tax_rate >= 1:
        raise ValuationError(f"tax_rate out of range for WACC: {tax_rate}")

    re = capm.risk_free_rate + capm.beta * capm.equity_risk_premium
    cost_of_equity = ExplainedValue(
        name="cost_of_equity",
        value=re,
        formula="re = rf + β × ERP",
        inputs={
            "risk_free_rate": capm.risk_free_rate,
            "beta": capm.beta,
            "equity_risk_premium": capm.equity_risk_premium,
        },
        intermediates={"rf_plus_beta_erp": re},
        confidence="high",
    )

    rd = debt.pre_tax_cost_of_debt
    cost_of_debt_pre_tax = ExplainedValue(
        name="cost_of_debt_pre_tax",
        value=rd,
        formula="rd = pre_tax_cost_of_debt",
        inputs={"pre_tax_cost_of_debt": rd},
        intermediates={},
        confidence="high",
    )

    rd_at = rd * (1.0 - tax_rate)
    cost_of_debt_after_tax = ExplainedValue(
        name="cost_of_debt_after_tax",
        value=rd_at,
        formula="rd_at = rd × (1 − t)",
        inputs={"pre_tax_cost_of_debt": rd, "tax_rate": tax_rate},
        intermediates={"one_minus_tax": 1.0 - tax_rate},
        confidence="high",
    )

    we, wd = _weights(structure)
    equity_weight = ExplainedValue(
        name="equity_weight",
        value=we,
        formula="we = E / (E + D) or explicit weight",
        inputs={
            "equity_market_value": structure.equity_market_value,
            "debt_market_value": structure.debt_market_value,
            "equity_weight": structure.equity_weight,
            "debt_weight": structure.debt_weight,
        },
        intermediates={},
        confidence="high",
    )
    debt_weight = ExplainedValue(
        name="debt_weight",
        value=wd,
        formula="wd = D / (E + D) or explicit weight",
        inputs={
            "equity_market_value": structure.equity_market_value,
            "debt_market_value": structure.debt_market_value,
            "equity_weight": structure.equity_weight,
            "debt_weight": structure.debt_weight,
        },
        intermediates={},
        confidence="high",
    )

    wacc = we * re + wd * rd_at
    if wacc <= 0:
        raise ValuationError(f"computed WACC must be positive, got {wacc}")

    wacc_explained = ExplainedValue(
        name="wacc",
        value=wacc,
        formula="WACC = we×re + wd×rd×(1−t)",
        inputs={
            "equity_weight": we,
            "cost_of_equity": re,
            "debt_weight": wd,
            "cost_of_debt_after_tax": rd_at,
        },
        intermediates={"we_re": we * re, "wd_rd_at": wd * rd_at},
        confidence="high",
    )

    return WaccResult(
        cost_of_equity=cost_of_equity,
        cost_of_debt_pre_tax=cost_of_debt_pre_tax,
        cost_of_debt_after_tax=cost_of_debt_after_tax,
        equity_weight=equity_weight,
        debt_weight=debt_weight,
        wacc=wacc_explained,
    )
