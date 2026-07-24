"""Orchestration service for the AI Investment Committee.

:class:`InvestmentCommittee` registers :class:`CommitteeMember`
instances, executes each member's ``analyze()`` against a shared
:class:`~ai_committee.models.CommitteeInput`, aggregates opinions with
equal-weight plurality voting, and returns a fully explained
:class:`~ai_committee.models.CommitteeReport`.

No AI / LLM reasoning. No weights. No probabilities.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from ai_committee.enums import Decision
from ai_committee.exceptions import CommitteeError
from ai_committee.members.base import CommitteeMember
from ai_committee.members.economic import EconomicMember
from ai_committee.members.fundamental import FundamentalMember
from ai_committee.members.technical import TechnicalMember
from ai_committee.members.valuation import ValuationMember
from ai_committee.models import (
    CommitteeInput,
    CommitteeReport,
    InvestmentDecision,
    MemberVote,
    Opinion,
)
from ai_committee.voting import aggregate_recommendations

Clock = Callable[[], datetime]


def _default_clock() -> datetime:
    """Return the current, timezone-aware UTC timestamp."""
    return datetime.now(UTC)


def _default_members() -> list[CommitteeMember]:
    """Return the Sprint 8.1 default member roster."""
    return [
        TechnicalMember(),
        FundamentalMember(),
        EconomicMember(),
        ValuationMember(),
    ]


class InvestmentCommittee:
    """Registers members, collects opinions, and aggregates decisions.

    The committee never runs upstream engines itself — those are
    upstream. It only deliberates over their already-produced,
    explainable outputs (technical, fundamental, economic, valuation).
    """

    def __init__(
        self,
        members: Sequence[CommitteeMember] | None = None,
        *,
        clock: Clock = _default_clock,
    ) -> None:
        """Initialize the committee with an optional member roster.

        Args:
            members: Initial voting members. Defaults to Technical +
                Fundamental + Economic + Valuation when omitted.
            clock: Callable returning the current timezone-aware
                timestamp, stamped onto :class:`InvestmentDecision`.
        """
        initial = list(members) if members is not None else _default_members()
        self._members: list[CommitteeMember] = []
        for member in initial:
            self.register(member)
        self._clock = clock

    def register(self, member: CommitteeMember) -> None:
        """Register a committee member for future deliberations.

        Args:
            member: The member to add.

        Raises:
            CommitteeError: If a member with the same ``name`` is
                already registered.
        """
        if any(existing.name == member.name for existing in self._members):
            msg = f"member {member.name!r} is already registered"
            raise CommitteeError(msg)
        self._members.append(member)

    @property
    def members(self) -> tuple[CommitteeMember, ...]:
        """Return the registered members in registration order."""
        return tuple(self._members)

    def deliberate(self, context: CommitteeInput) -> CommitteeReport:
        """Execute all members and aggregate their opinions.

        Args:
            context: Upstream engine outputs for one instrument.

        Returns:
            A fully explained :class:`CommitteeReport`.

        Raises:
            CommitteeError: If no members are registered, or any
                member fails to analyze the context.
        """
        if not self._members:
            msg = "cannot deliberate with an empty member roster"
            raise CommitteeError(msg)

        opinions = tuple(
            member.analyze(context) for member in self._members
        )
        votes = tuple(
            MemberVote(
                source=opinion.source,
                recommendation=opinion.recommendation,
                opinion=opinion,
            )
            for opinion in opinions
        )
        overall = aggregate_recommendations(
            tuple(vote.recommendation for vote in votes)
        )
        decided_at = self._clock()
        rationale = _decision_rationale(overall, opinions)
        decision = InvestmentDecision(
            instrument=context.instrument,
            decision=overall,
            rationale=rationale,
            decided_at=decided_at,
        )
        voting_summary = _voting_summary(votes, overall)
        explanation = _build_explanation(decision, votes)
        return CommitteeReport(
            instrument=context.instrument,
            opinions=opinions,
            votes=votes,
            decision=decision,
            voting_summary=voting_summary,
            explanation=explanation,
        )


def _decision_rationale(
    overall: Decision,
    opinions: tuple[Opinion, ...],
) -> str:
    """Build a short rationale for the aggregated decision."""
    tally = ", ".join(
        f"{o.source}={o.recommendation.value}" for o in opinions
    )
    if overall is Decision.NEUTRAL:
        return (
            f"Members conflict ({tally}); overall decision is "
            f"{overall.value}."
        )
    if len({o.recommendation for o in opinions}) == 1:
        return (
            f"Members agree ({tally}); overall decision is "
            f"{overall.value}."
        )
    return (
        f"Members partially align ({tally}); overall decision is "
        f"{overall.value}."
    )


def _voting_summary(
    votes: tuple[MemberVote, ...],
    overall: Decision,
) -> str:
    """Build a short deterministic voting-summary line."""
    counts = {
        Decision.BUY: 0,
        Decision.HOLD: 0,
        Decision.SELL: 0,
    }
    for vote in votes:
        counts[vote.recommendation] += 1
    return (
        f"votes={len(votes)} "
        f"buy={counts[Decision.BUY]} "
        f"hold={counts[Decision.HOLD]} "
        f"sell={counts[Decision.SELL]} "
        f"→ {overall.value}"
    )


def _build_explanation(
    decision: InvestmentDecision,
    votes: tuple[MemberVote, ...],
) -> str:
    """Build the full human-readable CommitteeReport explanation."""
    member_lines = "\n".join(
        (
            f"- {vote.source}: {vote.recommendation.value} — "
            f"{vote.opinion.reasoning} "
            f"[evidence={len(vote.opinion.evidence)}]"
        )
        for vote in votes
    )
    evidence_count = sum(len(vote.opinion.evidence) for vote in votes)
    members = ", ".join(vote.source for vote in votes)
    return (
        f"Investment Committee deliberation for "
        f"{decision.instrument.symbol}.\n"
        f"Members voted: {members}.\n"
        f"{member_lines}\n"
        f"Final decision: {decision.decision.value}.\n"
        f"Rationale: {decision.rationale}\n"
        f"Evidence items used: {evidence_count}."
    )
