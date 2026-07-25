"""Immutable report models for Business Quality Aggregator (F3.7)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from business_quality.business_quality_models import OverallRating
from business_quality.explainability import BusinessQualityExplainability
from business_quality.metadata import BusinessQualityMetadata
from business_quality.scoring import Confidence, Score
from business_quality.validation import BusinessQualityValidation

__all__ = [
    "BusinessQualityReport",
    "ConfidenceSummary",
    "ModuleBreakdownEntry",
    "ReportSignal",
]


@dataclass(frozen=True, slots=True)
class ReportSignal:
    """One aggregated signal (risk / positive / warning)."""

    text: str
    source: str = ""
    category: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "source": self.source,
            "category": self.category,
        }


@dataclass(frozen=True, slots=True)
class ModuleBreakdownEntry:
    """Per-module contribution snapshot for reporting (no new scores)."""

    name: str
    label: str
    rating: str | None = None
    score: float | None = None
    confidence: str | None = None
    weight: float | None = None
    present: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "rating": self.rating,
            "score": self.score,
            "confidence": self.confidence,
            "weight": self.weight,
            "present": self.present,
        }


@dataclass(frozen=True, slots=True)
class ConfidenceSummary:
    """Aggregated confidence presentation for downstream consumers."""

    overall: Confidence
    module_confidences: tuple[tuple[str, str], ...] = ()
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall.value,
            "module_confidences": [
                {"module": m, "confidence": c} for m, c in self.module_confidences
            ],
            "explanation": self.explanation,
        }


@dataclass(frozen=True, slots=True)
class BusinessQualityReport:
    """Canonical Business Quality report artifact (pure aggregation).

    UI-agnostic immutable domain model — no HTML/Markdown/PDF formatting.
    """

    metadata: BusinessQualityMetadata
    validation: BusinessQualityValidation
    executive_summary: str
    business_quality_rating: OverallRating | None
    overall_score: Score | None
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    key_risks: tuple[str, ...]
    positive_signals: tuple[str, ...]
    warning_signals: tuple[str, ...]
    confidence_summary: ConfidenceSummary
    evidence_summary: tuple[str, ...]
    module_breakdown: tuple[ModuleBreakdownEntry, ...]
    recommended_interpretation: str
    limitations: tuple[str, ...]
    explainability: tuple[BusinessQualityExplainability, ...]
    research_disclaimer: str
    source_modules: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "validation": self.validation.to_dict(),
            "executive_summary": self.executive_summary,
            "business_quality_rating": (
                self.business_quality_rating.value
                if self.business_quality_rating is not None
                else None
            ),
            "overall_score": (
                self.overall_score.to_dict() if self.overall_score is not None else None
            ),
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "key_risks": list(self.key_risks),
            "positive_signals": list(self.positive_signals),
            "warning_signals": list(self.warning_signals),
            "confidence_summary": self.confidence_summary.to_dict(),
            "evidence_summary": list(self.evidence_summary),
            "module_breakdown": [m.to_dict() for m in self.module_breakdown],
            "recommended_interpretation": self.recommended_interpretation,
            "limitations": list(self.limitations),
            "explainability": [e.to_dict() for e in self.explainability],
            "research_disclaimer": self.research_disclaimer,
            "source_modules": list(self.source_modules),
        }
