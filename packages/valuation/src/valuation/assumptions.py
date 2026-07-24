"""Injectable conservative valuation assumptions.

No hardcoded secrets. Defaults are documented conservative starting
points; callers should inject domain-appropriate values.
"""

from __future__ import annotations

from dataclasses import dataclass

from valuation.exceptions import ValuationError

__all__ = ["ValuationAssumptions"]


@dataclass(frozen=True, slots=True)
class ValuationAssumptions:
    """Conservative, injectable parameters for valuation methods.

    Attributes:
        discount_rate: Required return / WACC proxy used by DCF (decimal).
        fcf_growth_rate: Explicit-period free-cash-flow growth (decimal).
        terminal_growth_rate: Perpetual growth after the projection
            horizon (decimal). Must be strictly less than
            ``discount_rate``.
        projection_years: Explicit DCF forecast horizon (positive int).
        earnings_multiple: Conservative P/E applied to net income.
        owner_earnings_cap_rate: Capitalization rate for owner earnings
            (decimal yield).
        residual_income_required_return: Cost of equity for residual
            income (decimal).
    """

    discount_rate: float = 0.10
    fcf_growth_rate: float = 0.03
    terminal_growth_rate: float = 0.02
    projection_years: int = 5
    earnings_multiple: float = 12.0
    owner_earnings_cap_rate: float = 0.08
    residual_income_required_return: float = 0.10

    def __post_init__(self) -> None:
        """Validate conservative assumption bounds.

        Raises:
            ValuationError: If rates or multiples are not usable.
        """
        if self.discount_rate <= 0:
            msg = f"discount_rate must be positive, got {self.discount_rate}"
            raise ValuationError(msg)
        if self.fcf_growth_rate < -0.5:
            msg = f"fcf_growth_rate out of range: {self.fcf_growth_rate}"
            raise ValuationError(msg)
        if self.terminal_growth_rate < 0:
            msg = (
                f"terminal_growth_rate must be non-negative, "
                f"got {self.terminal_growth_rate}"
            )
            raise ValuationError(msg)
        if self.terminal_growth_rate >= self.discount_rate:
            msg = (
                "terminal_growth_rate must be strictly less than discount_rate "
                f"({self.terminal_growth_rate} >= {self.discount_rate})"
            )
            raise ValuationError(msg)
        if self.projection_years < 1:
            msg = f"projection_years must be >= 1, got {self.projection_years}"
            raise ValuationError(msg)
        if self.earnings_multiple <= 0:
            msg = f"earnings_multiple must be positive, got {self.earnings_multiple}"
            raise ValuationError(msg)
        if self.owner_earnings_cap_rate <= 0:
            msg = (
                "owner_earnings_cap_rate must be positive, "
                f"got {self.owner_earnings_cap_rate}"
            )
            raise ValuationError(msg)
        if self.residual_income_required_return <= 0:
            msg = (
                "residual_income_required_return must be positive, "
                f"got {self.residual_income_required_return}"
            )
            raise ValuationError(msg)
