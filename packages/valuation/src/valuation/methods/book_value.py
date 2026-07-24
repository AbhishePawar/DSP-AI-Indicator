"""Book-value / asset-value methodology."""

from __future__ import annotations

from fundamental import FinancialSnapshot
from valuation.assumptions import ValuationAssumptions
from valuation.enums import ValuationMethod
from valuation.methods.base import ValuationMethodRunner
from valuation.models import IntrinsicValueEstimate

__all__ = ["BookValueMethod"]

_FORMULA = "IV = total_equity"


class BookValueMethod(ValuationMethodRunner):
    """Intrinsic value equals reported book equity.

    Formula
        ``IV = total_equity`` (latest statement).

    Disabled when ``total_equity`` is missing.
    """

    @property
    def name(self) -> str:
        return ValuationMethod.BOOK_VALUE.value

    def estimate(
        self,
        snapshot: FinancialSnapshot,
        assumptions: ValuationAssumptions,
    ) -> IntrinsicValueEstimate:
        del assumptions  # unused — book value needs no growth/discount inputs
        equity = snapshot.latest.total_equity
        if equity is None:
            return IntrinsicValueEstimate(
                method=ValuationMethod.BOOK_VALUE,
                intrinsic_value=None,
                applicable=False,
                formula=_FORMULA,
                rationale="Book value unavailable: total_equity is missing.",
                inputs_used=("total_equity",),
            )
        return IntrinsicValueEstimate(
            method=ValuationMethod.BOOK_VALUE,
            intrinsic_value=float(equity),
            applicable=True,
            formula=_FORMULA,
            rationale=f"Book value / asset value equals reported equity {equity:,.2f}.",
            inputs_used=("total_equity",),
        )
