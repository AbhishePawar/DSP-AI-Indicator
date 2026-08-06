"""portfolio_intelligence_engine domain models.

Frozen dataclasses only. Every optional field is ``None`` when the upstream
engine did not supply it — never fabricated. See the package README for the
full data-honesty contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from portfolio_intelligence_engine.enums import (
    AllocationKind,
    DriftDirection,
    IntelligenceStatus,
    RecommendationAction,
    ValuationClass,
)
from portfolio_intelligence_engine.exceptions import PortfolioIntelligenceEngineError

__all__ = [
    "ConcentrationAnalysis",
    "ConcentrationFlag",
    "DiversificationScore",
    "DriftAnalysis",
    "DriftRow",
    "HealthScoreResult",
    "HealthSubScore",
    "HoldingSignal",
    "OpportunityEntry",
    "OpportunityRanking",
    "PortfolioRecommendation",
    "PortfolioScenarioSummary",
    "RiskHighlight",
    "RiskSummary",
    "ScenarioCase",
    "ValuationHeatmap",
    "ValuationHeatmapRow",
]


def _clean_symbol(value: str) -> str:
    cleaned = str(value).strip().upper()
    if not cleaned:
        msg = "symbol must not be empty"
        raise PortfolioIntelligenceEngineError(msg)
    return cleaned


@dataclass(frozen=True, slots=True)
class HoldingSignal:
    """One position's already-computed cross-engine signals.

    Every field beyond ``symbol``/``weight`` is optional and sourced from an
    existing, frozen engine one layer up (see
    ``dsp_platform.portfolio_intelligence_engine_facade``). This dataclass
    performs no computation — it is a typed carrier only.
    """

    symbol: str
    weight: float
    sector: str | None = None
    country: str | None = None
    industry: str | None = None
    style: str | None = None
    market_cap_bucket: str | None = None
    # Valuation Engine (via EPIC-A002 pass-through of linked Research Objects)
    margin_of_safety: float | None = None
    valuation_confidence: float | None = None
    # Business/Financial quality stage summaries (composition pipeline, pass-through)
    quality_score: float | None = None
    quality_available: bool = False
    # AI Committee / recommendation confidence (pass-through)
    committee_confidence: float | None = None
    # Risk Engine attribution (portfolio_analytics.compute_risk_attribution row)
    volatility: float | None = None
    risk_contribution_pct: float | None = None
    research_linked: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _clean_symbol(self.symbol))
        object.__setattr__(self, "weight", float(self.weight))

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "weight": self.weight,
            "sector": self.sector,
            "country": self.country,
            "industry": self.industry,
            "style": self.style,
            "market_cap_bucket": self.market_cap_bucket,
            "margin_of_safety": self.margin_of_safety,
            "valuation_confidence": self.valuation_confidence,
            "quality_score": self.quality_score,
            "quality_available": self.quality_available,
            "committee_confidence": self.committee_confidence,
            "volatility": self.volatility,
            "risk_contribution_pct": self.risk_contribution_pct,
            "research_linked": self.research_linked,
        }


@dataclass(frozen=True, slots=True)
class HealthSubScore:
    """One weighted component of the Portfolio Health Score."""

    name: str
    available: bool
    score: float | None
    weight: float
    contribution: float | None
    explanation: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "available": self.available,
            "score": self.score,
            "weight": self.weight,
            "contribution": self.contribution,
            "explanation": self.explanation,
        }


@dataclass(frozen=True, slots=True)
class HealthScoreResult:
    """Composite Portfolio Health Score (0-100) — weighted combination only."""

    status: IntelligenceStatus
    score: float | None
    components: tuple[HealthSubScore, ...]
    method_id: str = "dsp.portfolio_intelligence_engine.method.health_score.weighted_v1"
    limitations: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "score": self.score,
            "components": [c.to_public_dict() for c in self.components],
            "method_id": self.method_id,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class ConcentrationFlag:
    """One excessive-exposure flag."""

    kind: AllocationKind
    label: str
    weight: float
    threshold: float
    symbols: tuple[str, ...]

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "label": self.label,
            "weight": self.weight,
            "threshold": self.threshold,
            "symbols": list(self.symbols),
        }


@dataclass(frozen=True, slots=True)
class ConcentrationAnalysis:
    """Largest holdings + sector/industry/style/country concentration."""

    status: IntelligenceStatus
    largest_holdings: tuple[dict[str, Any], ...]
    sector_concentration: tuple[dict[str, Any], ...]
    industry_concentration: tuple[dict[str, Any], ...]
    style_concentration: tuple[dict[str, Any], ...]
    country_concentration: tuple[dict[str, Any], ...]
    herfindahl_index: float | None
    flags: tuple[ConcentrationFlag, ...]
    limitations: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "largest_holdings": [dict(h) for h in self.largest_holdings],
            "sector_concentration": [dict(h) for h in self.sector_concentration],
            "industry_concentration": [dict(h) for h in self.industry_concentration],
            "style_concentration": [dict(h) for h in self.style_concentration],
            "country_concentration": [dict(h) for h in self.country_concentration],
            "herfindahl_index": self.herfindahl_index,
            "flags": [f.to_public_dict() for f in self.flags],
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class ValuationHeatmapRow:
    """One holding's valuation classification — reuses caller-supplied MoS only."""

    symbol: str
    weight: float
    valuation_class: ValuationClass
    margin_of_safety: float | None
    confidence: float | None
    message: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "weight": self.weight,
            "valuation_class": self.valuation_class.value,
            "margin_of_safety": self.margin_of_safety,
            "confidence": self.confidence,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ValuationHeatmap:
    """Portfolio valuation heatmap — classification only, no new valuation math."""

    status: IntelligenceStatus
    rows: tuple[ValuationHeatmapRow, ...]
    undervalued_weight: float
    fairly_valued_weight: float
    overvalued_weight: float
    unavailable_weight: float
    method_id: str = (
        "dsp.portfolio_intelligence_engine.method.valuation_heatmap.mos_threshold_v1"
    )
    limitations: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "rows": [r.to_public_dict() for r in self.rows],
            "undervalued_weight": self.undervalued_weight,
            "fairly_valued_weight": self.fairly_valued_weight,
            "overvalued_weight": self.overvalued_weight,
            "unavailable_weight": self.unavailable_weight,
            "method_id": self.method_id,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class RiskHighlight:
    """One highest-risk holding, ranked by risk contribution."""

    symbol: str
    weight: float
    volatility: float | None
    risk_contribution_pct: float | None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "weight": self.weight,
            "volatility": self.volatility,
            "risk_contribution_pct": self.risk_contribution_pct,
        }


@dataclass(frozen=True, slots=True)
class RiskSummary:
    """Portfolio risk summary — aggregation + highlighting of existing Risk
    Engine output only."""

    status: IntelligenceStatus
    beta: float | None
    annualized_volatility: float | None
    max_drawdown: float | None
    tracking_error: float | None
    value_at_risk_95: float | None
    value_at_risk_method: str | None
    conditional_value_at_risk_95: float | None
    stress_test_count: int
    monte_carlo_available: bool
    highest_risk_holdings: tuple[RiskHighlight, ...]
    limitations: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "beta": self.beta,
            "annualized_volatility": self.annualized_volatility,
            "max_drawdown": self.max_drawdown,
            "tracking_error": self.tracking_error,
            "value_at_risk_95": self.value_at_risk_95,
            "value_at_risk_method": self.value_at_risk_method,
            "conditional_value_at_risk_95": self.conditional_value_at_risk_95,
            "stress_test_count": self.stress_test_count,
            "monte_carlo_available": self.monte_carlo_available,
            "highest_risk_holdings": [
                h.to_public_dict() for h in self.highest_risk_holdings
            ],
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class PortfolioRecommendation:
    """One actionable, rule-based recommendation for a single holding."""

    symbol: str
    action: RecommendationAction
    reason: str
    supporting_metrics: dict[str, Any] = field(default_factory=dict)
    confidence: float | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "action": self.action.value,
            "reason": self.reason,
            "supporting_metrics": dict(self.supporting_metrics),
            "confidence": self.confidence,
        }


@dataclass(frozen=True, slots=True)
class DriftRow:
    """One sector/style/cap-bucket bucket's deviation from an even baseline."""

    label: str
    weight: float
    baseline_weight: float
    direction: DriftDirection

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "weight": self.weight,
            "baseline_weight": self.baseline_weight,
            "direction": self.direction.value,
        }


@dataclass(frozen=True, slots=True)
class DriftAnalysis:
    """Sector/style/cap-size drift — deviation from a standard reference taxonomy."""

    status: IntelligenceStatus
    sector_drift: tuple[DriftRow, ...]
    missing_sectors: tuple[str, ...]
    style_drift: tuple[DriftRow, ...]
    cap_drift: tuple[DriftRow, ...]
    method_id: str = "dsp.portfolio_intelligence_engine.method.drift.gics_baseline_v1"
    limitations: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "sector_drift": [r.to_public_dict() for r in self.sector_drift],
            "missing_sectors": list(self.missing_sectors),
            "style_drift": [r.to_public_dict() for r in self.style_drift],
            "cap_drift": [r.to_public_dict() for r in self.cap_drift],
            "method_id": self.method_id,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class DiversificationScore:
    """Diversification score (0-100) explained by its inputs."""

    status: IntelligenceStatus
    score: float | None
    holding_count: int
    sector_count: int
    average_pairwise_correlation: float | None
    largest_position_weight: float | None
    position_herfindahl_index: float | None
    risk_herfindahl_index: float | None
    explanation: tuple[str, ...]
    limitations: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "score": self.score,
            "holding_count": self.holding_count,
            "sector_count": self.sector_count,
            "average_pairwise_correlation": self.average_pairwise_correlation,
            "largest_position_weight": self.largest_position_weight,
            "position_herfindahl_index": self.position_herfindahl_index,
            "risk_herfindahl_index": self.risk_herfindahl_index,
            "explanation": list(self.explanation),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class OpportunityEntry:
    """One holding's rank within one opportunity dimension."""

    symbol: str
    value: float
    weight: float

    def to_public_dict(self) -> dict[str, Any]:
        return {"symbol": self.symbol, "value": self.value, "weight": self.weight}


@dataclass(frozen=True, slots=True)
class OpportunityRanking:
    """Portfolio Opportunity Finder — ranking of existing signals only."""

    status: IntelligenceStatus
    highest_margin_of_safety: tuple[OpportunityEntry, ...]
    highest_expected_cagr: tuple[OpportunityEntry, ...]
    best_quality: tuple[OpportunityEntry, ...]
    lowest_risk: tuple[OpportunityEntry, ...]
    highest_conviction: tuple[OpportunityEntry, ...]
    limitations: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "highest_margin_of_safety": [
                e.to_public_dict() for e in self.highest_margin_of_safety
            ],
            "highest_expected_cagr": [
                e.to_public_dict() for e in self.highest_expected_cagr
            ],
            "best_quality": [e.to_public_dict() for e in self.best_quality],
            "lowest_risk": [e.to_public_dict() for e in self.lowest_risk],
            "highest_conviction": [e.to_public_dict() for e in self.highest_conviction],
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class ScenarioCase:
    """One Bull/Base/Bear case — a disclosed, weighted aggregation, not a
    re-run valuation."""

    case: str
    implied_return_pct: float | None

    def to_public_dict(self) -> dict[str, Any]:
        return {"case": self.case, "implied_return_pct": self.implied_return_pct}


@dataclass(frozen=True, slots=True)
class PortfolioScenarioSummary:
    """Portfolio-level Bull/Base/Bear synthesis from already-computed signals."""

    status: IntelligenceStatus
    cases: tuple[ScenarioCase, ...]
    expected_cagr: float | None
    expected_cagr_basis: str | None
    worst_case_drawdown: float | None
    worst_case_drawdown_basis: str | None
    confidence: float | None
    confidence_basis: str | None
    method_id: str = (
        "dsp.portfolio_intelligence_engine.method.scenario_summary.mos_volatility_band_v1"
    )
    limitations: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "cases": [c.to_public_dict() for c in self.cases],
            "expected_cagr": self.expected_cagr,
            "expected_cagr_basis": self.expected_cagr_basis,
            "worst_case_drawdown": self.worst_case_drawdown,
            "worst_case_drawdown_basis": self.worst_case_drawdown_basis,
            "confidence": self.confidence,
            "confidence_basis": self.confidence_basis,
            "method_id": self.method_id,
            "limitations": list(self.limitations),
        }
