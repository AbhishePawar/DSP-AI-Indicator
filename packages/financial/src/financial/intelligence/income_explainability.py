"""Explainability records for Income Statement Intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

__all__ = [
    "RESEARCH_DISCLAIMER",
    "MetricExplanation",
    "build_explanation",
]

RESEARCH_DISCLAIMER = (
    "Income Statement Intelligence is a research analysis of reported "
    "financial statement figures. It is not investment advice, a buy/sell "
    "recommendation, or a forecast of future results. Metrics are "
    "deterministic transformations of provided inputs; missing data reduces "
    "coverage and confidence. Always verify source filings."
)

_CONFIDENCE_LEVELS = frozenset({"high", "medium", "low", "insufficient"})


@dataclass(frozen=True, slots=True)
class MetricExplanation:
    """One derived metric with full calculation transparency."""

    name: str
    formula: str
    inputs: Mapping[str, Any]
    intermediates: Mapping[str, Any]
    result: float | None
    confidence: str
    interpretation: str
    limitations: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "formula": self.formula,
            "inputs": dict(self.inputs),
            "intermediates": dict(self.intermediates),
            "result": self.result,
            "confidence": self.confidence,
            "interpretation": self.interpretation,
            "limitations": self.limitations,
        }


def build_explanation(
    *,
    name: str,
    formula: str,
    inputs: Mapping[str, Any],
    intermediates: Mapping[str, Any] | None = None,
    result: float | None,
    confidence: str = "medium",
    interpretation: str,
    limitations: str = "",
) -> MetricExplanation:
    """Construct an immutable explainability record."""
    conf = str(confidence).strip().lower()
    if conf not in _CONFIDENCE_LEVELS:
        conf = "medium"
    return MetricExplanation(
        name=name,
        formula=formula,
        inputs=dict(inputs),
        intermediates=dict(intermediates or {}),
        result=result,
        confidence=conf,
        interpretation=interpretation,
        limitations=limitations,
    )
