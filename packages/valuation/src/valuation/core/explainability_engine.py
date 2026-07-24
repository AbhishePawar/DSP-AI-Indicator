"""Reusable explainability formatter for valuation engines."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from valuation.core.errors import ExplainabilityError
from valuation.core.interfaces import ExplainabilityProvider
from valuation.core.metadata import RESEARCH_DISCLAIMER
from valuation.core.result_models import ConfidenceLevel, ExplainabilityRecord

__all__ = ["ExplainabilityEngine"]


class ExplainabilityEngine(ExplainabilityProvider):
    """Format calculation steps into :class:`ExplainabilityRecord` tuples.

    Future models should supply calculation steps only; this engine
    attaches confidence notes and the research disclaimer.
    """

    def explain(
        self,
        steps: Sequence[Mapping[str, Any]],
        *,
        default_confidence: ConfidenceLevel = "medium",
        attach_disclaimer: bool = True,
    ) -> tuple[ExplainabilityRecord, ...]:
        """Convert step mappings into immutable explainability records.

        Each step may include: name, value, formula, inputs, intermediates,
        confidence, notes, warnings.
        """
        records: list[ExplainabilityRecord] = []
        for i, step in enumerate(steps):
            name = str(step.get("name") or "").strip()
            formula = str(step.get("formula") or "").strip()
            if not name:
                raise ExplainabilityError(f"step[{i}] missing name")
            if not formula:
                raise ExplainabilityError(f"step[{i}] missing formula")
            conf = str(step.get("confidence") or default_confidence)
            if conf not in {"high", "medium", "low"}:
                raise ExplainabilityError(f"step[{i}] invalid confidence {conf!r}")
            notes = str(step.get("notes") or "")
            if attach_disclaimer and RESEARCH_DISCLAIMER not in notes:
                notes = (notes + " " if notes else "") + RESEARCH_DISCLAIMER
            warnings = step.get("warnings") or ()
            if isinstance(warnings, str):
                warnings = (warnings,)
            value = step.get("value")
            records.append(
                ExplainabilityRecord(
                    name=name,
                    value=None if value is None else float(value),
                    formula=formula,
                    inputs=dict(step.get("inputs") or {}),
                    intermediates=dict(step.get("intermediates") or {}),
                    confidence=conf,  # type: ignore[arg-type]
                    notes=notes.strip(),
                    warnings=tuple(warnings),
                )
            )
        return tuple(records)

    def single(
        self,
        *,
        name: str,
        value: float | None,
        formula: str,
        inputs: Mapping[str, Any] | None = None,
        intermediates: Mapping[str, Any] | None = None,
        confidence: ConfidenceLevel = "medium",
        notes: str = "",
        warnings: Sequence[str] = (),
    ) -> ExplainabilityRecord:
        """Build one explainability record."""
        records = self.explain(
            [
                {
                    "name": name,
                    "value": value,
                    "formula": formula,
                    "inputs": dict(inputs or {}),
                    "intermediates": dict(intermediates or {}),
                    "confidence": confidence,
                    "notes": notes,
                    "warnings": tuple(warnings),
                }
            ]
        )
        return records[0]
