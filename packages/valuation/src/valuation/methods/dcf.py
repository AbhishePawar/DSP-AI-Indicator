"""Discounted cash flow methodology."""

from __future__ import annotations

from fundamental import FinancialSnapshot
from valuation.assumptions import ValuationAssumptions
from valuation.enums import ValuationMethod
from valuation.methods.base import ValuationMethodRunner
from valuation.models import IntrinsicValueEstimate

__all__ = ["DcfMethod"]

_FORMULA = (
    "FCF₀ = OCF − CapEx; "
    "FCFₜ = FCF₀(1+g)ᵗ; "
    "TV = FCFₙ(1+gₜ)/(r−gₜ); "
    "IV = Σ FCFₜ/(1+r)ᵗ + TV/(1+r)ⁿ"
)


class DcfMethod(ValuationMethodRunner):
    """Multi-stage free-cash-flow DCF with Gordon terminal value.

    Formula
        ``FCF₀ = operating_cash_flow − capital_expenditures``
        ``FCFₜ = FCF₀ × (1 + g)ᵗ`` for ``t = 1..N``
        ``TV = FCFₙ × (1 + g_terminal) / (r − g_terminal)``
        ``IV = Σₜ FCFₜ / (1+r)ᵗ + TV / (1+r)ⁿ``

    Uses injectable discount / growth / horizon assumptions.
    Disabled when OCF or CapEx is missing, or when FCF₀ ≤ 0.
    """

    @property
    def name(self) -> str:
        return ValuationMethod.DCF.value

    def estimate(
        self,
        snapshot: FinancialSnapshot,
        assumptions: ValuationAssumptions,
    ) -> IntrinsicValueEstimate:
        latest = snapshot.latest
        ocf = latest.operating_cash_flow
        capex = latest.capital_expenditures
        inputs = (
            "operating_cash_flow",
            "capital_expenditures",
            "discount_rate",
            "fcf_growth_rate",
            "terminal_growth_rate",
            "projection_years",
        )
        if ocf is None or capex is None:
            return IntrinsicValueEstimate(
                method=ValuationMethod.DCF,
                intrinsic_value=None,
                applicable=False,
                formula=_FORMULA,
                rationale=(
                    "DCF unavailable: operating_cash_flow or "
                    "capital_expenditures is missing."
                ),
                inputs_used=inputs,
            )
        fcf0 = float(ocf) - float(capex)
        if fcf0 <= 0:
            return IntrinsicValueEstimate(
                method=ValuationMethod.DCF,
                intrinsic_value=None,
                applicable=False,
                formula=_FORMULA,
                rationale=(
                    f"DCF skipped: base free cash flow non-positive ({fcf0:,.2f})."
                ),
                inputs_used=inputs,
            )

        r = float(assumptions.discount_rate)
        g = float(assumptions.fcf_growth_rate)
        g_t = float(assumptions.terminal_growth_rate)
        n = int(assumptions.projection_years)

        # P1-04 — runtime Gordon guard (defense in depth beyond assumptions ctor).
        if r <= 0:
            return IntrinsicValueEstimate(
                method=ValuationMethod.DCF,
                intrinsic_value=None,
                applicable=False,
                formula=_FORMULA,
                rationale=f"DCF unavailable: invalid discount_rate ({r}).",
                inputs_used=inputs,
            )
        if g_t >= r:
            return IntrinsicValueEstimate(
                method=ValuationMethod.DCF,
                intrinsic_value=None,
                applicable=False,
                formula=_FORMULA,
                rationale=(
                    "DCF unavailable: terminal_growth_rate >= discount_rate "
                    f"(g_t={g_t:g}, r={r:g})."
                ),
                inputs_used=inputs,
            )

        present_value = 0.0
        fcf_n = fcf0
        for t in range(1, n + 1):
            fcf_t = fcf0 * ((1.0 + g) ** t)
            present_value += fcf_t / ((1.0 + r) ** t)
            fcf_n = fcf_t

        terminal_value = fcf_n * (1.0 + g_t) / (r - g_t)
        present_value += terminal_value / ((1.0 + r) ** n)

        return IntrinsicValueEstimate(
            method=ValuationMethod.DCF,
            intrinsic_value=present_value,
            applicable=True,
            formula=_FORMULA,
            rationale=(
                f"DCF: FCF₀={fcf0:,.2f}, N={n}, r={r:g}, g={g:g}, "
                f"g_terminal={g_t:g} → IV={present_value:,.2f}."
            ),
            inputs_used=inputs,
        )
