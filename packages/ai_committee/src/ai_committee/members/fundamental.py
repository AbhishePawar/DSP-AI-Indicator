"""Fundamental committee member — Fundamental Engine liaison."""

from __future__ import annotations

from contracts.enums import EngineSource, SignalDirection

from ai_committee.enums import Decision
from ai_committee.exceptions import CommitteeError
from ai_committee.members.base import CommitteeMember
from ai_committee.models import CommitteeInput, Opinion
from ai_committee.voting import collapse_signals

__all__ = ["FundamentalMember"]


class FundamentalMember(CommitteeMember):
    """Forms an opinion from a Fundamental Engine analysis.

    Reads ``context.fundamental`` and collapses every business-metric
    signal into one BUY / HOLD / SELL recommendation.
    """

    @property
    def name(self) -> str:
        """Canonical member identifier."""
        return "fundamental"

    @property
    def source_engine(self) -> EngineSource:
        """Provenance: Fundamental Engine."""
        return EngineSource.FUNDAMENTAL_ENGINE

    def analyze(self, context: CommitteeInput) -> Opinion:
        """Collapse Fundamental Engine output into one opinion.

        Args:
            context: Deliberation inputs; ``fundamental`` must be set.

        Returns:
            A standardized :class:`~ai_committee.models.Opinion`.

        Raises:
            CommitteeError: If ``context.fundamental`` is missing or
                describes a different instrument than
                ``context.instrument``.
        """
        analysis = context.fundamental
        if analysis is None:
            msg = "FundamentalMember requires context.fundamental"
            raise CommitteeError(msg)
        if analysis.instrument != context.instrument:
            msg = (
                "fundamental analysis instrument "
                f"{analysis.instrument.symbol!r} does not match "
                f"context instrument {context.instrument.symbol!r}"
            )
            raise CommitteeError(msg)

        recommendation = collapse_signals(analysis.signals)
        return Opinion(
            source=self.name,
            recommendation=recommendation,
            confidence=None,
            reasoning=_fundamental_reasoning(
                recommendation, analysis.signals
            ),
            evidence=analysis.evidence,
            engine=self.source_engine,
        )


def _fundamental_reasoning(
    recommendation: Decision,
    signals: tuple,
) -> str:
    """Build a deterministic rationale for the fundamental opinion."""
    bullish = sum(
        1 for s in signals if s.direction is SignalDirection.BULLISH
    )
    bearish = sum(
        1 for s in signals if s.direction is SignalDirection.BEARISH
    )
    neutral = sum(
        1 for s in signals if s.direction is SignalDirection.NEUTRAL
    )
    total = len(signals)
    return (
        f"Fundamental member recommends {recommendation.value} "
        f"({bullish} bullish, {bearish} bearish, {neutral} neutral "
        f"of {total} business-metric signals)."
    )
