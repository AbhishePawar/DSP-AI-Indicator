"""Deterministic WACC from researched components. Reuses compute_wacc.

AI does not calculate WACC. DSP calls the existing DCF-intelligence WACC
engine. A calculated WACC is a derived value, then proposed as a DCF
assumption. It is never an observed fact.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from valuation.dcf_intelligence.assumptions import (
    CapmInputs,
    CapitalStructure,
    CostOfDebtInputs,
)
from valuation.dcf_intelligence.wacc import compute_wacc
from valuation.exceptions import ValuationError

__all__ = [
    "DSP_WACC_ENGINE",
    "DSP_WACC_VERSION",
    "WACC_RECONSTRUCTION_TOLERANCE",
    "DspWaccCalculation",
    "calculate_dsp_wacc",
    "compare_external_wacc",
]

DSP_WACC_ENGINE = "valuation.dcf_intelligence.wacc.compute_wacc"
DSP_WACC_VERSION = "dsp_wacc.v1"
WACC_RECONSTRUCTION_TOLERANCE = Decimal("0.0001")
_COST_EQUITY_FORMULA = "re = rf + β × ERP"
_WACC_FORMULA = "WACC = we×re + wd×rd×(1−t)"
_ALL_EQUITY_FORMULA = "WACC = re (all-equity; debt weight is 0)"


@dataclass(frozen=True, slots=True)
class DspWaccCalculation:
    status: str
    cost_of_equity: Decimal | None
    pre_tax_cost_of_debt: Decimal | None
    after_tax_cost_of_debt: Decimal | None
    equity_weight: Decimal | None
    debt_weight: Decimal | None
    wacc: Decimal | None
    formula: str
    engine: str
    inputs: dict[str, Any]
    evidence_ids: tuple[str, ...]
    detail: str
    calculated_at: datetime | None = None
    calculation_version: str = DSP_WACC_VERSION

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "cost_of_equity": None if self.cost_of_equity is None else str(self.cost_of_equity),
            "pre_tax_cost_of_debt": None if self.pre_tax_cost_of_debt is None else str(self.pre_tax_cost_of_debt),
            "after_tax_cost_of_debt": None if self.after_tax_cost_of_debt is None else str(self.after_tax_cost_of_debt),
            "equity_weight": None if self.equity_weight is None else str(self.equity_weight),
            "debt_weight": None if self.debt_weight is None else str(self.debt_weight),
            "wacc": None if self.wacc is None else str(self.wacc),
            "formula": self.formula,
            "engine": self.engine,
            "inputs": dict(self.inputs),
            "evidence_ids": list(self.evidence_ids),
            "detail": self.detail,
            "data_class": "DERIVED_VALUE",
            "calculated_at": None if self.calculated_at is None else self.calculated_at.isoformat(),
            "calculation_version": self.calculation_version,
        }


def _dec(value: float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(round(value, 10)))


def _unknown(detail: str, *, evidence_ids: tuple[str, ...] = ()) -> DspWaccCalculation:
    return DspWaccCalculation(
        status="UNKNOWN",
        cost_of_equity=None,
        pre_tax_cost_of_debt=None,
        after_tax_cost_of_debt=None,
        equity_weight=None,
        debt_weight=None,
        wacc=None,
        formula=_WACC_FORMULA,
        engine=DSP_WACC_ENGINE,
        inputs={},
        evidence_ids=evidence_ids,
        detail=detail,
        calculated_at=datetime.now(tz=UTC),
        calculation_version=DSP_WACC_VERSION,
    )


def compare_external_wacc(
    dsp_wacc: Decimal | None,
    external_wacc: Decimal | None,
) -> str:
    """Independently reconstructed WACC vs an external quote. Never averaged."""
    if dsp_wacc is None or external_wacc is None:
        return "UNKNOWN"
    if abs(dsp_wacc - external_wacc) <= WACC_RECONSTRUCTION_TOLERANCE:
        return "MATCH"
    return "REVIEW_REQUIRED"


def calculate_dsp_wacc(
    *,
    risk_free_rate: Decimal | None,
    beta: Decimal | None,
    equity_risk_premium: Decimal | None,
    equity_market_value: Decimal | None,
    debt_market_value: Decimal | None,
    pre_tax_cost_of_debt: Decimal | None,
    tax_rate: Decimal | None,
    finance_costs: Decimal | None = None,
    tax_rate_kind: str | None = None,
    evidence_ids: tuple[str, ...] = (),
) -> DspWaccCalculation:
    """Compute cost of equity / WACC. Missing components stay UNKNOWN."""
    inputs = {
        "risk_free_rate": None if risk_free_rate is None else str(risk_free_rate),
        "beta": None if beta is None else str(beta),
        "equity_risk_premium": None if equity_risk_premium is None else str(equity_risk_premium),
        "equity_market_value": None if equity_market_value is None else str(equity_market_value),
        "debt_market_value": None if debt_market_value is None else str(debt_market_value),
        "pre_tax_cost_of_debt": None if pre_tax_cost_of_debt is None else str(pre_tax_cost_of_debt),
        "tax_rate": None if tax_rate is None else str(tax_rate),
        "tax_rate_kind": tax_rate_kind,
        "finance_costs": None if finance_costs is None else str(finance_costs),
        "formula_cost_of_equity": _COST_EQUITY_FORMULA,
    }
    now = datetime.now(tz=UTC)
    if risk_free_rate is None or beta is None or equity_risk_premium is None:
        return _unknown(
            "cost of equity requires evidenced risk-free rate, beta, and ERP",
            evidence_ids=evidence_ids,
        )
    rd = pre_tax_cost_of_debt
    if rd is None and finance_costs is not None and debt_market_value is not None and debt_market_value > 0:
        rd = finance_costs / debt_market_value
        inputs["pre_tax_cost_of_debt"] = str(rd)
        inputs["pre_tax_cost_of_debt_origin"] = "finance_costs / debt"
    debt = Decimal("0") if debt_market_value is None else debt_market_value
    if debt < 0:
        return _unknown("debt market value cannot be negative", evidence_ids=evidence_ids)
    try:
        capm = CapmInputs(
            risk_free_rate=float(risk_free_rate),
            beta=float(beta),
            equity_risk_premium=float(equity_risk_premium),
        )
    except (ValuationError, TypeError, ValueError) as exc:
        return _unknown(f"CAPM inputs invalid: {exc}", evidence_ids=evidence_ids)

    if debt == 0:
        try:
            result = compute_wacc(
                capm=capm,
                debt=CostOfDebtInputs(0.0),
                structure=CapitalStructure(equity_market_value=1.0, debt_market_value=0.0),
                tax_rate=0.0,
            )
        except ValuationError as exc:
            return _unknown(str(exc), evidence_ids=evidence_ids)
        re = _dec(result.cost_of_equity.value)
        return DspWaccCalculation(
            status="CALCULATED",
            cost_of_equity=re,
            pre_tax_cost_of_debt=Decimal("0"),
            after_tax_cost_of_debt=Decimal("0"),
            equity_weight=Decimal("1"),
            debt_weight=Decimal("0"),
            wacc=re,
            formula=_ALL_EQUITY_FORMULA,
            engine=DSP_WACC_ENGINE,
            inputs=inputs,
            evidence_ids=evidence_ids,
            detail="all-equity required return from CAPM; not an observed WACC quote",
            calculated_at=now,
            calculation_version=DSP_WACC_VERSION,
        )

    if equity_market_value is None or equity_market_value <= 0:
        return _unknown(
            "levered WACC requires verified equity market value",
            evidence_ids=evidence_ids,
        )
    if rd is None:
        return _unknown(
            "levered WACC requires pre-tax cost of debt (or finance_costs / debt)",
            evidence_ids=evidence_ids,
        )
    if tax_rate is None:
        return _unknown(
            "levered WACC requires an evidenced tax rate; statutory defaults are not used",
            evidence_ids=evidence_ids,
        )
    try:
        result = compute_wacc(
            capm=capm,
            debt=CostOfDebtInputs(float(rd)),
            structure=CapitalStructure(
                equity_market_value=float(equity_market_value),
                debt_market_value=float(debt),
            ),
            tax_rate=float(tax_rate),
        )
    except ValuationError as exc:
        return _unknown(str(exc), evidence_ids=evidence_ids)
    return DspWaccCalculation(
        status="CALCULATED",
        cost_of_equity=_dec(result.cost_of_equity.value),
        pre_tax_cost_of_debt=_dec(result.cost_of_debt_pre_tax.value),
        after_tax_cost_of_debt=_dec(result.cost_of_debt_after_tax.value),
        equity_weight=_dec(result.equity_weight.value),
        debt_weight=_dec(result.debt_weight.value),
        wacc=_dec(result.wacc.value),
        formula=_WACC_FORMULA,
        engine=DSP_WACC_ENGINE,
        inputs=inputs,
        evidence_ids=evidence_ids,
        detail="derived WACC from researched components; not an observed fact",
        calculated_at=now,
        calculation_version=DSP_WACC_VERSION,
    )
