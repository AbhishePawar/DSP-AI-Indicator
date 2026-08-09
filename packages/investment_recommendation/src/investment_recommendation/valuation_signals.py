"""Public valuation signal contract for decision intelligence.

Built from ``OverallValuationResult`` public fields only — never internal models.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from investment_recommendation.adapters import explained_value
from investment_recommendation.exceptions import (
    InvestmentRecommendationValidationError,
)

__all__ = ["ValuationSignals"]


@dataclass(frozen=True, slots=True)
class ValuationSignals:
    """Share-level valuation signals consumed by the recommendation engine."""

    intrinsic_value_per_share: float | None
    current_market_price: float | None
    margin_of_safety: float | None = None
    premium_discount: float | None = None
    # Default 0.0 — never invent mid-confidence when callers omit evidence.
    confidence: float = 0.0

    def __post_init__(self) -> None:
        conf = float(self.confidence)
        if not 0.0 <= conf <= 1.0:
            raise InvestmentRecommendationValidationError(
                "ValuationSignals.confidence must be in [0.0, 1.0]"
            )
        object.__setattr__(self, "confidence", conf)
        ivps = self.intrinsic_value_per_share
        price = self.current_market_price
        mos = self.margin_of_safety
        premium = self.premium_discount
        if mos is None and ivps is not None and price is not None and ivps != 0:
            mos = (float(ivps) - float(price)) / float(ivps)
            object.__setattr__(self, "margin_of_safety", mos)
        if (
            premium is None
            and ivps is not None
            and price is not None
            and ivps != 0
        ):
            premium = (float(price) - float(ivps)) / float(ivps)
            object.__setattr__(self, "premium_discount", premium)

    @classmethod
    def from_overall(cls, valuation: object) -> ValuationSignals:
        """Extract public OverallValuationResult fields."""
        return cls(
            intrinsic_value_per_share=explained_value(
                valuation, "overall_intrinsic_value_per_share"
            ),
            current_market_price=explained_value(
                valuation, "current_market_price"
            ),
            margin_of_safety=explained_value(valuation, "margin_of_safety"),
            premium_discount=explained_value(valuation, "premium_discount"),
            confidence=explained_value(valuation, "confidence") or 0.0,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "intrinsic_value_per_share": self.intrinsic_value_per_share,
            "current_market_price": self.current_market_price,
            "margin_of_safety": self.margin_of_safety,
            "premium_discount": self.premium_discount,
            "confidence": self.confidence,
        }
