"""Immutable domain models for Investment Committee (FEATURE-008)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from investment_committee.exceptions import InvestmentCommitteeValidationError
from investment_committee.metadata import InvestmentCommitteeMetadata
from investment_committee.scoring import CommitteeDecision, ReviewerRole

__all__ = [
    "CommitteeConsensus",
    "CommitteeEvidence",
    "CommitteeExplainability",
    "CommitteeScore",
    "CommitteeValidationSummary",
    "InvestmentCommitteeConfidence",
    "InvestmentCommitteeResult",
    "ReviewerOpinion",
]


@dataclass(frozen=True, slots=True)
class InvestmentCommitteeConfidence:
    value: float = 0.0
    basis: str = "not_assessed"

    def __post_init__(self) -> None:
        if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
            raise InvestmentCommitteeValidationError("confidence.value must be numeric")
        value = float(self.value)
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise InvestmentCommitteeValidationError(
                "confidence.value must be finite and in [0.0, 1.0]"
            )
        basis = self.basis.strip()
        if not basis:
            raise InvestmentCommitteeValidationError("confidence.basis is required")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "basis", basis)

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "basis": self.basis}


@dataclass(frozen=True, slots=True)
class CommitteeScore:
    value: float | None = None
    status: str = "not_assessed"
    scale_min: float = 0.0
    scale_max: float = 100.0

    def __post_init__(self) -> None:
        status = self.status.strip()
        if not status:
            raise InvestmentCommitteeValidationError("score.status is required")
        object.__setattr__(self, "status", status)
        if self.value is None:
            return
        value = float(self.value)
        if not math.isfinite(value):
            raise InvestmentCommitteeValidationError("score.value must be finite")
        if not self.scale_min <= value <= self.scale_max:
            raise InvestmentCommitteeValidationError(
                f"score.value must be in [{self.scale_min}, {self.scale_max}]"
            )
        object.__setattr__(self, "value", value)
        if status == "not_assessed":
            object.__setattr__(self, "status", "assessed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "status": self.status,
            "scale_min": self.scale_min,
            "scale_max": self.scale_max,
        }


@dataclass(frozen=True, slots=True)
class CommitteeEvidence:
    source: str
    reference: str
    summary: str = ""
    reasoning: str = ""
    confidence: float = 0.0
    supporting_metrics: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    contributing_reviewers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source.strip() or not self.reference.strip():
            raise InvestmentCommitteeValidationError(
                "evidence.source and evidence.reference are required"
            )
        confidence = float(self.confidence)
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise InvestmentCommitteeValidationError(
                "evidence.confidence must be in [0.0, 1.0]"
            )
        object.__setattr__(self, "source", self.source.strip())
        object.__setattr__(self, "reference", self.reference.strip())
        object.__setattr__(self, "summary", self.summary.strip())
        object.__setattr__(self, "reasoning", self.reasoning.strip())
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "supporting_metrics", tuple(self.supporting_metrics))
        object.__setattr__(self, "limitations", tuple(self.limitations))
        object.__setattr__(
            self, "contributing_reviewers", tuple(self.contributing_reviewers)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "reference": self.reference,
            "summary": self.summary,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "supporting_metrics": list(self.supporting_metrics),
            "limitations": list(self.limitations),
            "contributing_reviewers": list(self.contributing_reviewers),
        }


@dataclass(frozen=True, slots=True)
class CommitteeValidationSummary:
    ok: bool
    required_inputs: tuple[str, ...] = ()
    missing_inputs: tuple[str, ...] = ()
    invalid_inputs: tuple[str, ...] = ()
    checks: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "required_inputs",
            "missing_inputs",
            "invalid_inputs",
            "checks",
            "errors",
        ):
            object.__setattr__(self, name, tuple(getattr(self, name)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "required_inputs": list(self.required_inputs),
            "missing_inputs": list(self.missing_inputs),
            "invalid_inputs": list(self.invalid_inputs),
            "checks": list(self.checks),
            "errors": list(self.errors),
        }


@dataclass(frozen=True, slots=True)
class ReviewerOpinion:
    role: ReviewerRole
    opinion: CommitteeDecision
    score: CommitteeScore
    confidence: InvestmentCommitteeConfidence
    evidence: tuple[CommitteeEvidence, ...] = ()
    supporting_factors: tuple[str, ...] = ()
    concerns: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    reasoning: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "supporting_factors", tuple(self.supporting_factors))
        object.__setattr__(self, "concerns", tuple(self.concerns))
        object.__setattr__(self, "limitations", tuple(self.limitations))
        object.__setattr__(self, "reasoning", self.reasoning.strip())

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role.value,
            "opinion": self.opinion.value,
            "score": self.score.to_dict(),
            "confidence": self.confidence.to_dict(),
            "evidence": [e.to_dict() for e in self.evidence],
            "supporting_factors": list(self.supporting_factors),
            "concerns": list(self.concerns),
            "limitations": list(self.limitations),
            "reasoning": self.reasoning,
        }


@dataclass(frozen=True, slots=True)
class CommitteeConsensus:
    decision: CommitteeDecision
    agreement_score: float
    disagreement_summary: str
    minority_opinions: tuple[str, ...]
    consensus_confidence: InvestmentCommitteeConfidence
    consensus_method: str
    escalation_flags: tuple[str, ...]
    weighted_rank: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.agreement_score) or not 0.0 <= self.agreement_score <= 1.0:
            raise InvestmentCommitteeValidationError(
                "agreement_score must be in [0.0, 1.0]"
            )
        object.__setattr__(self, "minority_opinions", tuple(self.minority_opinions))
        object.__setattr__(self, "escalation_flags", tuple(self.escalation_flags))
        object.__setattr__(
            self, "disagreement_summary", self.disagreement_summary.strip()
        )
        object.__setattr__(self, "consensus_method", self.consensus_method.strip())

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "agreement_score": self.agreement_score,
            "disagreement_summary": self.disagreement_summary,
            "minority_opinions": list(self.minority_opinions),
            "consensus_confidence": self.consensus_confidence.to_dict(),
            "consensus_method": self.consensus_method,
            "escalation_flags": list(self.escalation_flags),
            "weighted_rank": self.weighted_rank,
        }


@dataclass(frozen=True, slots=True)
class CommitteeExplainability:
    evidence: tuple[CommitteeEvidence, ...] = ()
    confidence: InvestmentCommitteeConfidence = InvestmentCommitteeConfidence()
    assumptions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    reasoning: str = ""
    reviewer_contributions: tuple[str, ...] = ()
    conflicting_opinions: tuple[str, ...] = ()
    consensus_method: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "assumptions", tuple(self.assumptions))
        object.__setattr__(self, "limitations", tuple(self.limitations))
        object.__setattr__(
            self, "reviewer_contributions", tuple(self.reviewer_contributions)
        )
        object.__setattr__(
            self, "conflicting_opinions", tuple(self.conflicting_opinions)
        )
        object.__setattr__(self, "reasoning", self.reasoning.strip())
        object.__setattr__(self, "consensus_method", self.consensus_method.strip())

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence": [e.to_dict() for e in self.evidence],
            "confidence": self.confidence.to_dict(),
            "assumptions": list(self.assumptions),
            "limitations": list(self.limitations),
            "reasoning": self.reasoning,
            "reviewer_contributions": list(self.reviewer_contributions),
            "conflicting_opinions": list(self.conflicting_opinions),
            "consensus_method": self.consensus_method,
        }


@dataclass(frozen=True, slots=True)
class InvestmentCommitteeResult:
    metadata: InvestmentCommitteeMetadata
    validation: CommitteeValidationSummary
    reviewers: tuple[ReviewerOpinion, ...]
    consensus: CommitteeConsensus
    score: CommitteeScore
    decision: CommitteeDecision
    confidence: InvestmentCommitteeConfidence
    evidence: tuple[CommitteeEvidence, ...]
    explainability: CommitteeExplainability
    final_investment_thesis: str = ""
    decision_summary: str = ""
    research_disclaimer: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "reviewers", tuple(self.reviewers))
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(
            self, "final_investment_thesis", self.final_investment_thesis.strip()
        )
        object.__setattr__(self, "decision_summary", self.decision_summary.strip())
        object.__setattr__(
            self, "research_disclaimer", self.research_disclaimer.strip()
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "validation": self.validation.to_dict(),
            "reviewers": [r.to_dict() for r in self.reviewers],
            "consensus": self.consensus.to_dict(),
            "score": self.score.to_dict(),
            "decision": self.decision.value,
            "confidence": self.confidence.to_dict(),
            "evidence": [e.to_dict() for e in self.evidence],
            "explainability": self.explainability.to_dict(),
            "final_investment_thesis": self.final_investment_thesis,
            "decision_summary": self.decision_summary,
            "research_disclaimer": self.research_disclaimer,
        }
