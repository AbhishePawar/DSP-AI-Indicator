"""Pure mapper from committee deliberation to contracts.Recommendation."""

from __future__ import annotations

from ai_committee import CommitteeReport, Decision, InvestmentDecision, Opinion
from contracts.domain.evidence import Evidence
from contracts.domain.margin_of_safety import MarginOfSafety
from contracts.domain.recommendation import Recommendation
from contracts.domain.valuation_summary import ValuationSummary
from contracts.enums import RecommendationAction
from contracts.exceptions import ContractValidationError
from recommendation.exceptions import RecommendationMappingError

__all__ = ["RecommendationMapper"]

_DECISION_TO_ACTION: dict[Decision, RecommendationAction] = {
    Decision.BUY: RecommendationAction.BUY,
    Decision.HOLD: RecommendationAction.HOLD,
    Decision.SELL: RecommendationAction.SELL,
    # Contracts has no NEUTRAL action — conflict resolves to HOLD with
    # conviction reflecting the lack of majority (see _conviction).
    Decision.NEUTRAL: RecommendationAction.HOLD,
}


class RecommendationMapper:
    """Stateless translator: ``CommitteeReport`` → ``Recommendation``.

    No analysis, voting, provider I/O, or side effects. Every field on
    the output is derived deterministically from the input report.
    """

    @staticmethod
    def map(report: CommitteeReport) -> Recommendation:
        """Map a full committee report onto ``contracts.Recommendation``.

        Args:
            report: Completed deliberation record from
                ``InvestmentCommittee.deliberate``.

        Returns:
            Immutable ``contracts.Recommendation``.

        Raises:
            RecommendationMappingError: If the report cannot be
                translated into a valid Recommendation.
        """
        try:
            action = RecommendationMapper._map_action(report.decision.decision)
            conviction = RecommendationMapper._conviction(report)
            supporting = RecommendationMapper._supporting_evidence(report)
            dissenting = RecommendationMapper._dissenting_views(report)
            rationale = RecommendationMapper._rationale(report)
            mos, summary = RecommendationMapper._valuation_payload(report)

            return Recommendation(
                instrument=report.instrument,
                action=action,
                conviction=conviction,
                rationale=rationale,
                generated_at=report.decision.decided_at,
                supporting_evidence=supporting,
                dissenting_views=dissenting,
                time_horizon=None,
                target_price=None,
                margin_of_safety=mos,
                valuation_summary=summary,
            )
        except ContractValidationError as exc:
            msg = f"mapped Recommendation failed contracts validation: {exc}"
            raise RecommendationMappingError(msg) from exc

    @staticmethod
    def map_decision(
        decision: InvestmentDecision,
        *,
        supporting_evidence: tuple[Evidence, ...] = (),
        dissenting_views: tuple[str, ...] = (),
        conviction: float | None = None,
    ) -> Recommendation:
        """Map a standalone ``InvestmentDecision`` (without full report).

        Useful when only the final decision object is available. Prefer
        :meth:`map` when a ``CommitteeReport`` exists so evidence and
        dissent can be recovered.

        Args:
            decision: Final committee decision.
            supporting_evidence: Optional evidence trail.
            dissenting_views: Optional dissenting narratives.
            conviction: Optional conviction override in ``[0.0, 1.0]``.
                Defaults to ``0.5`` when omitted (no vote tally available).

        Returns:
            Immutable ``contracts.Recommendation``.
        """
        try:
            return Recommendation(
                instrument=decision.instrument,
                action=RecommendationMapper._map_action(decision.decision),
                conviction=0.5 if conviction is None else conviction,
                rationale=decision.rationale,
                generated_at=decision.decided_at,
                supporting_evidence=supporting_evidence,
                dissenting_views=dissenting_views,
            )
        except ContractValidationError as exc:
            msg = f"mapped Recommendation failed contracts validation: {exc}"
            raise RecommendationMappingError(msg) from exc

    @staticmethod
    def _map_action(decision: Decision) -> RecommendationAction:
        try:
            return _DECISION_TO_ACTION[decision]
        except KeyError as exc:
            msg = f"unsupported committee Decision: {decision!r}"
            raise RecommendationMappingError(msg) from exc

    @staticmethod
    def _conviction(report: CommitteeReport) -> float:
        """Derive conviction from vote agreement with the final decision.

        Unanimous agreement → ``1.0``. Split majority → fraction agreeing.
        ``NEUTRAL`` (BUY vs SELL conflict) → ``0.5``.
        """
        decision = report.decision.decision
        votes = report.votes
        if not votes:
            return 0.5
        if decision is Decision.NEUTRAL:
            return 0.5
        agreeing = sum(1 for vote in votes if vote.recommendation is decision)
        return agreeing / len(votes)

    @staticmethod
    def _action_matches_opinion(
        action: RecommendationAction, opinion: Opinion
    ) -> bool:
        mapped = RecommendationMapper._map_action(opinion.recommendation)
        return mapped is action

    @staticmethod
    def _supporting_evidence(report: CommitteeReport) -> tuple[Evidence, ...]:
        """Evidence from opinions that agree with the final action.

        For ``NEUTRAL`` → ``HOLD``, include every opinion's evidence so
        the conflict trail remains visible on the contract.
        """
        action = RecommendationMapper._map_action(report.decision.decision)
        if report.decision.decision is Decision.NEUTRAL:
            return report.evidence_used

        items: list[Evidence] = []
        for opinion in report.opinions:
            if RecommendationMapper._action_matches_opinion(action, opinion):
                items.extend(opinion.evidence)
        return tuple(items)

    @staticmethod
    def _dissenting_views(report: CommitteeReport) -> tuple[str, ...]:
        """Human-readable dissent from opinions that disagree with the action."""
        action = RecommendationMapper._map_action(report.decision.decision)
        if report.decision.decision is Decision.NEUTRAL:
            # Every member is part of the unresolved conflict.
            return tuple(
                f"{opinion.source}: {opinion.recommendation.value} — "
                f"{opinion.reasoning}"
                for opinion in report.opinions
            )

        views: list[str] = []
        for opinion in report.opinions:
            if not RecommendationMapper._action_matches_opinion(action, opinion):
                views.append(
                    f"{opinion.source}: {opinion.recommendation.value} — "
                    f"{opinion.reasoning}"
                )
        return tuple(views)

    @staticmethod
    def _rationale(report: CommitteeReport) -> str:
        """Combine decision rationale with the voting summary."""
        decision_text = report.decision.rationale.strip()
        summary = report.voting_summary.strip()
        if summary and summary not in decision_text:
            return f"{decision_text} ({summary})"
        return decision_text

    @staticmethod
    def _valuation_payload(
        report: CommitteeReport,
    ) -> tuple[MarginOfSafety | None, ValuationSummary | None]:
        """Propagate MoS / summary from the valuation opinion (no recalc)."""
        for opinion in report.opinions:
            if opinion.source == "valuation":
                return opinion.margin_of_safety, opinion.valuation_summary
        return None, None
