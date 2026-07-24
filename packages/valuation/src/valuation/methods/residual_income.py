"""Residual-income methodology."""

from __future__ import annotations

from fundamental import FinancialSnapshot
from valuation.assumptions import ValuationAssumptions
from valuation.enums import ValuationMethod
from valuation.methods._math import safe_divide
from valuation.methods.base import ValuationMethodRunner
from valuation.models import IntrinsicValueEstimate

__all__ = ["ResidualIncomeMethod"]

_FORMULA = "ROE = NI / Equity; RI = (ROE − r)×Equity; IV = Equity + RI / r"


class ResidualIncomeMethod(ValuationMethodRunner):
    """Perpetual residual-income model when book equity and NI exist.

    Formula
        ``ROE = net_income / total_equity``
        ``RI = (ROE − r) × total_equity``
        ``IV = total_equity + RI / r``

    where ``r = residual_income_required_return``.

    Equivalent closed form: ``IV = Equity × ROE / r`` when ROE and r
    are defined. Disabled when net income or equity is missing, or
    equity ≤ 0.
    """

    @property
    def name(self) -> str:
        return ValuationMethod.RESIDUAL_INCOME.value

    def estimate(
        self,
        snapshot: FinancialSnapshot,
        assumptions: ValuationAssumptions,
    ) -> IntrinsicValueEstimate:
        latest = snapshot.latest
        net_income = latest.net_income
        equity = latest.total_equity
        r = assumptions.residual_income_required_return
        inputs = ("net_income", "total_equity", "residual_income_required_return")
        if net_income is None or equity is None:
            return IntrinsicValueEstimate(
                method=ValuationMethod.RESIDUAL_INCOME,
                intrinsic_value=None,
                applicable=False,
                formula=_FORMULA,
                rationale=(
                    "Residual income unavailable: net_income or "
                    "total_equity is missing."
                ),
                inputs_used=inputs,
            )
        if equity <= 0:
            return IntrinsicValueEstimate(
                method=ValuationMethod.RESIDUAL_INCOME,
                intrinsic_value=None,
                applicable=False,
                formula=_FORMULA,
                rationale=(
                    f"Residual income skipped: total_equity non-positive ({equity})."
                ),
                inputs_used=inputs,
            )
        roe = safe_divide(float(net_income), float(equity))
        assert roe is not None
        residual_income = (roe - float(r)) * float(equity)
        value = float(equity) + residual_income / float(r)
        return IntrinsicValueEstimate(
            method=ValuationMethod.RESIDUAL_INCOME,
            intrinsic_value=value,
            applicable=True,
            formula=_FORMULA,
            rationale=(
                f"Residual income: ROE={roe:.4f}, r={r:g}, "
                f"RI={residual_income:,.2f} → IV={value:,.2f}."
            ),
            inputs_used=inputs,
        )
