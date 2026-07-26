"""Explainability builders for Investment Committee."""

from __future__ import annotations

from investment_committee.metadata import InvestmentCommitteeMetadata
from investment_committee.models import (
    CommitteeConsensus,
    CommitteeEvidence,
    CommitteeExplainability,
    InvestmentCommitteeConfidence,
    ReviewerOpinion,
)
from investment_committee.scoring import CommitteeDecision

__all__ = [
    "RESEARCH_DISCLAIMER",
    "build_explainability",
    "build_summary",
    "build_thesis",
]

RESEARCH_DISCLAIMER = (
    "Investment Committee produces research-only, deterministic multi-reviewer "
    "consensus from public domain and recommendation engines. It is not an LLM, "
    "not machine learning, not AI Committee G-era frozen package output, and not "
    "investment advice."
)


def build_summary(
    decision: CommitteeDecision,
    consensus: CommitteeConsensus,
    reviewers: tuple[ReviewerOpinion, ...],
) -> str:
    return (
        f"Committee decision is {decision.value.replace('_', ' ')} "
        f"(agreement {consensus.agreement_score:.0%}, "
        f"weighted_rank={consensus.weighted_rank:.2f}) across "
        f"{len(reviewers)} reviewers. {consensus.disagreement_summary}"
    )


def build_thesis(
    decision: CommitteeDecision,
    consensus: CommitteeConsensus,
    reviewers: tuple[ReviewerOpinion, ...],
) -> str:
    parts = [
        f"{r.role.value}→{r.opinion.value}({r.score.value})" for r in reviewers
    ]
    flags = (
        f" Escalation: {', '.join(consensus.escalation_flags)}."
        if consensus.escalation_flags
        else ""
    )
    return (
        f"Thesis ({decision.value}): confidence-weighted consensus of independent "
        f"deterministic reviewers [{'; '.join(parts)}]. "
        f"Method={consensus.consensus_method}.{flags}"
    )


def build_explainability(
    metadata: InvestmentCommitteeMetadata,
    reviewers: tuple[ReviewerOpinion, ...],
    consensus: CommitteeConsensus,
    decision: CommitteeDecision,
) -> CommitteeExplainability:
    evidence: list[CommitteeEvidence] = []
    contributions: list[str] = []
    for reviewer in reviewers:
        evidence.extend(reviewer.evidence)
        contributions.append(
            f"{reviewer.role.value}: opinion={reviewer.opinion.value}, "
            f"score={reviewer.score.value}, confidence={reviewer.confidence.value}"
        )
    evidence.append(
        CommitteeEvidence(
            source="ConsensusEngine",
            reference="confidence_weighted_rank_mean",
            summary=f"Consensus decision={decision.value}",
            reasoning=consensus.disagreement_summary,
            confidence=consensus.consensus_confidence.value,
            supporting_metrics=(
                f"agreement={consensus.agreement_score}",
                f"weighted_rank={consensus.weighted_rank}",
                f"escalation={list(consensus.escalation_flags)}",
            ),
            limitations=("Consensus is rule-based, not probabilistic AI.",),
            contributing_reviewers=tuple(r.role.value for r in reviewers),
        )
    )
    return CommitteeExplainability(
        evidence=tuple(evidence),
        confidence=consensus.consensus_confidence,
        assumptions=(
            "Public InvestmentRecommendation and domain analyses are accepted inputs.",
            "No LLM / ML in this package.",
            f"Framework version: {metadata.framework_version}.",
        ),
        limitations=(
            "Distinct from frozen G-era ai_committee.InvestmentCommittee.",
            "Research-only multi-agent deliberation proxy.",
            "Platform / API / frontend composition deferred.",
        ),
        reasoning=build_summary(decision, consensus, reviewers),
        reviewer_contributions=tuple(contributions),
        conflicting_opinions=consensus.minority_opinions,
        consensus_method=consensus.consensus_method,
    )
