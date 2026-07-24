"""Explainability primitives for Reverse DCF (research-only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from core.exceptions import ValidationError

__all__ = ["ReverseExplainedValue", "ConfidenceBand"]

ConfidenceBand = str  # "high" | "medium" | "low"


@dataclass(frozen=True, slots=True)
class ReverseExplainedValue:
    """One reverse-DCF field with full explainability trail."""

    name: str
    value: float | None
    formula: str
    inputs: Mapping[str, float | int | str | bool | None]
    intermediates: Mapping[str, float | int | str | bool | None]
    confidence: ConfidenceBand
    notes: str = ""
    convergence_notes: str = ""

    def __post_init__(self) -> None:
        name = self.name.strip()
        formula = self.formula.strip()
        if not name:
            raise ValidationError("ReverseExplainedValue.name must not be empty")
        if not formula:
            raise ValidationError("ReverseExplainedValue.formula must not be empty")
        if self.confidence not in {"high", "medium", "low"}:
            raise ValidationError(f"invalid confidence: {self.confidence!r}")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "formula", formula)
        object.__setattr__(self, "notes", self.notes.strip())
        object.__setattr__(self, "convergence_notes", self.convergence_notes.strip())
        object.__setattr__(self, "inputs", dict(self.inputs))
        object.__setattr__(self, "intermediates", dict(self.intermediates))
