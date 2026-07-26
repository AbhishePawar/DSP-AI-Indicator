"""Immutable domain models for Investment Recommendation (FEATURE-007)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from investment_recommendation.exceptions import (
    InvestmentRecommendationValidationError,
)
from investment_recommendation.metadata import InvestmentRecommendationMetadata
from investment_recommendation.scoring import (
    DecisionComponent,
    DecisionWeights,
    InvestmentRecommendationAction,
)

__all__ = [
    "DecisionContribution",
    "InvestmentRecommendation",
    "InvestmentRecommendationConfidence",
    "InvestmentRecommendationEvidence",
    "InvestmentRecommendationExplainability",
    "InvestmentRecommendationScore",
    "InvestmentRecommendationValidationSummary",
    "MarginOfSafetyAssessment",
    "TriggeredRule",
]


@dataclass(frozen=True, slots=True)
class InvestmentRecommendationConfidence:
    value: float = 0.0
    basis: str = "not_assessed"

    def __post_init__(self) -> None:
        if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
            raise InvestmentRecommendationValidationError(
                "confidence.value must be numeric"
            )
        value = float(self.value)
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise InvestmentRecommendationValidationError(
                "confidence.value must be finite and in the range [0.0, 1.0]"
            )
        basis = self.basis.strip()
        if not basis:
            raise InvestmentRecommendationValidationError(
                "confidence.basis is required"
            )
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "basis", basis)

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "basis": self.basis}


@dataclass(frozen=True, slots=True)
class InvestmentRecommendationScore:
    value: float | None = None
    status: str = "not_assessed"
    scale_min: float = 0.0
    scale_max: float = 100.0

    def __post_init__(self) -> None:
        status = self.status.strip()
        if not status:
            raise InvestmentRecommendationValidationError("score.status is required")
        object.__setattr__(self, "status", status)
        if self.value is None:
            return
        if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
            raise InvestmentRecommendationValidationError(
                "score.value must be numeric or None"
            )
        value = float(self.value)
        if not math.isfinite(value):
            raise InvestmentRecommendationValidationError("score.value must be finite")
        if not self.scale_min <= value <= self.scale_max:
            raise InvestmentRecommendationValidationError(
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
class InvestmentRecommendationEvidence:
    source: str
    reference: str
    summary: str = ""
    reasoning: str = ""
    confidence: float = 0.0
    supporting_metrics: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    contributing_engines: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        source = self.source.strip()
        reference = self.reference.strip()
        if not source:
            raise InvestmentRecommendationValidationError("evidence.source is required")
        if not reference:
            raise InvestmentRecommendationValidationError(
                "evidence.reference is required"
            )
        confidence = float(self.confidence)
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise InvestmentRecommendationValidationError(
                "evidence.confidence must be finite and in [0.0, 1.0]"
            )
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "reference", reference)
        object.__setattr__(self, "summary", self.summary.strip())
        object.__setattr__(self, "reasoning", self.reasoning.strip())
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "supporting_metrics", tuple(self.supporting_metrics))
        object.__setattr__(self, "limitations", tuple(self.limitations))
        object.__setattr__(
            self, "contributing_engines", tuple(self.contributing_engines)
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
            "contributing_engines": list(self.contributing_engines),
        }


@dataclass(frozen=True, slots=True)
class InvestmentRecommendationValidationSummary:
    ok: bool
    required_inputs: tuple[str, ...] = ()
    missing_inputs: tuple[str, ...] = ()
    invalid_inputs: tuple[str, ...] = ()
    checks: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "required_inputs",
            "missing_inputs",
            "invalid_inputs",
            "checks",
            "warnings",
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
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


@dataclass(frozen=True, slots=True)
class MarginOfSafetyAssessment:
    intrinsic_value_per_share: float | None
    current_market_price: float | None
    margin_of_safety: float | None
    premium_discount: float | None
    valuation_score: float | None
    valuation_confidence: float
    classification: str
    reasoning: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "intrinsic_value_per_share": self.intrinsic_value_per_share,
            "current_market_price": self.current_market_price,
            "margin_of_safety": self.margin_of_safety,
            "premium_discount": self.premium_discount,
            "valuation_score": self.valuation_score,
            "valuation_confidence": self.valuation_confidence,
            "classification": self.classification,
            "reasoning": self.reasoning,
        }


@dataclass(frozen=True, slots=True)
class TriggeredRule:
    rule_id: str
    group: str
    description: str
    score_delta: float = 0.0
    action_cap: InvestmentRecommendationAction | None = None
    engines: tuple[str, ...] = ()
    supporting_metrics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_id", self.rule_id.strip())
        object.__setattr__(self, "group", self.group.strip())
        object.__setattr__(self, "description", self.description.strip())
        object.__setattr__(self, "engines", tuple(self.engines))
        object.__setattr__(
            self, "supporting_metrics", tuple(self.supporting_metrics)
        )
        if not self.rule_id:
            raise InvestmentRecommendationValidationError("rule.rule_id is required")
        if not math.isfinite(self.score_delta):
            raise InvestmentRecommendationValidationError(
                "rule.score_delta must be finite"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "group": self.group,
            "description": self.description,
            "score_delta": self.score_delta,
            "action_cap": (
                self.action_cap.value if self.action_cap is not None else None
            ),
            "engines": list(self.engines),
            "supporting_metrics": list(self.supporting_metrics),
        }


@dataclass(frozen=True, slots=True)
class DecisionContribution:
    component: DecisionComponent
    score: InvestmentRecommendationScore
    weight: float
    weighted_contribution: float | None
    confidence: InvestmentRecommendationConfidence
    data_available: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component.value,
            "score": self.score.to_dict(),
            "weight": self.weight,
            "weighted_contribution": self.weighted_contribution,
            "confidence": self.confidence.to_dict(),
            "data_available": self.data_available,
        }


@dataclass(frozen=True, slots=True)
class InvestmentRecommendationExplainability:
    evidence: tuple[InvestmentRecommendationEvidence, ...] = ()
    confidence: InvestmentRecommendationConfidence = (
        InvestmentRecommendationConfidence()
    )
    assumptions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    reasoning: str = ""
    engine_weights: dict[str, float] | None = None
    decision_rules_triggered: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "assumptions", tuple(self.assumptions))
        object.__setattr__(self, "limitations", tuple(self.limitations))
        object.__setattr__(
            self, "decision_rules_triggered", tuple(self.decision_rules_triggered)
        )
        object.__setattr__(self, "reasoning", self.reasoning.strip())
        if self.engine_weights is not None:
            object.__setattr__(self, "engine_weights", dict(self.engine_weights))

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence": [e.to_dict() for e in self.evidence],
            "confidence": self.confidence.to_dict(),
            "assumptions": list(self.assumptions),
            "limitations": list(self.limitations),
            "reasoning": self.reasoning,
            "engine_weights": self.engine_weights,
            "decision_rules_triggered": list(self.decision_rules_triggered),
        }


@dataclass(frozen=True, slots=True)
class InvestmentRecommendation:
    metadata: InvestmentRecommendationMetadata
    validation: InvestmentRecommendationValidationSummary
    score: InvestmentRecommendationScore
    recommendation: InvestmentRecommendationAction
    confidence: InvestmentRecommendationConfidence
    evidence: tuple[InvestmentRecommendationEvidence, ...]
    explainability: InvestmentRecommendationExplainability
    contributions: tuple[DecisionContribution, ...] = ()
    triggered_rules: tuple[TriggeredRule, ...] = ()
    margin_of_safety: MarginOfSafetyAssessment | None = None
    raw_score: float | None = None
    positive_factors: tuple[str, ...] = ()
    negative_factors: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    key_drivers: tuple[str, ...] = ()
    investment_thesis: str = ""
    decision_summary: str = ""
    recommendation_text: str = ""
    weights_used: DecisionWeights | None = None
    research_disclaimer: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "contributions", tuple(self.contributions))
        object.__setattr__(self, "triggered_rules", tuple(self.triggered_rules))
        object.__setattr__(self, "positive_factors", tuple(self.positive_factors))
        object.__setattr__(self, "negative_factors", tuple(self.negative_factors))
        object.__setattr__(self, "risks", tuple(self.risks))
        object.__setattr__(self, "key_drivers", tuple(self.key_drivers))
        object.__setattr__(self, "investment_thesis", self.investment_thesis.strip())
        object.__setattr__(self, "decision_summary", self.decision_summary.strip())
        object.__setattr__(
            self, "recommendation_text", self.recommendation_text.strip()
        )
        object.__setattr__(
            self, "research_disclaimer", self.research_disclaimer.strip()
        )

    @property
    def overall_investment_score(self) -> float | None:
        return self.score.value

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "validation": self.validation.to_dict(),
            "score": self.score.to_dict(),
            "overall_investment_score": self.overall_investment_score,
            "recommendation": self.recommendation.value,
            "confidence": self.confidence.to_dict(),
            "evidence": [e.to_dict() for e in self.evidence],
            "explainability": self.explainability.to_dict(),
            "contributions": [c.to_dict() for c in self.contributions],
            "triggered_rules": [r.to_dict() for r in self.triggered_rules],
            "margin_of_safety": (
                self.margin_of_safety.to_dict()
                if self.margin_of_safety is not None
                else None
            ),
            "raw_score": self.raw_score,
            "positive_factors": list(self.positive_factors),
            "negative_factors": list(self.negative_factors),
            "risks": list(self.risks),
            "key_drivers": list(self.key_drivers),
            "investment_thesis": self.investment_thesis,
            "decision_summary": self.decision_summary,
            "recommendation_text": self.recommendation_text,
            "weights_used": (
                self.weights_used.to_dict() if self.weights_used is not None else None
            ),
            "research_disclaimer": self.research_disclaimer,
        }
