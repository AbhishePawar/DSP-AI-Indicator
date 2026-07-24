"""Owner-earnings (Buffett-style) methodology."""

from __future__ import annotations

from fundamental import FinancialSnapshot
from valuation.assumptions import ValuationAssumptions
from valuation.enums import ValuationMethod
from valuation.methods.base import ValuationMethodRunner
from valuation.models import IntrinsicValueEstimate

__all__ = ["OwnerEarningsMethod"]

_FORMULA = "OE = OCF − CapEx; IV = OE / cap_rate"


class OwnerEarningsMethod(ValuationMethodRunner):
    """Buffett-style owner earnings capitalized at an injectable yield.

    Formula
        ``OwnerEarnings ≈ operating_cash_flow − capital_expenditures``
        ``IV = OwnerEarnings / owner_earnings_cap_rate``

    CapEx on statements is a non-negative magnitude; it is subtracted
    from operating cash flow. Disabled when OCF or CapEx is missing,
    or when owner earnings are non-positive (cannot capitalize).
    """

    @property
    def name(self) -> str:
        return ValuationMethod.OWNER_EARNINGS.value

    def estimate(
        self,
        snapshot: FinancialSnapshot,
        assumptions: ValuationAssumptions,
    ) -> IntrinsicValueEstimate:
        latest = snapshot.latest
        ocf = latest.operating_cash_flow
        capex = latest.capital_expenditures
        cap_rate = assumptions.owner_earnings_cap_rate
        inputs = (
            "operating_cash_flow",
            "capital_expenditures",
            "owner_earnings_cap_rate",
        )
        if ocf is None or capex is None:
            return IntrinsicValueEstimate(
                method=ValuationMethod.OWNER_EARNINGS,
                intrinsic_value=None,
                applicable=False,
                formula=_FORMULA,
                rationale=(
                    "Owner earnings unavailable: operating_cash_flow or "
                    "capital_expenditures is missing."
                ),
                inputs_used=inputs,
            )
        owner_earnings = float(ocf) - float(capex)
        if owner_earnings <= 0:
            return IntrinsicValueEstimate(
                method=ValuationMethod.OWNER_EARNINGS,
                intrinsic_value=None,
                applicable=False,
                formula=_FORMULA,
                rationale=(
                    f"Owner earnings non-positive ({owner_earnings:,.2f}); "
                    "capitalization skipped."
                ),
                inputs_used=inputs,
            )
        value = owner_earnings / float(cap_rate)
        return IntrinsicValueEstimate(
            method=ValuationMethod.OWNER_EARNINGS,
            intrinsic_value=value,
            applicable=True,
            formula=_FORMULA,
            rationale=(
                f"Owner earnings {owner_earnings:,.2f} capitalized at "
                f"{cap_rate:g} → {value:,.2f}."
            ),
            inputs_used=inputs,
        )
