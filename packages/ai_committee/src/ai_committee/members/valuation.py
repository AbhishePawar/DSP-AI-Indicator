"""Valuation committee member — Valuation Engine liaison."""

from __future__ import annotations

from contracts import EngineSource, ValuationConfidence, ValuationContext

from ai_committee.enums import Decision
from ai_committee.exceptions import CommitteeError
from ai_committee.members.base import CommitteeMember
from ai_committee.models import CommitteeInput, Opinion

__all__ = ["ValuationMember"]

#: Graham-style cushion: undervalued enough to vote BUY.
_BUY_MOS = 0.20
#: Overvalued enough to vote SELL.
_SELL_MOS = -0.20
#: Only HIGH/MEDIUM confidence assessments cast directional votes.
_VOTABLE = frozenset(
    {ValuationConfidence.HIGH, ValuationConfidence.MEDIUM}
)
_CONFIDENCE_SCORE: dict[ValuationConfidence, float | None] = {
    ValuationConfidence.HIGH: 0.85,
    ValuationConfidence.MEDIUM: 0.65,
    ValuationConfidence.LOW: 0.40,
    ValuationConfidence.INSUFFICIENT: None,
}


class ValuationMember(CommitteeMember):
    """Forms an opinion from a Valuation Engine context DTO.

    Reads ``context.valuation`` and maps margin of safety plus
    confidence onto BUY / HOLD / SELL. MoS and valuation summary are
    propagated onto the Opinion without recalculation (Phase A1).
    """

    @property
    def name(self) -> str:
        """Canonical member identifier."""
        return "valuation"

    @property
    def source_engine(self) -> EngineSource:
        """Provenance: Valuation Engine."""
        return EngineSource.VALUATION_ENGINE

    def analyze(self, context: CommitteeInput) -> Opinion:
        """Map a ValuationContext into one opinion.

        Args:
            context: Deliberation inputs; ``valuation`` must be set and
                match ``context.instrument``.

        Returns:
            A standardized :class:`~ai_committee.models.Opinion`.

        Raises:
            CommitteeError: If ``context.valuation`` is missing or
                describes a different instrument than
                ``context.instrument``.
        """
        assessment = context.valuation
        if assessment is None:
            msg = "ValuationMember requires context.valuation"
            raise CommitteeError(msg)
        if assessment.instrument != context.instrument:
            msg = (
                "valuation assessment instrument "
                f"{assessment.instrument.symbol!r} does not match "
                f"context instrument {context.instrument.symbol!r}"
            )
            raise CommitteeError(msg)

        recommendation = map_valuation_decision(assessment)
        return Opinion(
            source=self.name,
            recommendation=recommendation,
            confidence=_CONFIDENCE_SCORE.get(assessment.confidence),
            reasoning=_valuation_reasoning(assessment, recommendation),
            evidence=assessment.evidence,
            engine=self.source_engine,
            margin_of_safety=assessment.margin_of_safety,
            valuation_summary=assessment.valuation_summary,
        )


def map_valuation_decision(assessment: ValuationContext) -> Decision:
    """Derive BUY / HOLD / SELL from margin of safety and confidence.

    Rules (deterministic):

    * MoS unavailable, or confidence not HIGH/MEDIUM → HOLD
    * MoS ≥ +20% → BUY
    * MoS ≤ −20% → SELL
    * otherwise → HOLD
    """
    mos = assessment.margin_of_safety
    if (
        not mos.available
        or mos.ratio is None
        or assessment.confidence not in _VOTABLE
    ):
        return Decision.HOLD
    if mos.ratio >= _BUY_MOS:
        return Decision.BUY
    if mos.ratio <= _SELL_MOS:
        return Decision.SELL
    return Decision.HOLD


def _valuation_reasoning(
    assessment: ValuationContext,
    recommendation: Decision,
) -> str:
    """Preserve assessment reasoning with an explicit member prefix."""
    mos = assessment.margin_of_safety
    mos_text = (
        f"{mos.ratio:.2%}"
        if mos.available and mos.ratio is not None
        else "n/a"
    )
    mid = assessment.valuation_summary.intrinsic_mid
    mid_text = f"{mid:,.2f}" if mid is not None else "n/a"
    return (
        f"Valuation member recommends {recommendation.value} "
        f"(mos={mos_text}, confidence={assessment.confidence.value}, "
        f"mid={mid_text}): {assessment.reasoning}"
    )
