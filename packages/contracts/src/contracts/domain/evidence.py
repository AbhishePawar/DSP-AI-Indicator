"""Evidence domain contract.

:class:`Evidence` represents a single, discrete fact or data point cited in
support of a broader claim (e.g. a
:class:`~contracts.domain.recommendation.Recommendation`). Where an
:class:`~contracts.domain.explanation.Explanation` describes *why* one
computed value has the value it has, ``Evidence`` describes a supporting
fact used to justify a decision that may be built from many such values.
"""

from __future__ import annotations

from dataclasses import dataclass

from contracts._validation import ensure_in_range, ensure_non_empty_str
from contracts.domain.explanation import Explanation
from contracts.enums import EngineSource


@dataclass(frozen=True, slots=True)
class Evidence:
    """Immutable, discrete supporting fact for a claim or decision.

    Attributes:
        source_engine: Which platform engine produced this evidence.
        claim: Human-readable statement of what this evidence supports
            (e.g. ``"P/E of 15.2 is below the sector median of 22.4"``).
        value: Optional numeric or textual value backing the claim.
        reference: Optional pointer to the underlying data this evidence
            was derived from (e.g. a statement period, an indicator name).
        explanation: Optional detailed explanation of how this evidence
            was derived.
        weight: Optional strength of this evidence's support for the
            claim, normalized to ``[0.0, 1.0]``.
    """

    source_engine: EngineSource
    claim: str
    value: float | str | None = None
    reference: str | None = None
    explanation: Explanation | None = None
    weight: float | None = None

    def __post_init__(self) -> None:
        """Validate claim content and weight bounds.

        Raises:
            ContractValidationError: If ``claim`` is empty, or ``weight``
                is outside ``[0.0, 1.0]``.
        """
        claim = ensure_non_empty_str(self.claim, field_name="claim")
        object.__setattr__(self, "claim", claim)

        if self.weight is not None:
            weight = ensure_in_range(
                self.weight, field_name="weight", minimum=0.0, maximum=1.0
            )
            object.__setattr__(self, "weight", weight)
