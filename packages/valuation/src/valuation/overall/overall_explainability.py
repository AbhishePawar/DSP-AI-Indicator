"""Explainability helpers for Overall Valuation Aggregator (research-only)."""

from __future__ import annotations

from valuation.core.explainability_engine import ExplainabilityEngine
from valuation.core.result_models import ExplainabilityRecord

__all__ = ["OverallExplainedValue", "explain_step", "explain_many"]

OverallExplainedValue = ExplainabilityRecord


def explain_step(
    *,
    name: str,
    value: float | None,
    formula: str,
    inputs: dict | None = None,
    intermediates: dict | None = None,
    confidence: str = "medium",
    notes: str = "",
    warnings: tuple[str, ...] = (),
) -> ExplainabilityRecord:
    """Build one explainability record via the shared ExplainabilityEngine."""
    return ExplainabilityEngine().single(
        name=name,
        value=value,
        formula=formula,
        inputs=inputs or {},
        intermediates=intermediates or {},
        confidence=confidence,  # type: ignore[arg-type]
        notes=notes,
        warnings=warnings,
    )


def explain_many(steps: list[dict]) -> tuple[ExplainabilityRecord, ...]:
    """Format multiple calculation steps."""
    return ExplainabilityEngine().explain(steps)
