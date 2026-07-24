"""Build a Decision Brief from committee report + recommendation."""

from __future__ import annotations

from ai_committee import CommitteeReport, Decision
from contracts import Recommendation, RecommendationAction

from decision_intelligence.models.brief import (
    DecisionBrief,
    EvidenceHighlight,
    MemberAttribution,
)

__all__ = ["build_decision_brief"]

_ACTION_TO_DECISION: dict[RecommendationAction, Decision] = {
    RecommendationAction.BUY: Decision.BUY,
    RecommendationAction.STRONG_BUY: Decision.BUY,
    RecommendationAction.HOLD: Decision.HOLD,
    RecommendationAction.SELL: Decision.SELL,
    RecommendationAction.STRONG_SELL: Decision.SELL,
}


def build_decision_brief(
    report: CommitteeReport,
    recommendation: Recommendation,
) -> DecisionBrief:
    """Synthesize an investor-facing brief from existing deliberation artifacts."""
    final = _effective_final_decision(report, recommendation)
    attribution = _attribution(report, final)
    highlights = _evidence_highlights(report, recommendation)
    assumptions = _key_assumptions(report, recommendation)
    invalidators = _invalidators(report, recommendation, attribution)
    watchlist = _watchlist(report, recommendation, attribution)
    headline = _headline(recommendation, attribution)
    summary = _executive_summary(recommendation, attribution, report)

    return DecisionBrief(
        instrument=recommendation.instrument,
        action=recommendation.action,
        conviction=recommendation.conviction,
        headline=headline,
        executive_summary=summary,
        attribution=attribution,
        evidence_highlights=highlights,
        key_assumptions=assumptions,
        invalidators=invalidators,
        monitoring_watchlist=watchlist,
        generated_at=recommendation.generated_at,
    )


def _effective_final_decision(
    report: CommitteeReport,
    recommendation: Recommendation,
) -> Decision:
    # Prefer committee decision; NEUTRAL maps like HOLD for agreement checks.
    decision = report.decision.decision
    if decision is Decision.NEUTRAL:
        return Decision.HOLD
    mapped = _ACTION_TO_DECISION.get(recommendation.action)
    return mapped if mapped is not None else decision


def _attribution(
    report: CommitteeReport,
    final: Decision,
) -> tuple[MemberAttribution, ...]:
    items: list[MemberAttribution] = []
    for vote in report.votes:
        opinion = vote.opinion
        agreed = vote.recommendation is final
        if agreed:
            role = "supporting"
        elif vote.recommendation is Decision.HOLD and final is not Decision.HOLD:
            role = "neutral"
        else:
            role = "dissenting"
        excerpt = opinion.reasoning
        if len(excerpt) > 160:
            excerpt = excerpt[:157] + "..."
        items.append(
            MemberAttribution(
                source=vote.source,
                stance=vote.recommendation.value,
                agreed_with_final=agreed,
                role=role,
                rationale_excerpt=excerpt,
            )
        )
    return tuple(items)


def _evidence_highlights(
    report: CommitteeReport,
    recommendation: Recommendation,
) -> tuple[EvidenceHighlight, ...]:
    supporting = recommendation.supporting_evidence
    highlights: list[EvidenceHighlight] = []

    # Prefer MoS / valuation evidence as strongest when present.
    strong = None
    for item in supporting:
        ref = (item.reference or "").lower()
        claim = item.claim.lower()
        if "margin_of_safety" in ref or "mos" in ref or "margin of safety" in claim:
            strong = item
            break
    if strong is None and supporting:
        strong = max(
            supporting,
            key=lambda e: (e.weight is not None, e.weight or 0.0),
        )
    if strong is not None:
        highlights.append(
            EvidenceHighlight.from_evidence(
                strong,
                strength="strong",
                rank_reason="Highest-priority supporting evidence for the final action.",
            )
        )

    # Weakest: dissenting opinion evidence or lowest-weight supporting leftovers.
    weak = None
    for opinion in report.opinions:
        if opinion.recommendation.value != recommendation.action.value:
            if opinion.evidence:
                weak = opinion.evidence[0]
                reason = (
                    f"Evidence from dissenting {opinion.source} "
                    f"({opinion.recommendation.value})."
                )
                break
    if weak is None:
        leftovers = [e for e in supporting if strong is None or e is not strong]
        if leftovers:
            weak = min(
                leftovers,
                key=lambda e: (e.weight is not None, e.weight or 0.0),
            )
            reason = "Lowest-weight supporting evidence item."
        else:
            reason = ""
    if weak is not None and reason:
        # Avoid duplicating the same item as both strong and weak.
        if strong is None or weak.claim != strong.claim:
            highlights.append(
                EvidenceHighlight.from_evidence(
                    weak,
                    strength="weak",
                    rank_reason=reason,
                )
            )

    if not highlights and report.evidence_used:
        first = report.evidence_used[0]
        highlights.append(
            EvidenceHighlight.from_evidence(
                first,
                strength="strong",
                rank_reason="Only available deliberation evidence.",
            )
        )
    return tuple(highlights)


def _key_assumptions(
    report: CommitteeReport,
    recommendation: Recommendation,
) -> tuple[str, ...]:
    assumptions: list[str] = []
    mos = recommendation.margin_of_safety
    if mos is not None and mos.available:
        assumptions.append(
            "Equity market capitalization used for Margin of Safety remains representative."
        )
        assumptions.append(
            "Intrinsic-value mid estimate remains a valid central reference."
        )
    elif any(v.source == "valuation" for v in report.votes):
        assumptions.append(
            "Valuation stance does not rely on an available Margin of Safety cushion."
        )

    sources = {v.source for v in report.votes}
    if "economic" in sources:
        assumptions.append(
            "Current macroeconomic regime classification remains relevant."
        )
    if "fundamental" in sources:
        assumptions.append(
            "Latest fundamental statements remain reflective of business quality."
        )
    if "technical" in sources:
        assumptions.append(
            "Recent price-indicator regime remains informative for near-term bias."
        )
    if not assumptions:
        assumptions.append(
            "Committee member stances remain stable until new evidence arrives."
        )
    return tuple(assumptions)


def _invalidators(
    report: CommitteeReport,
    recommendation: Recommendation,
    attribution: tuple[MemberAttribution, ...],
) -> tuple[str, ...]:
    items: list[str] = []
    mos = recommendation.margin_of_safety
    if mos is not None and mos.available:
        items.append(
            "Margin of Safety compresses below the valuation member's actionable cushion."
        )
    if any(a.source == "economic" for a in attribution):
        items.append(
            "Macro member flips stance on a material regime change."
        )
    if any(a.source == "fundamental" for a in attribution):
        items.append(
            "Fundamental signal majority reverses on updated statements."
        )
    dissenters = [a for a in attribution if a.role == "dissenting"]
    if dissenters:
        names = ", ".join(a.source for a in dissenters)
        items.append(
            f"Dissenting member(s) ({names}) gain plurality support."
        )
    if recommendation.action is RecommendationAction.HOLD or (
        report.decision.decision is Decision.NEUTRAL
    ):
        items.append(
            "A clear majority forms for BUY or SELL, ending the unresolved conflict."
        )
    if not items:
        items.append(
            "A change in committee plurality would reopen the recommendation."
        )
    return tuple(items)


def _watchlist(
    report: CommitteeReport,
    recommendation: Recommendation,
    attribution: tuple[MemberAttribution, ...],
) -> tuple[str, ...]:
    items: list[str] = []
    mos = recommendation.margin_of_safety
    if mos is not None and mos.available:
        items.append("Track Margin of Safety vs market capitalization updates.")
    if any(a.source == "economic" for a in attribution):
        items.append("Monitor macro regime indicators (growth, inflation, liquidity).")
    if any(a.source == "fundamental" for a in attribution):
        items.append("Watch next earnings / statement release for metric confirmation.")
    if any(a.source == "technical" for a in attribution):
        items.append("Watch technical regime / trend confirmation among indicators.")
    soft = [a for a in attribution if a.role == "neutral"]
    if soft:
        items.append(
            "Revisit soft-dissent members for confirmation before sizing up."
        )
    if not items:
        items.append("Re-run deliberation when material new evidence arrives.")
    return tuple(items)


def _headline(
    recommendation: Recommendation,
    attribution: tuple[MemberAttribution, ...],
) -> str:
    symbol = recommendation.instrument.symbol
    action = recommendation.action.value.upper().replace("_", " ")
    supporting = [a.source for a in attribution if a.role == "supporting"]
    dissenting = [a.source for a in attribution if a.role == "dissenting"]
    if supporting and not dissenting:
        drivers = ", ".join(supporting)
        return f"{action} {symbol} — committee aligned ({drivers})."
    if supporting and dissenting:
        return (
            f"{action} {symbol} — supported by {', '.join(supporting)}; "
            f"dissent from {', '.join(dissenting)}."
        )
    return f"{action} {symbol} — see deliberation summary."


def _executive_summary(
    recommendation: Recommendation,
    attribution: tuple[MemberAttribution, ...],
    report: CommitteeReport,
) -> str:
    action = recommendation.action.value
    conviction = recommendation.conviction
    supporting = [a for a in attribution if a.role == "supporting"]
    dissenting = [a for a in attribution if a.role == "dissenting"]
    neutral = [a for a in attribution if a.role == "neutral"]
    parts = [
        f"DSP recommends {action} with conviction {conviction:.2f}.",
        f"Voting summary: {report.voting_summary}.",
    ]
    if supporting:
        parts.append(
            "Supporting members: "
            + ", ".join(f"{a.source} ({a.stance})" for a in supporting)
            + "."
        )
    if dissenting:
        parts.append(
            "Dissenting members: "
            + ", ".join(f"{a.source} ({a.stance})" for a in dissenting)
            + "."
        )
    if neutral:
        parts.append(
            "Non-opposing HOLD stances: "
            + ", ".join(a.source for a in neutral)
            + "."
        )
    mos = recommendation.margin_of_safety
    if mos is not None and mos.available and mos.ratio is not None:
        parts.append(f"Available Margin of Safety is {mos.ratio:.2%}.")
    elif mos is not None and not mos.available:
        parts.append("Margin of Safety was unavailable for this recommendation.")
    summary = recommendation.valuation_summary
    if summary is not None and summary.intrinsic_mid is not None:
        parts.append(
            f"Intrinsic mid estimate is {summary.intrinsic_mid:.2f} "
            f"{summary.currency}."
        )
    return " ".join(parts)
