"""Immutable domain models for Growth Quality Intelligence (FEATURE-005)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from growth_quality.exceptions import GrowthQualityValidationError
from growth_quality.metadata import GrowthQualityMetadata
from growth_quality.scoring import (
    GrowthQualityDimension,
    GrowthQualityRating,
    GrowthQualityWeights,
)

__all__ = [
    "GrowthQualityAnalysis",
    "GrowthQualityComponentScore",
    "GrowthQualityConfidence",
    "GrowthQualityEvidence",
    "GrowthQualityExplainability",
    "GrowthQualityScore",
    "GrowthQualityValidationSummary",
]


@dataclass(frozen=True, slots=True)
class GrowthQualityConfidence:
    value: float = 0.0
    basis: str = "not_assessed"

    def __post_init__(self) -> None:
        if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
            raise GrowthQualityValidationError("confidence.value must be numeric")
        value = float(self.value)
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise GrowthQualityValidationError(
                "confidence.value must be finite and in the range [0.0, 1.0]"
            )
        basis = self.basis.strip()
        if not basis:
            raise GrowthQualityValidationError("confidence.basis is required")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "basis", basis)

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "basis": self.basis}


@dataclass(frozen=True, slots=True)
class GrowthQualityScore:
    value: float | None = None
    status: str = "not_assessed"
    scale_min: float = 0.0
    scale_max: float = 100.0

    def __post_init__(self) -> None:
        status = self.status.strip()
        if not status:
            raise GrowthQualityValidationError("score.status is required")
        object.__setattr__(self, "status", status)
        if self.value is None:
            return
        if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
            raise GrowthQualityValidationError("score.value must be numeric or None")
        value = float(self.value)
        if not math.isfinite(value):
            raise GrowthQualityValidationError("score.value must be finite")
        if not self.scale_min <= value <= self.scale_max:
            raise GrowthQualityValidationError(
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
class GrowthQualityEvidence:
    source: str
    reference: str
    summary: str = ""
    reasoning: str = ""
    confidence: float = 0.0
    supporting_metrics: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        source = self.source.strip()
        reference = self.reference.strip()
        if not source:
            raise GrowthQualityValidationError("evidence.source is required")
        if not reference:
            raise GrowthQualityValidationError("evidence.reference is required")
        if not isinstance(self.confidence, (int, float)) or isinstance(
            self.confidence, bool
        ):
            raise GrowthQualityValidationError("evidence.confidence must be numeric")
        confidence = float(self.confidence)
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise GrowthQualityValidationError(
                "evidence.confidence must be finite and in [0.0, 1.0]"
            )
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "reference", reference)
        object.__setattr__(self, "summary", self.summary.strip())
        object.__setattr__(self, "reasoning", self.reasoning.strip())
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "supporting_metrics", tuple(self.supporting_metrics))
        object.__setattr__(self, "limitations", tuple(self.limitations))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "reference": self.reference,
            "summary": self.summary,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "supporting_metrics": list(self.supporting_metrics),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class GrowthQualityValidationSummary:
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
class GrowthQualityExplainability:
    evidence: tuple[GrowthQualityEvidence, ...] = ()
    confidence: GrowthQualityConfidence = GrowthQualityConfidence()
    assumptions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    reasoning: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "assumptions", tuple(self.assumptions))
        object.__setattr__(self, "limitations", tuple(self.limitations))
        object.__setattr__(self, "reasoning", self.reasoning.strip())

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence": [item.to_dict() for item in self.evidence],
            "confidence": self.confidence.to_dict(),
            "assumptions": list(self.assumptions),
            "limitations": list(self.limitations),
            "reasoning": self.reasoning,
        }


@dataclass(frozen=True, slots=True)
class GrowthQualityComponentScore:
    dimension: GrowthQualityDimension
    score: GrowthQualityScore
    confidence: GrowthQualityConfidence
    evidence: tuple[GrowthQualityEvidence, ...]
    reasoning: str
    positive_factors: tuple[str, ...] = ()
    negative_factors: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    weight: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "positive_factors", tuple(self.positive_factors))
        object.__setattr__(self, "negative_factors", tuple(self.negative_factors))
        object.__setattr__(self, "risks", tuple(self.risks))
        object.__setattr__(self, "reasoning", self.reasoning.strip())
        if not math.isfinite(self.weight) or self.weight < 0:
            raise GrowthQualityValidationError(
                "component.weight must be finite and >= 0"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "score": self.score.to_dict(),
            "confidence": self.confidence.to_dict(),
            "evidence": [e.to_dict() for e in self.evidence],
            "reasoning": self.reasoning,
            "positive_factors": list(self.positive_factors),
            "negative_factors": list(self.negative_factors),
            "risks": list(self.risks),
            "weight": self.weight,
        }


@dataclass(frozen=True, slots=True)
class GrowthQualityAnalysis:
    metadata: GrowthQualityMetadata
    validation: GrowthQualityValidationSummary
    score: GrowthQualityScore
    evidence: tuple[GrowthQualityEvidence, ...]
    confidence: GrowthQualityConfidence
    explainability: GrowthQualityExplainability
    components: tuple[GrowthQualityComponentScore, ...] = ()
    overall_growth_rating: GrowthQualityRating | None = None
    summary: str = ""
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    recommendation: str = ""
    weights_used: GrowthQualityWeights | None = None
    input_references: tuple[str, ...] = (
        "FinancialAnalysis",
        "BusinessQualityAnalysis",
    )
    research_disclaimer: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "components", tuple(self.components))
        object.__setattr__(self, "strengths", tuple(self.strengths))
        object.__setattr__(self, "weaknesses", tuple(self.weaknesses))
        object.__setattr__(self, "risks", tuple(self.risks))
        object.__setattr__(self, "input_references", tuple(self.input_references))
        object.__setattr__(self, "summary", self.summary.strip())
        object.__setattr__(self, "recommendation", self.recommendation.strip())
        object.__setattr__(self, "research_disclaimer", self.research_disclaimer.strip())

    @property
    def overall_growth_score(self) -> float | None:
        return self.score.value

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "validation": self.validation.to_dict(),
            "score": self.score.to_dict(),
            "overall_growth_score": self.overall_growth_score,
            "overall_growth_rating": (
                self.overall_growth_rating.value
                if self.overall_growth_rating is not None
                else None
            ),
            "evidence": [item.to_dict() for item in self.evidence],
            "confidence": self.confidence.to_dict(),
            "explainability": self.explainability.to_dict(),
            "components": [c.to_dict() for c in self.components],
            "summary": self.summary,
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "risks": list(self.risks),
            "recommendation": self.recommendation,
            "weights_used": (
                self.weights_used.to_dict() if self.weights_used is not None else None
            ),
            "input_references": list(self.input_references),
            "research_disclaimer": self.research_disclaimer,
        }
