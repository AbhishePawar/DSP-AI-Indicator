"""Explainability framework for Business Quality assessments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from business_quality.scoring import Confidence

__all__ = [
    "RESEARCH_DISCLAIMER",
    "BusinessQualityExplainability",
    "build_explainability",
]

RESEARCH_DISCLAIMER = (
    "Business Quality Framework artifacts are research structures only. "
    "They are not investment advice, buy/sell recommendations, or forecasts. "
    "F3.1 provides explainability scaffolding without analytical conclusions."
)


@dataclass(frozen=True, slots=True)
class BusinessQualityExplainability:
    """One assessment explanation with full provenance fields."""

    title: str
    description: str
    evidence: tuple[str, ...]
    reasoning: str
    confidence: Confidence
    limitations: str = ""
    references: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "evidence": list(self.evidence),
            "reasoning": self.reasoning,
            "confidence": self.confidence.value,
            "limitations": self.limitations,
            "references": list(self.references),
        }


def build_explainability(
    *,
    title: str,
    description: str,
    evidence: Sequence[str] | None = None,
    reasoning: str,
    confidence: Confidence | str = Confidence.INSUFFICIENT,
    limitations: str = "",
    references: Sequence[str] | None = None,
) -> BusinessQualityExplainability:
    """Construct an immutable explainability record."""
    conf = (
        confidence
        if isinstance(confidence, Confidence)
        else Confidence(str(confidence))
    )
    return BusinessQualityExplainability(
        title=title,
        description=description,
        evidence=tuple(evidence or ()),
        reasoning=reasoning,
        confidence=conf,
        limitations=limitations,
        references=tuple(references or ()),
    )


def explainability_from_mapping(
    payload: Mapping[str, Any],
) -> BusinessQualityExplainability:
    """Deserialize explainability from a plain mapping."""
    return build_explainability(
        title=str(payload.get("title", "")),
        description=str(payload.get("description", "")),
        evidence=tuple(payload.get("evidence") or ()),
        reasoning=str(payload.get("reasoning", "")),
        confidence=str(payload.get("confidence", Confidence.INSUFFICIENT.value)),
        limitations=str(payload.get("limitations", "")),
        references=tuple(payload.get("references") or ()),
    )
