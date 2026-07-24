"""Margin of Safety — shared-kernel value object.

Margin of Safety is the relative cushion between intrinsic value and
market value:

    ratio = (intrinsic_value − market_value) / intrinsic_value

Positive ratios mean the market price is below intrinsic value.
This type is framework-independent and calculated once in the
Valuation Engine, then propagated to committee and recommendation
surfaces without recalculation.
"""

from __future__ import annotations

from dataclasses import dataclass

from contracts.exceptions import ContractValidationError

__all__ = ["MarginOfSafety", "MARKET_CAPITALIZATION_KEY"]

#: Canonical ``FundamentalStatement.extra_line_items`` key for equity
#: market capitalization (populated by data_engine normalizers).
MARKET_CAPITALIZATION_KEY = "market_capitalization"


@dataclass(frozen=True, slots=True)
class MarginOfSafety:
    """Immutable margin-of-safety reading for one valuation.

    Attributes:
        ratio: ``(intrinsic − market) / intrinsic`` when available.
        intrinsic_value: Central intrinsic equity value used in the
            ratio (typically the mid of the valuation range).
        market_value: Equity market capitalization compared to
            intrinsic value.
        available: ``True`` when a usable ratio was computed.
    """

    ratio: float | None
    intrinsic_value: float | None
    market_value: float | None
    available: bool

    def __post_init__(self) -> None:
        """Enforce availability invariants.

        Raises:
            ContractValidationError: If availability disagrees with
                ``ratio``, or market/intrinsic values are negative.
        """
        if self.available and self.ratio is None:
            msg = "available MarginOfSafety must include ratio"
            raise ContractValidationError(msg)
        if not self.available and self.ratio is not None:
            msg = "unavailable MarginOfSafety must not include ratio"
            raise ContractValidationError(msg)
        if self.intrinsic_value is not None and self.intrinsic_value < 0:
            msg = (
                f"intrinsic_value must be non-negative, "
                f"got {self.intrinsic_value}"
            )
            raise ContractValidationError(msg)
        if self.market_value is not None and self.market_value < 0:
            msg = (
                f"market_value must be non-negative, got {self.market_value}"
            )
            raise ContractValidationError(msg)
