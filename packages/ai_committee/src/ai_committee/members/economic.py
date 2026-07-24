"""Economic committee member — Economic Engine liaison."""

from __future__ import annotations

from contracts import AnalyticalStance, EconomicContext, EngineSource

from ai_committee.enums import Decision
from ai_committee.exceptions import CommitteeError
from ai_committee.members.base import CommitteeMember
from ai_committee.models import CommitteeInput, Opinion

__all__ = ["EconomicMember"]

_ECO_TO_DECISION: dict[AnalyticalStance, Decision] = {
    AnalyticalStance.BUY: Decision.BUY,
    AnalyticalStance.HOLD: Decision.HOLD,
    AnalyticalStance.SELL: Decision.SELL,
}


class EconomicMember(CommitteeMember):
    """Forms an opinion from an Economic Engine assessment context.

    Reads ``context.economic`` (contracts DTO) and maps its stance,
    reasoning, and evidence onto a standardized Opinion with no
    information loss.
    """

    @property
    def name(self) -> str:
        """Canonical member identifier."""
        return "economic"

    @property
    def source_engine(self) -> EngineSource:
        """Provenance: Economic Engine."""
        return EngineSource.ECONOMIC_ENGINE

    def analyze(self, context: CommitteeInput) -> Opinion:
        """Map an EconomicContext into one opinion.

        Args:
            context: Deliberation inputs; ``economic`` must be set.
                Economic contexts are macro / country-level and are
                not checked against ``context.instrument``.

        Returns:
            A standardized :class:`~ai_committee.models.Opinion`.

        Raises:
            CommitteeError: If ``context.economic`` is missing.
        """
        assessment = context.economic
        if assessment is None:
            msg = "EconomicMember requires context.economic"
            raise CommitteeError(msg)

        recommendation = _map_recommendation(assessment)
        return Opinion(
            source=self.name,
            recommendation=recommendation,
            confidence=None,
            reasoning=_economic_reasoning(assessment, recommendation),
            evidence=assessment.evidence,
            engine=self.source_engine,
        )


def _map_recommendation(assessment: EconomicContext) -> Decision:
    """Map contracts AnalyticalStance onto committee Decision."""
    return _ECO_TO_DECISION[assessment.stance]


def _economic_reasoning(
    assessment: EconomicContext,
    recommendation: Decision,
) -> str:
    """Preserve assessment reasoning with an explicit member prefix."""
    return (
        f"Economic member recommends {recommendation.value} "
        f"(condition={assessment.overall_condition}, "
        f"country={assessment.country}): {assessment.reasoning}"
    )
