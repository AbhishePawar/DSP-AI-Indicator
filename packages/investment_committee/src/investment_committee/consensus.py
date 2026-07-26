"""Deterministic consensus aggregation for Investment Committee."""

from __future__ import annotations

from investment_committee.models import (
    CommitteeConsensus,
    InvestmentCommitteeConfidence,
    ReviewerOpinion,
)
from investment_committee.scoring import (
    ACTION_RANK,
    CommitteeDecision,
    ReviewerRole,
    decision_from_rank,
    rank_of,
)
from investment_committee.signals import CommitteeSignals

__all__ = ["build_consensus"]

_CONSENSUS_METHOD = (
    "confidence_weighted_rank_mean_with_risk_veto_and_agreement_score"
)


def build_consensus(
    reviewers: tuple[ReviewerOpinion, ...],
    signals: CommitteeSignals,
) -> CommitteeConsensus:
    ranks: list[float] = []
    weights: list[float] = []
    for reviewer in reviewers:
        if reviewer.score.value is None:
            continue
        ranks.append(float(rank_of(reviewer.opinion)))
        weights.append(max(0.05, reviewer.confidence.value))

    if not ranks:
        return CommitteeConsensus(
            decision=CommitteeDecision.HOLD,
            agreement_score=0.0,
            disagreement_summary="No scored reviewer opinions available.",
            minority_opinions=(),
            consensus_confidence=InvestmentCommitteeConfidence(
                value=0.0, basis="insufficient_reviewers"
            ),
            consensus_method=_CONSENSUS_METHOD,
            escalation_flags=("insufficient_reviewer_scores",),
            weighted_rank=3.0,
        )

    total_w = sum(weights)
    weighted_rank = sum(r * w for r, w in zip(ranks, weights, strict=True)) / total_w
    decision = decision_from_rank(weighted_rank)

    # Risk officer soft veto: if risk is strongly bearish, cap bullish consensus
    risk = next(
        (r for r in reviewers if r.role is ReviewerRole.RISK_OFFICER), None
    )
    escalation: list[str] = []
    if risk is not None and rank_of(risk.opinion) <= ACTION_RANK[CommitteeDecision.REDUCE]:
        if ACTION_RANK[decision] >= ACTION_RANK[CommitteeDecision.BUY]:
            decision = CommitteeDecision.ACCUMULATE
            escalation.append("risk_officer_soft_veto_cap_buy")
        if rank_of(risk.opinion) <= ACTION_RANK[CommitteeDecision.SELL]:
            if ACTION_RANK[decision] >= ACTION_RANK[CommitteeDecision.ACCUMULATE]:
                decision = CommitteeDecision.HOLD
                escalation.append("risk_officer_soft_veto_cap_accumulate")

    # Great business / expensive — escalate disagreement narrative
    if (
        signals.business_quality is not None
        and signals.business_quality >= 70.0
        and signals.mos_ratio is not None
        and signals.mos_ratio < 0
    ):
        escalation.append("great_business_expensive_valuation")

    majority_rank = ACTION_RANK[decision]
    minority: list[str] = []
    for reviewer in reviewers:
        if abs(rank_of(reviewer.opinion) - majority_rank) >= 2:
            minority.append(
                f"{reviewer.role.value}={reviewer.opinion.value} "
                f"(score={reviewer.score.value})"
            )

    # Agreement: fraction within 1 rank of consensus
    agree = sum(
        1 for reviewer in reviewers if abs(rank_of(reviewer.opinion) - majority_rank) <= 1
    )
    agreement = agree / len(reviewers) if reviewers else 0.0

    # Dispersion penalty
    mean_r = sum(ranks) / len(ranks)
    variance = sum((r - mean_r) ** 2 for r in ranks) / len(ranks)
    dispersion = variance ** 0.5
    agreement = max(0.0, min(1.0, agreement * (1.0 - min(0.4, dispersion / 6.0))))

    mean_conf = sum(r.confidence.value for r in reviewers) / len(reviewers)
    consensus_conf = round(mean_conf * (0.55 + 0.45 * agreement), 4)

    if agreement < 0.5:
        escalation.append("low_agreement")
        disagreement = (
            f"Low agreement ({agreement:.0%}). Minority views: "
            + (", ".join(minority) if minority else "none enumerated")
            + "."
        )
    elif minority:
        disagreement = (
            "Moderate disagreement. Minority opinions: " + "; ".join(minority) + "."
        )
    else:
        disagreement = "Reviewers are broadly aligned with the consensus decision."

    if consensus_conf < 0.4:
        escalation.append("low_consensus_confidence")

    return CommitteeConsensus(
        decision=decision,
        agreement_score=round(agreement, 4),
        disagreement_summary=disagreement,
        minority_opinions=tuple(minority),
        consensus_confidence=InvestmentCommitteeConfidence(
            value=consensus_conf, basis="mean_reviewer_confidence_x_agreement"
        ),
        consensus_method=_CONSENSUS_METHOD,
        escalation_flags=tuple(dict.fromkeys(escalation)),
        weighted_rank=round(weighted_rank, 4),
    )
