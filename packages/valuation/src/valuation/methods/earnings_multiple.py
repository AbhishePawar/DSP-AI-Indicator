"""Earnings-multiple methodology."""

from __future__ import annotations

from fundamental import FinancialSnapshot
from valuation.assumptions import ValuationAssumptions
from valuation.enums import ValuationMethod
from valuation.methods.base import ValuationMethodRunner
from valuation.models import IntrinsicValueEstimate

__all__ = ["EarningsMultipleMethod"]

_FORMULA = "IV = net_income × earnings_multiple"


class EarningsMultipleMethod(ValuationMethodRunner):
    """Capitalize trailing net income at a conservative earnings multiple.

    Formula
        ``IV = net_income × earnings_multiple``

    Uses injectable ``ValuationAssumptions.earnings_multiple`` (default 12).
    Disabled when ``net_income`` is missing.
    """

    @property
    def name(self) -> str:
        return ValuationMethod.EARNINGS_MULTIPLE.value

    def estimate(
        self,
        snapshot: FinancialSnapshot,
        assumptions: ValuationAssumptions,
    ) -> IntrinsicValueEstimate:
        net_income = snapshot.latest.net_income
        multiple = assumptions.earnings_multiple
        if net_income is None:
            return IntrinsicValueEstimate(
                method=ValuationMethod.EARNINGS_MULTIPLE,
                intrinsic_value=None,
                applicable=False,
                formula=_FORMULA,
                rationale="Earnings multiple unavailable: net_income is missing.",
                inputs_used=("net_income", "earnings_multiple"),
            )
        # P1-04 — do not capitalize non-positive earnings into a false IV.
        if float(net_income) <= 0:
            return IntrinsicValueEstimate(
                method=ValuationMethod.EARNINGS_MULTIPLE,
                intrinsic_value=None,
                applicable=False,
                formula=_FORMULA,
                rationale=(
                    "Earnings multiple unavailable: net_income is non-positive "
                    f"({net_income})."
                ),
                inputs_used=("net_income", "earnings_multiple"),
            )
        value = float(net_income) * float(multiple)
        return IntrinsicValueEstimate(
            method=ValuationMethod.EARNINGS_MULTIPLE,
            intrinsic_value=value,
            applicable=True,
            formula=_FORMULA,
            rationale=(
                f"Earnings multiple: {net_income:,.2f} × {multiple:g} = {value:,.2f}."
            ),
            inputs_used=("net_income", "earnings_multiple"),
        )
