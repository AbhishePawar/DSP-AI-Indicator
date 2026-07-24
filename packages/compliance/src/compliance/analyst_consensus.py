"""Market Analyst Consensus — ports only (no provider integrations)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol, runtime_checkable

__all__ = [
    "AnalystEstimate",
    "ConsensusSnapshot",
    "ConsensusProviderPort",
    "DspVsStreetComparison",
]


@dataclass(frozen=True, slots=True)
class AnalystEstimate:
    """Single analyst row — architecture placeholder."""

    analyst_id: str
    firm: str | None = None
    rating: str | None = None
    target_price: Decimal | None = None
    as_of: str | None = None


@dataclass(frozen=True, slots=True)
class ConsensusSnapshot:
    """Street consensus aggregate — fields defined; providers later."""

    average_target_price: Decimal | None = None
    consensus_rating: str | None = None
    coverage_count: int = 0
    rating_distribution: dict[str, int] = field(default_factory=dict)
    individual_analysts: tuple[AnalystEstimate, ...] = ()
    target_distribution: dict[str, int] = field(default_factory=dict)
    bull_case: str | None = None
    bear_case: str | None = None
    market_agreement: str | None = None
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DspVsStreetComparison:
    """DSP research posture vs street consensus — presentation only."""

    dsp_view: str
    street_consensus: str | None
    agreement_note: str | None = None
    ai_consensus_analysis: str | None = None


@runtime_checkable
class ConsensusProviderPort(Protocol):
    """Provider-neutral port — do not implement vendor adapters in PR1.0."""

    def fetch_consensus(self, symbol: str) -> ConsensusSnapshot: ...
