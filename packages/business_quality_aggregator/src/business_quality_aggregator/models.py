"""Immutable domain models for Business Quality Aggregator (FEATURE-006)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from business_quality_aggregator.exceptions import (
    BusinessQualityAggregatorValidationError,
)
from business_quality_aggregator.metadata import BusinessQualityAggregatorMetadata
from business_quality_aggregator.scoring import (
    AggregatorComponent,
    BusinessQualityAggregatorRating,
    BusinessQualityAggregatorWeights,
)

__all__ = [
    "AggregatorComponentResult",
    "BusinessQualityAggregation",
    "BusinessQualityAggregatorConfidence",
    "BusinessQualityAggregatorEvidence",
    "BusinessQualityAggregatorExplainability",
    "BusinessQualityAggregatorScore",
    "BusinessQualityAggregatorValidationSummary",
    "ConflictAdjustment",
]


@dataclass(frozen=True, slots=True)
class BusinessQualityAggregatorConfidence:
    value: float = 0.0
    basis: str = "not_assessed"

    def __post_init__(self) -> None:
        if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
            raise BusinessQualityAggregatorValidationError(
                "confidence.value must be numeric"
            )
        value = float(self.value)
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise BusinessQualityAggregatorValidationError(
                "confidence.value must be finite and in the range [0.0, 1.0]"
            )
        basis = self.basis.strip()
        if not basis:
            raise BusinessQualityAggregatorValidationError(
                "confidence.basis is required"
            )
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "basis", basis)

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "basis": self.basis}


@dataclass(frozen=True, slots=True)
class BusinessQualityAggregatorScore:
    value: float | None = None
    status: str = "not_assessed"
    scale_min: float = 0.0
    scale_max: float = 100.0

    def __post_init__(self) -> None:
        status = self.status.strip()
        if not status:
            raise BusinessQualityAggregatorValidationError("score.status is required")
        object.__setattr__(self, "status", status)
        if self.value is None:
            return
        if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
            raise BusinessQualityAggregatorValidationError(
                "score.value must be numeric or None"
            )
        value = float(self.value)
        if not math.isfinite(value):
            raise BusinessQualityAggregatorValidationError("score.value must be finite")
        if not self.scale_min <= value <= self.scale_max:
            raise BusinessQualityAggregatorValidationError(
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
class BusinessQualityAggregatorEvidence:
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
            raise BusinessQualityAggregatorValidationError("evidence.source is required")
        if not reference:
            raise BusinessQualityAggregatorValidationError(
                "evidence.reference is required"
            )
        if not isinstance(self.confidence, (int, float)) or isinstance(
            self.confidence, bool
        ):
            raise BusinessQualityAggregatorValidationError(
                "evidence.confidence must be numeric"
            )
        confidence = float(self.confidence)
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise BusinessQualityAggregatorValidationError(
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
class BusinessQualityAggregatorValidationSummary:
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
class BusinessQualityAggregatorExplainability:
    evidence: tuple[BusinessQualityAggregatorEvidence, ...] = ()
    confidence: BusinessQualityAggregatorConfidence = (
        BusinessQualityAggregatorConfidence()
    )
    assumptions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    reasoning: str = ""
    engine_weights: dict[str, float] | None = None
    data_availability: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "assumptions", tuple(self.assumptions))
        object.__setattr__(self, "limitations", tuple(self.limitations))
        object.__setattr__(self, "data_availability", tuple(self.data_availability))
        object.__setattr__(self, "reasoning", self.reasoning.strip())
        if self.engine_weights is not None:
            object.__setattr__(self, "engine_weights", dict(self.engine_weights))

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence": [item.to_dict() for item in self.evidence],
            "confidence": self.confidence.to_dict(),
            "assumptions": list(self.assumptions),
            "limitations": list(self.limitations),
            "reasoning": self.reasoning,
            "engine_weights": self.engine_weights,
            "data_availability": list(self.data_availability),
        }


@dataclass(frozen=True, slots=True)
class ConflictAdjustment:
    rule_id: str
    description: str
    penalty_points: float
    engines: tuple[str, ...]
    supporting_metrics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_id", self.rule_id.strip())
        object.__setattr__(self, "description", self.description.strip())
        object.__setattr__(self, "engines", tuple(self.engines))
        object.__setattr__(
            self, "supporting_metrics", tuple(self.supporting_metrics)
        )
        if not self.rule_id:
            raise BusinessQualityAggregatorValidationError(
                "conflict.rule_id is required"
            )
        if not math.isfinite(self.penalty_points) or self.penalty_points < 0:
            raise BusinessQualityAggregatorValidationError(
                "conflict.penalty_points must be finite and >= 0"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "penalty_points": self.penalty_points,
            "engines": list(self.engines),
            "supporting_metrics": list(self.supporting_metrics),
        }


@dataclass(frozen=True, slots=True)
class AggregatorComponentResult:
    component: AggregatorComponent
    engine_score: BusinessQualityAggregatorScore
    engine_rating: str | None
    engine_confidence: BusinessQualityAggregatorConfidence
    weight: float
    weighted_contribution: float | None
    evidence: tuple[BusinessQualityAggregatorEvidence, ...] = ()
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    data_available: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "strengths", tuple(self.strengths))
        object.__setattr__(self, "weaknesses", tuple(self.weaknesses))
        object.__setattr__(self, "risks", tuple(self.risks))
        if not math.isfinite(self.weight) or self.weight < 0:
            raise BusinessQualityAggregatorValidationError(
                "component.weight must be finite and >= 0"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component.value,
            "engine_score": self.engine_score.to_dict(),
            "engine_rating": self.engine_rating,
            "engine_confidence": self.engine_confidence.to_dict(),
            "weight": self.weight,
            "weighted_contribution": self.weighted_contribution,
            "evidence": [e.to_dict() for e in self.evidence],
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "risks": list(self.risks),
            "data_available": self.data_available,
        }


@dataclass(frozen=True, slots=True)
class BusinessQualityAggregation:
    metadata: BusinessQualityAggregatorMetadata
    validation: BusinessQualityAggregatorValidationSummary
    score: BusinessQualityAggregatorScore
    evidence: tuple[BusinessQualityAggregatorEvidence, ...]
    confidence: BusinessQualityAggregatorConfidence
    explainability: BusinessQualityAggregatorExplainability
    components: tuple[AggregatorComponentResult, ...] = ()
    conflict_adjustments: tuple[ConflictAdjustment, ...] = ()
    raw_weighted_score: float | None = None
    overall_business_quality_rating: BusinessQualityAggregatorRating | None = None
    summary: str = ""
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    investment_observations: tuple[str, ...] = ()
    recommendation: str = ""
    weights_used: BusinessQualityAggregatorWeights | None = None
    input_references: tuple[str, ...] = (
        "EconomicAnalysis",
        "ManagementAnalysis",
        "FinancialStrengthAnalysis",
        "EarningsQualityAnalysis",
        "GrowthQualityAnalysis",
    )
    research_disclaimer: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "components", tuple(self.components))
        object.__setattr__(
            self, "conflict_adjustments", tuple(self.conflict_adjustments)
        )
        object.__setattr__(self, "strengths", tuple(self.strengths))
        object.__setattr__(self, "weaknesses", tuple(self.weaknesses))
        object.__setattr__(self, "risks", tuple(self.risks))
        object.__setattr__(
            self, "investment_observations", tuple(self.investment_observations)
        )
        object.__setattr__(self, "input_references", tuple(self.input_references))
        object.__setattr__(self, "summary", self.summary.strip())
        object.__setattr__(self, "recommendation", self.recommendation.strip())
        object.__setattr__(
            self, "research_disclaimer", self.research_disclaimer.strip()
        )

    @property
    def overall_business_quality_score(self) -> float | None:
        return self.score.value

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "validation": self.validation.to_dict(),
            "score": self.score.to_dict(),
            "overall_business_quality_score": self.overall_business_quality_score,
            "overall_business_quality_rating": (
                self.overall_business_quality_rating.value
                if self.overall_business_quality_rating is not None
                else None
            ),
            "raw_weighted_score": self.raw_weighted_score,
            "evidence": [item.to_dict() for item in self.evidence],
            "confidence": self.confidence.to_dict(),
            "explainability": self.explainability.to_dict(),
            "components": [c.to_dict() for c in self.components],
            "conflict_adjustments": [c.to_dict() for c in self.conflict_adjustments],
            "summary": self.summary,
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "risks": list(self.risks),
            "investment_observations": list(self.investment_observations),
            "recommendation": self.recommendation,
            "weights_used": (
                self.weights_used.to_dict() if self.weights_used is not None else None
            ),
            "input_references": list(self.input_references),
            "research_disclaimer": self.research_disclaimer,
        }
