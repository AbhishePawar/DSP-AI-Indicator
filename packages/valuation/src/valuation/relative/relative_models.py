"""Domain models for Relative Valuation Suite — research-only.

Peer / industry / sector multiples are **injected** via immutable data
containers. No company names are hardcoded; no market-data APIs are called.

Future Market Data Platform adapters should implement
:class:`MultipleProvider` and populate :class:`BenchmarkMultiples`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Protocol, runtime_checkable

from valuation.core.confidence_engine import ConfidenceDetail
from valuation.core.metadata import RESEARCH_DISCLAIMER, VALUATION_CORE_VERSION
from valuation.core.quality_flags import QualityFlag
from valuation.core.result_models import (
    ScenarioOutcome,
    SensitivityMatrix,
    ValidationSummary,
    ValuationMetadata,
    ValuationResult,
)
from valuation.relative.relative_explainability import RelativeExplainedValue

__all__ = [
    "RELATIVE_VERSION",
    "RESEARCH_DISCLAIMER",
    "RelativeMultiple",
    "BenchmarkScope",
    "RelativeQualityFlag",
    "BenchmarkMultiples",
    "MultipleSnapshot",
    "MultipleProvider",
    "StaticMultipleProvider",
    "RelativeInputs",
    "MultipleAnalysis",
    "RelativeValuationResult",
    "to_valuation_result",
    "to_v2_aggregate_payload",
]

RELATIVE_VERSION = "0.10.0-relative"


class RelativeMultiple(str, Enum):
    """Supported relative valuation multiples."""

    PE = "pe"
    FORWARD_PE = "forward_pe"
    PEG = "peg"
    PB = "pb"
    PTBV = "ptbv"
    PRICE_SALES = "price_sales"
    PRICE_CASH_FLOW = "price_cash_flow"
    PRICE_FCF = "price_fcf"
    EV_SALES = "ev_sales"
    EV_EBIT = "ev_ebit"
    EV_EBITDA = "ev_ebitda"
    DIVIDEND_YIELD = "dividend_yield"


class BenchmarkScope(str, Enum):
    """Which benchmark set drives the primary fair multiple."""

    INDUSTRY = "industry"
    SECTOR = "sector"
    PEER = "peer"
    HISTORICAL = "historical"
    WEIGHTED = "weighted"


class RelativeQualityFlag(str, Enum):
    """Relative-valuation research quality / risk flags."""

    UNDERVALUED = "undervalued"
    OVERVALUED = "overvalued"
    DEEP_VALUE = "deep_value"
    PREMIUM_VALUATION = "premium_valuation"
    GROWTH_PREMIUM = "growth_premium"
    CYCLICAL_VALUATION = "cyclical_valuation"
    INDUSTRY_LEADER = "industry_leader"
    SECTOR_LEADER = "sector_leader"
    OUTLIER_MULTIPLE = "outlier_multiple"
    WEAK_PEER_SET = "weak_peer_set"


@dataclass(frozen=True, slots=True)
class BenchmarkMultiples:
    """Injected benchmark multiples for one scope (no company names).

    Attributes:
        median: Median multiple for the scope.
        mean: Mean multiple for the scope.
        count: Number of observations (peer quality signal).
        percentile_25 / percentile_75: Optional distribution anchors.
        label: Opaque research label (e.g. industry code), not a ticker.
    """

    median: float | None = None
    mean: float | None = None
    count: int = 0
    percentile_25: float | None = None
    percentile_75: float | None = None
    label: str = ""


@dataclass(frozen=True, slots=True)
class MultipleSnapshot:
    """One multiple's current vs benchmark analysis."""

    multiple: RelativeMultiple
    current: float | None
    industry: BenchmarkMultiples
    sector: BenchmarkMultiples
    peer: BenchmarkMultiples
    historical_average: float | None
    fair_multiple: float | None
    valuation_gap: float | None
    premium_discount: float | None
    percentile_rank: float | None
    implied_price: float | None


@runtime_checkable
class MultipleProvider(Protocol):
    """Port for future Market Data Platform injection of multiples."""

    def get_industry(self, multiple: RelativeMultiple) -> BenchmarkMultiples:
        """Return industry benchmark for ``multiple``."""

    def get_sector(self, multiple: RelativeMultiple) -> BenchmarkMultiples:
        """Return sector benchmark for ``multiple``."""

    def get_peer(self, multiple: RelativeMultiple) -> BenchmarkMultiples:
        """Return peer-group benchmark for ``multiple``."""

    def get_historical(self, multiple: RelativeMultiple) -> float | None:
        """Return historical average multiple, if available."""


class StaticMultipleProvider:
    """In-memory provider for research / tests (no network I/O)."""

    def __init__(
        self,
        *,
        industry: Mapping[RelativeMultiple, BenchmarkMultiples] | None = None,
        sector: Mapping[RelativeMultiple, BenchmarkMultiples] | None = None,
        peer: Mapping[RelativeMultiple, BenchmarkMultiples] | None = None,
        historical: Mapping[RelativeMultiple, float] | None = None,
    ) -> None:
        self._industry = dict(industry or {})
        self._sector = dict(sector or {})
        self._peer = dict(peer or {})
        self._historical = dict(historical or {})

    def get_industry(self, multiple: RelativeMultiple) -> BenchmarkMultiples:
        return self._industry.get(multiple, BenchmarkMultiples())

    def get_sector(self, multiple: RelativeMultiple) -> BenchmarkMultiples:
        return self._sector.get(multiple, BenchmarkMultiples())

    def get_peer(self, multiple: RelativeMultiple) -> BenchmarkMultiples:
        return self._peer.get(multiple, BenchmarkMultiples())

    def get_historical(self, multiple: RelativeMultiple) -> float | None:
        return self._historical.get(multiple)


@dataclass(frozen=True, slots=True)
class RelativeInputs:
    """Company fundamentals + injected relative benchmarks.

    Multiples and peer sets must be supplied by the caller / future data
    platform — this engine never fetches market data.
    """

    current_market_price: float
    shares_outstanding: float
    method: RelativeMultiple = RelativeMultiple.PE
    benchmark_scope: BenchmarkScope = BenchmarkScope.INDUSTRY

    enterprise_value: float | None = None
    revenue: float | None = None
    ebit: float | None = None
    ebitda: float | None = None
    net_income: float | None = None
    eps: float | None = None
    forward_eps: float | None = None
    book_value: float | None = None
    tangible_book_value: float | None = None
    operating_cash_flow: float | None = None
    free_cash_flow: float | None = None
    dividend_per_share: float | None = None
    dividend_yield: float | None = None
    growth_rate: float | None = None
    expected_growth: float | None = None

    industry: BenchmarkMultiples = field(default_factory=BenchmarkMultiples)
    sector: BenchmarkMultiples = field(default_factory=BenchmarkMultiples)
    peer: BenchmarkMultiples = field(default_factory=BenchmarkMultiples)
    historical_average: float | None = None
    average_5y: float | None = None
    average_10y: float | None = None

    # Optional map of additional multiples' benchmarks (for full suite analysis)
    industry_by_multiple: Mapping[RelativeMultiple, BenchmarkMultiples] = field(
        default_factory=dict
    )
    sector_by_multiple: Mapping[RelativeMultiple, BenchmarkMultiples] = field(
        default_factory=dict
    )
    peer_by_multiple: Mapping[RelativeMultiple, BenchmarkMultiples] = field(
        default_factory=dict
    )
    historical_by_multiple: Mapping[RelativeMultiple, float] = field(
        default_factory=dict
    )

    risk_free_rate: float | None = None
    market_premium: float | None = None
    industry_weight: float = 0.40
    sector_weight: float = 0.20
    peer_weight: float = 0.40
    accounting_quality_score: float | None = None
    currency: str = "USD"

    bear_multiple_delta: float = -0.10
    bull_multiple_delta: float = 0.10
    bear_growth_delta: float = -0.02
    bull_growth_delta: float = 0.02


@dataclass(frozen=True, slots=True)
class MultipleAnalysis:
    """Aggregate analysis across computed multiples."""

    snapshots: tuple[MultipleSnapshot, ...]
    primary: MultipleSnapshot


@dataclass(frozen=True, slots=True)
class RelativeValuationResult:
    """Full relative-valuation research result."""

    version: str
    currency: str
    disclaimer: str
    methodology: str
    method: RelativeMultiple
    benchmark_scope: BenchmarkScope
    current_multiple: RelativeExplainedValue
    fair_multiple: RelativeExplainedValue
    implied_share_price: RelativeExplainedValue
    intrinsic_value: RelativeExplainedValue
    intrinsic_value_per_share: RelativeExplainedValue
    premium_discount: RelativeExplainedValue
    margin_of_safety: RelativeExplainedValue
    peer_ranking: RelativeExplainedValue
    industry_ranking: RelativeExplainedValue
    historical_ranking: RelativeExplainedValue
    multiple_analysis: MultipleAnalysis
    confidence: str
    confidence_detail: ConfidenceDetail
    quality_flags: tuple[RelativeQualityFlag, ...]
    core_quality_flags: tuple[QualityFlag, ...]
    validation_summary: ValidationSummary
    scenarios: tuple[ScenarioOutcome, ...]
    sensitivity: SensitivityMatrix
    explainability: tuple[RelativeExplainedValue, ...]
    limitations: tuple[str, ...]
    metadata: ValuationMetadata
    execution_time_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "currency": self.currency,
            "disclaimer": self.disclaimer,
            "methodology": self.methodology,
            "method": self.method.value,
            "benchmark_scope": self.benchmark_scope.value,
            "current_multiple": self.current_multiple.value,
            "fair_multiple": self.fair_multiple.value,
            "implied_share_price": self.implied_share_price.value,
            "intrinsic_value": self.intrinsic_value.value,
            "intrinsic_value_per_share": self.intrinsic_value_per_share.value,
            "premium_discount": self.premium_discount.value,
            "margin_of_safety": self.margin_of_safety.value,
            "confidence": self.confidence,
            "quality_flags": [f.value for f in self.quality_flags],
            "execution_time_ms": self.execution_time_ms,
        }


def to_valuation_result(result: RelativeValuationResult) -> ValuationResult:
    """Map relative result onto shared :class:`ValuationResult`."""
    return ValuationResult(
        model_name="relative",
        version=result.version,
        methodology=result.methodology,
        intrinsic_value=result.intrinsic_value.value,
        enterprise_value=None,
        equity_value=result.intrinsic_value.value,
        intrinsic_value_per_share=result.intrinsic_value_per_share.value,
        margin_of_safety=result.margin_of_safety.value,
        confidence_score=result.confidence_detail.score,
        confidence_level=result.confidence_detail.level,
        quality_flags=result.core_quality_flags,
        sensitivity_results=result.sensitivity,
        scenario_results=result.scenarios,
        validation_summary=result.validation_summary,
        explainability=result.explainability,
        research_disclaimer=result.disclaimer,
        execution_time_ms=result.execution_time_ms,
        metadata=result.metadata,
        currency=result.currency,
        confidence_explanation=result.confidence_detail.explanation,
    )


def to_v2_aggregate_payload(result: RelativeValuationResult) -> dict[str, object]:
    """Stable cite payload for future V2.0 valuation aggregation."""
    return {
        "method": "relative",
        "module": "valuation.relative",
        "version": result.version,
        "currency": result.currency,
        "multiple": result.method.value,
        "benchmark_scope": result.benchmark_scope.value,
        "intrinsic_value_per_share": result.intrinsic_value_per_share.value,
        "premium_discount": result.premium_discount.value,
        "confidence": result.confidence,
        "quality_flags": [f.value for f in result.quality_flags],
        "disclaimer": result.disclaimer,
        "core_version": VALUATION_CORE_VERSION,
    }
