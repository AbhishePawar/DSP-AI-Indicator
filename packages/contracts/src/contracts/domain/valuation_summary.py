"""Valuation summary — shared-kernel readout of one valuation pass.

Carries the aggregated intrinsic-value range, margin of safety, and
confidence label produced by the Valuation Engine. Downstream layers
(committee, recommendation) consume this object rather than
recomputing valuation math.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from contracts._validation import ensure_non_empty_str
from contracts.domain.margin_of_safety import MarginOfSafety
from contracts.exceptions import ContractValidationError

__all__ = ["ValuationSummary"]


@dataclass(frozen=True, slots=True)
class ValuationSummary:
    """Immutable valuation readout for committee and recommendation use.

    Attributes:
        intrinsic_low: Lowest applicable intrinsic estimate.
        intrinsic_mid: Central (median) intrinsic estimate.
        intrinsic_high: Highest applicable intrinsic estimate.
        margin_of_safety: MoS computed once against market capitalization.
        confidence: Engine confidence label (``high`` / ``medium`` /
            ``low`` / ``insufficient``).
        currency: ISO 4217 currency of monetary figures.
        as_of: Statement / valuation as-of date.
    """

    intrinsic_low: float | None
    intrinsic_mid: float | None
    intrinsic_high: float | None
    margin_of_safety: MarginOfSafety
    confidence: str
    currency: str
    as_of: date

    def __post_init__(self) -> None:
        """Normalize confidence/currency and validate range ordering."""
        confidence = ensure_non_empty_str(
            self.confidence, field_name="confidence"
        ).lower()
        currency = ensure_non_empty_str(
            self.currency, field_name="currency"
        ).upper()
        low, mid, high = (
            self.intrinsic_low,
            self.intrinsic_mid,
            self.intrinsic_high,
        )
        if low is not None and high is not None and low > high:
            msg = f"intrinsic_low ({low}) must not exceed intrinsic_high ({high})"
            raise ContractValidationError(msg)
        if mid is not None and low is not None and mid < low:
            msg = f"intrinsic_mid ({mid}) must not be below intrinsic_low ({low})"
            raise ContractValidationError(msg)
        if mid is not None and high is not None and mid > high:
            msg = (
                f"intrinsic_mid ({mid}) must not exceed intrinsic_high ({high})"
            )
            raise ContractValidationError(msg)
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "currency", currency)
