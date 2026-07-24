"""Internal domain models for the Valuation Engine.

Engine-local types wrap analytical results. Margin of Safety and
Valuation Summary are shared-kernel contracts types — calculated once
here and propagated downstream without recalculation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from contracts.domain.evidence import Evidence
from contracts.domain.instrument import Instrument
from contracts.domain.margin_of_safety import MarginOfSafety
from contracts.domain.valuation_summary import ValuationSummary
from core.exceptions import ValidationError
from valuation.enums import ValuationConfidence, ValuationMethod

__all__ = [
    "IntrinsicValueEstimate",
    "MarginOfSafety",
    "MarketSnapshot",
    "ValuationAssessment",
    "ValuationEvidence",
    "ValuationRange",
]


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    """Optional market context for margin-of-safety calculations.

    Engine-local input adapter. When ``market_cap`` is omitted, margin
    of safety is reported as unavailable rather than invented.

    Attributes:
        market_cap: Equity market capitalization in statement currency.
        as_of: Optional market observation date.
    """

    market_cap: float | None = None
    as_of: date | None = None

    def __post_init__(self) -> None:
        if self.market_cap is not None and self.market_cap < 0:
            msg = f"market_cap must be non-negative, got {self.market_cap}"
            raise ValidationError(msg)


@dataclass(frozen=True, slots=True)
class IntrinsicValueEstimate:
    """Result of one independent valuation method.

    Attributes:
        method: Which methodology produced this estimate.
        intrinsic_value: Company-level equity value in statement
            currency, or ``None`` when the method was not applicable.
        applicable: ``True`` when required inputs were present.
        formula: Short documented formula identity.
        rationale: Human-readable explanation of the result or skip.
        inputs_used: Normalized names of statement fields / assumptions.
    """

    method: ValuationMethod
    intrinsic_value: float | None
    applicable: bool
    formula: str
    rationale: str
    inputs_used: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        formula = self.formula.strip()
        rationale = self.rationale.strip()
        if not formula:
            msg = "formula must not be empty"
            raise ValidationError(msg)
        if not rationale:
            msg = "rationale must not be empty"
            raise ValidationError(msg)
        if self.applicable and self.intrinsic_value is None:
            msg = "applicable estimates must include intrinsic_value"
            raise ValidationError(msg)
        if not self.applicable and self.intrinsic_value is not None:
            msg = "non-applicable estimates must not include intrinsic_value"
            raise ValidationError(msg)
        object.__setattr__(self, "formula", formula)
        object.__setattr__(self, "rationale", rationale)
        object.__setattr__(self, "inputs_used", tuple(self.inputs_used))


@dataclass(frozen=True, slots=True)
class ValuationRange:
    """Aggregated low / central / high intrinsic values.

    Attributes:
        low: Minimum applicable estimate (or ``None``).
        mid: Median applicable estimate (or ``None``).
        high: Maximum applicable estimate (or ``None``).
    """

    low: float | None
    mid: float | None
    high: float | None

    def __post_init__(self) -> None:
        values = [v for v in (self.low, self.mid, self.high) if v is not None]
        if values and (
            (self.low is not None and self.high is not None and self.low > self.high)
            or (
                self.mid is not None
                and self.low is not None
                and self.mid < self.low
            )
            or (
                self.mid is not None
                and self.high is not None
                and self.mid > self.high
            )
        ):
            msg = f"invalid valuation range: {self.low}, {self.mid}, {self.high}"
            raise ValidationError(msg)


@dataclass(frozen=True, slots=True)
class ValuationEvidence:
    """Engine-local evidence item before contracts mapping.

    Attributes:
        method: Source methodology.
        claim: What was concluded.
        value: Numeric support, if any.
        reference: Formula or input reference label.
    """

    method: ValuationMethod
    claim: str
    value: float | None = None
    reference: str = ""

    def __post_init__(self) -> None:
        claim = self.claim.strip()
        if not claim:
            msg = "claim must not be empty"
            raise ValidationError(msg)
        object.__setattr__(self, "claim", claim)
        object.__setattr__(self, "reference", self.reference.strip())


@dataclass(frozen=True, slots=True)
class ValuationAssessment:
    """Complete Valuation Engine output for one financial snapshot.

    Attributes:
        instrument: Valued instrument.
        estimates: Per-method results (including non-applicable).
        valuation_range: Aggregated low / mid / high.
        margin_of_safety: Shared-kernel MoS (computed once).
        summary: Shared-kernel valuation summary for downstream use.
        confidence: Breadth-based confidence label.
        evidence: ``contracts.Evidence`` trail for downstream use.
        method_evidence: Engine-local evidence items.
        reasoning: Summary narrative.
        currency: Statement currency (ISO 4217).
        as_of: Latest statement ``period_end``.
        assessed_at: Analysis timestamp (injectable clock).
    """

    instrument: Instrument
    estimates: tuple[IntrinsicValueEstimate, ...]
    valuation_range: ValuationRange
    margin_of_safety: MarginOfSafety
    summary: ValuationSummary
    confidence: ValuationConfidence
    evidence: tuple[Evidence, ...]
    method_evidence: tuple[ValuationEvidence, ...]
    reasoning: str
    currency: str
    as_of: date
    assessed_at: datetime

    def __post_init__(self) -> None:
        reasoning = self.reasoning.strip()
        currency = self.currency.strip().upper()
        if not reasoning:
            msg = "reasoning must not be empty"
            raise ValidationError(msg)
        if not currency:
            msg = "currency must not be empty"
            raise ValidationError(msg)
        if not self.estimates:
            msg = "estimates must not be empty"
            raise ValidationError(msg)
        object.__setattr__(self, "reasoning", reasoning)
        object.__setattr__(self, "currency", currency)
        object.__setattr__(self, "estimates", tuple(self.estimates))
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "method_evidence", tuple(self.method_evidence))

    @property
    def applicable_estimates(self) -> tuple[IntrinsicValueEstimate, ...]:
        """Return estimates that produced an intrinsic value."""
        return tuple(e for e in self.estimates if e.applicable)
