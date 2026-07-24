"""Internal data models for the AI Investment Committee.

None of :class:`Opinion`, :class:`MemberVote`,
:class:`InvestmentDecision`, :class:`CommitteeReport`, or
:class:`CommitteeInput` is a ``contracts`` type. They exist purely to
carry deliberation state inside this package. Other engines must never
import them directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contracts.domain.committee_context import (
    EconomicContext,
    FundamentalContext,
    TechnicalContext,
    ValuationContext,
)
from contracts.domain.evidence import Evidence
from contracts.domain.instrument import Instrument
from contracts.domain.margin_of_safety import MarginOfSafety
from contracts.domain.valuation_summary import ValuationSummary
from contracts.enums import EngineSource
from core.exceptions import ValidationError

from ai_committee.enums import Decision

#: Recommendations a single member is allowed to cast. NEUTRAL is
#: reserved for the committee's aggregated decision when members
#: conflict (BUY vs SELL).
_MEMBER_RECOMMENDATIONS: frozenset[Decision] = frozenset(
    {Decision.BUY, Decision.HOLD, Decision.SELL}
)


@dataclass(frozen=True, slots=True)
class CommitteeInput:
    """One deliberation round's upstream analytical contexts.

    Every optional field is a contracts DTO — never an engine-native
    assessment type. Orchestration maps engine results onto these
    contexts before deliberation.

    Attributes:
        instrument: The instrument under deliberation.
        technical: Optional Indicator Engine context.
        fundamental: Optional Fundamental Engine context.
        economic: Optional Economic Engine context (macro).
        valuation: Optional Valuation Engine context.

    Future members (Behavioral, …) extend this object with additional
    optional fields — additive, never a redesign of the committee itself.
    """

    instrument: Instrument
    technical: TechnicalContext | None = None
    fundamental: FundamentalContext | None = None
    economic: EconomicContext | None = None
    valuation: ValuationContext | None = None


@dataclass(frozen=True, slots=True)
class Opinion:
    """One analytical engine's standardized recommendation.

    Attributes:
        source: Canonical member / engine identifier (e.g.
            ``"technical"``, ``"fundamental"``).
        recommendation: Member-level decision (BUY / HOLD / SELL).
        confidence: Reserved for future weighted / probabilistic
            voting. Always ``None`` in Sprint 5.0.
        reasoning: Human-readable rationale for ``recommendation``.
        evidence: Supporting ``contracts.Evidence`` items carried
            forward from the upstream engine.
        engine: Provenance tag naming which platform engine produced
            the underlying signals.
        margin_of_safety: Optional MoS propagated from Valuation
            (never recalculated in the committee).
        valuation_summary: Optional valuation readout propagated from
            Valuation (never recalculated in the committee).
    """

    source: str
    recommendation: Decision
    reasoning: str
    evidence: tuple[Evidence, ...] = ()
    confidence: float | None = None
    engine: EngineSource | None = None
    margin_of_safety: MarginOfSafety | None = None
    valuation_summary: ValuationSummary | None = None

    def __post_init__(self) -> None:
        """Normalize source and validate recommendation / reasoning.

        Raises:
            ValidationError: If ``source`` or ``reasoning`` is empty,
                ``recommendation`` is NEUTRAL, or ``confidence`` is set
                outside ``[0.0, 1.0]``.
        """
        source = self.source.strip().lower()
        if not source:
            msg = "source must not be empty"
            raise ValidationError(msg)
        if self.recommendation not in _MEMBER_RECOMMENDATIONS:
            msg = (
                "opinion.recommendation must be BUY, HOLD, or SELL; "
                f"got {self.recommendation!r}"
            )
            raise ValidationError(msg)
        reasoning = self.reasoning.strip()
        if not reasoning:
            msg = "reasoning must not be empty"
            raise ValidationError(msg)
        if self.confidence is not None and not (
            0.0 <= self.confidence <= 1.0
        ):
            msg = "confidence must be in [0.0, 1.0] when provided"
            raise ValidationError(msg)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "reasoning", reasoning)
        object.__setattr__(self, "evidence", tuple(self.evidence))


@dataclass(frozen=True, slots=True)
class MemberVote:
    """One recorded vote cast during a committee deliberation.

    Attributes:
        source: Canonical member identifier (matches
            :attr:`Opinion.source`).
        recommendation: The recommendation cast as this member's vote.
        opinion: The full opinion the vote was derived from.
    """

    source: str
    recommendation: Decision
    opinion: Opinion

    def __post_init__(self) -> None:
        """Normalize source and enforce opinion consistency.

        Raises:
            ValidationError: If ``source`` is empty or disagrees with
                ``opinion.source`` / ``opinion.recommendation``.
        """
        source = self.source.strip().lower()
        if not source:
            msg = "source must not be empty"
            raise ValidationError(msg)
        if source != self.opinion.source:
            msg = (
                "source must match opinion.source "
                f"({self.opinion.source!r}), got {source!r}"
            )
            raise ValidationError(msg)
        if self.recommendation is not self.opinion.recommendation:
            msg = (
                "recommendation must match opinion.recommendation "
                f"({self.opinion.recommendation!r}), got "
                f"{self.recommendation!r}"
            )
            raise ValidationError(msg)
        object.__setattr__(self, "source", source)


@dataclass(frozen=True, slots=True)
class InvestmentDecision:
    """The committee's final decision for one instrument.

    Attributes:
        instrument: The instrument the decision applies to.
        decision: Overall decision after aggregation (BUY / HOLD /
            SELL / NEUTRAL).
        rationale: Human-readable summary of why this decision was
            reached.
        decided_at: Timezone-aware timestamp of the deliberation.
    """

    instrument: Instrument
    decision: Decision
    rationale: str
    decided_at: datetime

    def __post_init__(self) -> None:
        """Validate non-empty rationale.

        Raises:
            ValidationError: If ``rationale`` is empty.
        """
        rationale = self.rationale.strip()
        if not rationale:
            msg = "rationale must not be empty"
            raise ValidationError(msg)
        object.__setattr__(self, "rationale", rationale)


@dataclass(frozen=True, slots=True)
class CommitteeReport:
    """Full, explainable record of one committee deliberation.

    Attributes:
        instrument: The instrument that was deliberated.
        opinions: Every :class:`Opinion` collected, in member order.
        votes: Every :class:`MemberVote` cast, in member order.
        decision: The final :class:`InvestmentDecision`.
        voting_summary: Short deterministic summary of the vote tally.
        explanation: Full human-readable deliberation narrative —
            who voted, each opinion, evidence, reasoning, and the
            final decision.
    """

    instrument: Instrument
    opinions: tuple[Opinion, ...]
    votes: tuple[MemberVote, ...]
    decision: InvestmentDecision
    voting_summary: str
    explanation: str

    def __post_init__(self) -> None:
        """Validate non-empty content and instrument consistency.

        Raises:
            ValidationError: If required collections / strings are
                empty or ``decision.instrument`` disagrees.
        """
        opinions = tuple(self.opinions)
        votes = tuple(self.votes)
        if not opinions:
            msg = "opinions must not be empty"
            raise ValidationError(msg)
        if not votes:
            msg = "votes must not be empty"
            raise ValidationError(msg)
        if len(opinions) != len(votes):
            msg = "opinions and votes must have the same length"
            raise ValidationError(msg)
        voting_summary = self.voting_summary.strip()
        if not voting_summary:
            msg = "voting_summary must not be empty"
            raise ValidationError(msg)
        explanation = self.explanation.strip()
        if not explanation:
            msg = "explanation must not be empty"
            raise ValidationError(msg)
        if self.decision.instrument != self.instrument:
            msg = (
                "decision.instrument must match report instrument "
                f"({self.instrument.symbol})"
            )
            raise ValidationError(msg)
        object.__setattr__(self, "opinions", opinions)
        object.__setattr__(self, "votes", votes)
        object.__setattr__(self, "voting_summary", voting_summary)
        object.__setattr__(self, "explanation", explanation)

    @property
    def members_participated(self) -> tuple[str, ...]:
        """Return every voting member's source name, in vote order."""
        return tuple(vote.source for vote in self.votes)

    @property
    def evidence_used(self) -> tuple[Evidence, ...]:
        """Return every evidence item cited across all opinions."""
        return tuple(
            item for opinion in self.opinions for item in opinion.evidence
        )
