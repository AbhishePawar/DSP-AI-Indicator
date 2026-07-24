"""Committee-facing analytical context DTOs.

These types are the only engine-derived shapes the Investment Committee
is allowed to consume. They contain the minimal fields members need for
deliberation — never full engine-native assessment graphs.

Mapping from engine results onto these DTOs lives in orchestration
(application layer), not in contracts or the committee.
"""

from __future__ import annotations

from dataclasses import dataclass

from contracts._validation import ensure_non_empty_str
from contracts.domain.evidence import Evidence
from contracts.domain.instrument import Instrument
from contracts.domain.margin_of_safety import MarginOfSafety
from contracts.domain.signal import Signal
from contracts.domain.valuation_summary import ValuationSummary
from contracts.enums import AnalyticalStance, ValuationConfidence

__all__ = [
    "EconomicContext",
    "FundamentalContext",
    "TechnicalContext",
    "ValuationContext",
]


@dataclass(frozen=True, slots=True)
class TechnicalContext:
    """Committee input derived from Indicator Engine output."""

    instrument: Instrument
    signals: tuple[Signal, ...]
    evidence: tuple[Evidence, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "signals", tuple(self.signals))
        object.__setattr__(self, "evidence", tuple(self.evidence))


@dataclass(frozen=True, slots=True)
class FundamentalContext:
    """Committee input derived from Fundamental Engine output."""

    instrument: Instrument
    signals: tuple[Signal, ...]
    evidence: tuple[Evidence, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "signals", tuple(self.signals))
        object.__setattr__(self, "evidence", tuple(self.evidence))


@dataclass(frozen=True, slots=True)
class EconomicContext:
    """Committee input derived from Economic Engine output."""

    stance: AnalyticalStance
    overall_condition: str
    country: str
    reasoning: str
    evidence: tuple[Evidence, ...] = ()

    def __post_init__(self) -> None:
        condition = ensure_non_empty_str(
            self.overall_condition, field_name="overall_condition"
        ).lower()
        country = ensure_non_empty_str(self.country, field_name="country")
        reasoning = ensure_non_empty_str(self.reasoning, field_name="reasoning")
        object.__setattr__(self, "overall_condition", condition)
        object.__setattr__(self, "country", country)
        object.__setattr__(self, "reasoning", reasoning)
        object.__setattr__(self, "evidence", tuple(self.evidence))


@dataclass(frozen=True, slots=True)
class ValuationContext:
    """Committee input derived from Valuation Engine output.

    Margin of Safety and Valuation Summary are shared-kernel types
    calculated once upstream (Phase A1) and never recalculated here.
    """

    instrument: Instrument
    margin_of_safety: MarginOfSafety
    valuation_summary: ValuationSummary
    confidence: ValuationConfidence
    reasoning: str
    evidence: tuple[Evidence, ...] = ()

    def __post_init__(self) -> None:
        reasoning = ensure_non_empty_str(self.reasoning, field_name="reasoning")
        object.__setattr__(self, "reasoning", reasoning)
        object.__setattr__(self, "evidence", tuple(self.evidence))
