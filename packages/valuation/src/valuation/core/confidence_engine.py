"""Reusable confidence scoring engine (research-only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from valuation.core.interfaces import ConfidenceProvider
from valuation.core.result_models import ConfidenceLevel

__all__ = ["ConfidenceDetail", "ConfidenceEngine"]


@dataclass(frozen=True, slots=True)
class ConfidenceDetail:
    """Transparent confidence score with rationale."""

    score: float
    level: ConfidenceLevel
    max_score: float
    factors: Mapping[str, float]
    explanation: str

    def to_dict(self) -> dict[str, object]:
        return {
            "score": self.score,
            "level": self.level,
            "max_score": self.max_score,
            "factors": dict(self.factors),
            "explanation": self.explanation,
        }


class ConfidenceEngine(ConfidenceProvider):
    """Score research confidence from structured factor inputs.

    Recognized factor keys (0–1 weights applied when present):
    accounting_quality, forecast_reliability, data_completeness,
    business_stability, capital_allocation, model_assumptions,
    clean_surplus_compliance, solver_accuracy.
    """

    FACTOR_WEIGHTS: Mapping[str, float] = {
        "accounting_quality": 1.0,
        "forecast_reliability": 1.0,
        "data_completeness": 1.0,
        "business_stability": 1.0,
        "capital_allocation": 1.0,
        "model_assumptions": 1.0,
        "clean_surplus_compliance": 1.0,
        "solver_accuracy": 1.0,
    }

    def score(
        self,
        factors: Mapping[str, float | int | bool | None],
    ) -> ConfidenceDetail:
        """Compute weighted confidence.

        Boolean factors map to 1.0/0.0. Numeric factors should be in [0, 1]
        (values > 1 are treated as already-scaled points and capped later).
        Missing factors contribute 0.
        """
        scored: dict[str, float] = {}
        total = 0.0
        max_score = 0.0
        for key, weight in self.FACTOR_WEIGHTS.items():
            max_score += weight
            raw = factors.get(key)
            if raw is None:
                scored[key] = 0.0
                continue
            if isinstance(raw, bool):
                val = 1.0 if raw else 0.0
            else:
                val = float(raw)
                if val > 1.0:
                    val = min(val / 100.0, 1.0) if val > 10 else min(val, 1.0)
                val = max(0.0, min(1.0, val))
            scored[key] = val * weight
            total += scored[key]

        if max_score <= 0:
            level: ConfidenceLevel = "low"
        elif total / max_score >= 0.75:
            level = "high"
        elif total / max_score >= 0.45:
            level = "medium"
        else:
            level = "low"

        explanation = (
            f"Confidence={level} (score {total:.2f}/{max_score:.2f}). "
            + ", ".join(f"{k}={v:.2f}" for k, v in scored.items())
        )
        return ConfidenceDetail(
            score=total,
            level=level,
            max_score=max_score,
            factors=scored,
            explanation=explanation,
        )
