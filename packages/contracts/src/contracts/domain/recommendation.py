"""Recommendation domain contract.

A :class:`Recommendation` is the terminal output of the AI Investment
Committee for a single instrument: a discrete action, a conviction level,
and the evidence trail that justifies it. Every recommendation is required
to carry a non-empty rationale, and should carry supporting evidence — a
recommendation without an explanation is not a valid instance of this
contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contracts._validation import (
    ensure_in_range,
    ensure_non_empty_str,
    ensure_timezone_aware,
)
from contracts.domain.evidence import Evidence
from contracts.domain.instrument import Instrument
from contracts.domain.margin_of_safety import MarginOfSafety
from contracts.domain.valuation_summary import ValuationSummary
from contracts.enums import RecommendationAction


@dataclass(frozen=True, slots=True)
class Recommendation:
    """Immutable, explainable investment recommendation for one instrument.

    Attributes:
        instrument: The instrument this recommendation applies to.
        action: The recommended discrete action.
        conviction: Confidence in the recommendation, normalized to
            ``[0.0, 1.0]``.
        rationale: Human-readable summary of why this action is
            recommended.
        generated_at: Timezone-aware timestamp the recommendation was
            generated.
        supporting_evidence: Evidence items that justify the
            recommendation.
        dissenting_views: Optional recorded minority/opposing viewpoints
            considered during committee deliberation.
        time_horizon: Optional intended holding period (e.g. ``"3M"``,
            ``"12M"``).
        target_price: Optional target price associated with the
            recommendation.
        margin_of_safety: Optional MoS propagated from the Valuation
            Engine (never recalculated here).
        valuation_summary: Optional valuation readout propagated from
            the Valuation Engine.
    """

    instrument: Instrument
    action: RecommendationAction
    conviction: float
    rationale: str
    generated_at: datetime
    supporting_evidence: tuple[Evidence, ...] = ()
    dissenting_views: tuple[str, ...] = ()
    time_horizon: str | None = None
    target_price: float | None = None
    margin_of_safety: MarginOfSafety | None = None
    valuation_summary: ValuationSummary | None = None

    def __post_init__(self) -> None:
        """Validate conviction bounds, rationale content, and timestamp.

        Raises:
            ContractValidationError: If ``conviction`` is outside
                ``[0.0, 1.0]``, ``rationale`` is empty, or
                ``generated_at`` is a naive datetime.
        """
        conviction = ensure_in_range(
            self.conviction, field_name="conviction", minimum=0.0, maximum=1.0
        )
        rationale = ensure_non_empty_str(self.rationale, field_name="rationale")
        ensure_timezone_aware(self.generated_at, field_name="generated_at")

        object.__setattr__(self, "conviction", conviction)
        object.__setattr__(self, "rationale", rationale)
        object.__setattr__(
            self, "supporting_evidence", tuple(self.supporting_evidence)
        )
        object.__setattr__(self, "dissenting_views", tuple(self.dissenting_views))
