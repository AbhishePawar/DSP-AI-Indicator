"""Explanation domain contract.

An :class:`Explanation` is the platform's core Explainable AI primitive.
Any engine that produces a computed value which could influence a
downstream decision attaches an ``Explanation`` describing what produced
that value and why, in human-readable terms. This is what makes Design
Principle 3 ("Explainable AI") a type in the codebase rather than a
convention some engines happen to follow.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contracts._validation import (
    ensure_in_range,
    ensure_non_empty_str,
    ensure_timezone_aware,
)
from contracts.enums import EngineSource


@dataclass(frozen=True, slots=True)
class Explanation:
    """Immutable, human-readable rationale behind a computed value.

    Attributes:
        source_engine: Which platform engine produced this explanation.
        summary: A short, one-line human-readable rationale (e.g.
            ``"RSI(14) = 72.4 indicates an overbought condition"``).
        inputs_used: Names/identifiers of the inputs that fed the
            computation being explained (e.g.
            ``("close_price", "period=14")``).
        detail: Optional longer-form explanation with additional context.
        confidence: Optional confidence score in ``[0.0, 1.0]`` for the
            explained value, where applicable.
        generated_at: Optional timezone-aware timestamp of when the
            explanation was generated.
    """

    source_engine: EngineSource
    summary: str
    inputs_used: tuple[str, ...] = ()
    detail: str | None = None
    confidence: float | None = None
    generated_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate summary content, confidence bounds, and timestamp.

        Raises:
            ContractValidationError: If ``summary`` is empty,
                ``confidence`` is outside ``[0.0, 1.0]``, or
                ``generated_at`` is a naive datetime.
        """
        summary = ensure_non_empty_str(self.summary, field_name="summary")
        object.__setattr__(self, "summary", summary)
        object.__setattr__(self, "inputs_used", tuple(self.inputs_used))

        if self.confidence is not None:
            confidence = ensure_in_range(
                self.confidence, field_name="confidence", minimum=0.0, maximum=1.0
            )
            object.__setattr__(self, "confidence", confidence)

        if self.generated_at is not None:
            ensure_timezone_aware(self.generated_at, field_name="generated_at")
