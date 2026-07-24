"""Explained numeric values for evidence-first DCF outputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from core.exceptions import ValidationError

__all__ = ["ExplainedValue", "ConfidenceLevel"]

ConfidenceLevel = str  # "high" | "medium" | "low" | "insufficient"


@dataclass(frozen=True, slots=True)
class ExplainedValue:
    """One calculated field with full explainability trail.

    Attributes:
        name: Canonical field identity.
        value: Final numeric result, or ``None`` when unavailable.
        formula: Formula identity used.
        inputs: Named inputs consumed.
        intermediates: Named intermediate quantities.
        confidence: Confidence label for this field.
        notes: Limitations or skip rationale.
    """

    name: str
    value: float | None
    formula: str
    inputs: Mapping[str, float | int | str | bool | None]
    intermediates: Mapping[str, float | int | str | bool | None]
    confidence: ConfidenceLevel
    notes: str = ""

    def __post_init__(self) -> None:
        name = self.name.strip()
        formula = self.formula.strip()
        if not name:
            raise ValidationError("ExplainedValue.name must not be empty")
        if not formula:
            raise ValidationError("ExplainedValue.formula must not be empty")
        if self.confidence not in {"high", "medium", "low", "insufficient"}:
            raise ValidationError(
                f"invalid confidence: {self.confidence!r}"
            )
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "formula", formula)
        object.__setattr__(self, "notes", self.notes.strip())
        object.__setattr__(self, "inputs", dict(self.inputs))
        object.__setattr__(self, "intermediates", dict(self.intermediates))
