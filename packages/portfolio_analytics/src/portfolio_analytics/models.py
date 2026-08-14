"""portfolio_analytics domain models.

Frozen dataclasses only. Every optional numeric field is ``None`` when it
cannot honestly be computed from the supplied inputs — never fabricated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from portfolio_analytics.enums import (
    AllocationDimension,
    AnalyticsStatus,
    RebalancingAction,
    TaxTerm,
)
from portfolio_analytics.exceptions import PortfolioAnalyticsError

__all__ = [
    "AllocationBreakdown",
    "AllocationBucket",
    "CorrelationMatrix",
    "EfficientFrontierPoint",
    "EfficientFrontierResult",
    "FactorExposure",
    "FactorExposureProfile",
    "HeatmapCell",
    "MonteCarloSummary",
    "PerformanceRatios",
    "PositionInput",
    "PositionLimitBreach",
    "PositionLimitReport",
    "RebalancingPlan",
    "RebalancingTrade",
    "RiskAttributionProfile",
    "RiskAttributionRow",
    "ScenarioImpact",
    "StressTestResult",
    "TaxLotAnalysis",
    "TaxReport",
]


def _clean_symbol(value: str, *, field_name: str = "symbol") -> str:
    cleaned = value.strip().upper()
    if not cleaned:
        msg = f"{field_name} must not be empty"
        raise PortfolioAnalyticsError(msg)
    return cleaned


def _finite_or_raise(value: float, *, field_name: str) -> float:
    numeric = float(value)
    if numeric != numeric or numeric in (float("inf"), float("-inf")):
        msg = f"{field_name} must be a finite number"
        raise PortfolioAnalyticsError(msg)
    return numeric


@dataclass(frozen=True, slots=True)
class PositionInput:
    """One caller-declared portfolio position (stateless dict-in contract)."""

    symbol: str
    weight: float
    units: float | None = None
    cost_basis_per_unit: float | None = None
    purchase_date: date | None = None
    sector: str | None = None
    country: str | None = None
    exchange: str | None = None
    value_score: float | None = None
    quality_score: float | None = None
    momentum_score: float | None = None
    size_score: float | None = None
    volatility_score: float | None = None

    def __post_init__(self) -> None:
        symbol = _clean_symbol(self.symbol)
        weight = _finite_or_raise(self.weight, field_name="weight")
        if weight < 0:
            msg = "weight must be >= 0"
            raise PortfolioAnalyticsError(msg)
        sector = None if self.sector is None else (self.sector.strip() or None)
        country = None if self.country is None else (self.country.strip() or None)
        exchange = None if self.exchange is None else (self.exchange.strip() or None)
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "weight", weight)
        object.__setattr__(self, "sector", sector)
        object.__setattr__(self, "country", country)
        object.__setattr__(self, "exchange", exchange)


@dataclass(frozen=True, slots=True)
class PerformanceRatios:
    """Portfolio-vs-benchmark performance metrics (RS-004/RS-006 inputs)."""

    status: AnalyticsStatus
    window_days: int
    sharpe_ratio: float | None = None
    sortino_ratio: float | None = None
    treynor_ratio: float | None = None
    jensen_alpha: float | None = None
    beta: float | None = None
    tracking_error: float | None = None
    information_ratio: float | None = None
    max_drawdown: float | None = None
    annualized_return: float | None = None
    annualized_volatility: float | None = None
    risk_free_rate: float = 0.0
    limitations: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "window_days": self.window_days,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "treynor_ratio": self.treynor_ratio,
            "jensen_alpha": self.jensen_alpha,
            "beta": self.beta,
            "tracking_error": self.tracking_error,
            "information_ratio": self.information_ratio,
            "max_drawdown": self.max_drawdown,
            "annualized_return": self.annualized_return,
            "annualized_volatility": self.annualized_volatility,
            "risk_free_rate": self.risk_free_rate,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class CorrelationMatrix:
    """Pairwise correlation matrix across holdings."""

    symbols: tuple[str, ...]
    matrix: tuple[tuple[float | None, ...], ...]
    window_days: int

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "symbols": list(self.symbols),
            "matrix": [list(row) for row in self.matrix],
            "window_days": self.window_days,
        }


@dataclass(frozen=True, slots=True)
class HeatmapCell:
    """One portfolio-heatmap cell — weight/volatility/correlation risk contribution."""

    symbol: str
    sector: str | None
    weight: float
    volatility: float | None
    risk_contribution_pct: float | None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "sector": self.sector,
            "weight": self.weight,
            "volatility": self.volatility,
            "risk_contribution_pct": self.risk_contribution_pct,
        }


@dataclass(frozen=True, slots=True)
class RiskAttributionRow:
    """Per-position contribution to total portfolio risk."""

    symbol: str
    weight: float
    volatility: float | None
    correlation_to_portfolio: float | None
    risk_contribution_pct: float | None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "weight": self.weight,
            "volatility": self.volatility,
            "correlation_to_portfolio": self.correlation_to_portfolio,
            "risk_contribution_pct": self.risk_contribution_pct,
        }


@dataclass(frozen=True, slots=True)
class RiskAttributionProfile:
    """Risk attribution + heatmap bundle for one portfolio."""

    status: AnalyticsStatus
    rows: tuple[RiskAttributionRow, ...]
    heatmap: tuple[HeatmapCell, ...]
    correlation_matrix: CorrelationMatrix | None
    limitations: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "rows": [r.to_public_dict() for r in self.rows],
            "heatmap": [c.to_public_dict() for c in self.heatmap],
            "correlation_matrix": (
                self.correlation_matrix.to_public_dict()
                if self.correlation_matrix is not None
                else None
            ),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class FactorExposure:
    """Portfolio-weighted rollup of one factor — aggregation only, no scoring."""

    factor_name: str
    exposure_value: float | None
    contributing_positions: int
    total_positions: int

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "factor_name": self.factor_name,
            "exposure_value": self.exposure_value,
            "contributing_positions": self.contributing_positions,
            "total_positions": self.total_positions,
        }


@dataclass(frozen=True, slots=True)
class FactorExposureProfile:
    """Collection of factor exposures for one portfolio."""

    status: AnalyticsStatus
    factors: tuple[FactorExposure, ...]
    limitations: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "factors": [f.to_public_dict() for f in self.factors],
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class AllocationBucket:
    """One bucket (e.g. one sector or country) of an allocation breakdown."""

    label: str
    weight: float
    symbols: tuple[str, ...]

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "weight": self.weight,
            "symbols": list(self.symbols),
        }


@dataclass(frozen=True, slots=True)
class AllocationBreakdown:
    """Allocation breakdown along one dimension (sector or country)."""

    dimension: AllocationDimension
    status: AnalyticsStatus
    buckets: tuple[AllocationBucket, ...]
    unclassified_weight: float
    limitations: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "status": self.status.value,
            "buckets": [b.to_public_dict() for b in self.buckets],
            "unclassified_weight": self.unclassified_weight,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class EfficientFrontierPoint:
    """One sampled point on the (approximate) efficient frontier."""

    expected_return: float
    volatility: float
    weights: dict[str, float] = field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "expected_return": self.expected_return,
            "volatility": self.volatility,
            "weights": dict(self.weights),
        }


@dataclass(frozen=True, slots=True)
class EfficientFrontierResult:
    """Efficient frontier sampling result — approximation, never exact."""

    status: AnalyticsStatus
    points: tuple[EfficientFrontierPoint, ...]
    current_portfolio_point: EfficientFrontierPoint | None
    method_id: str
    samples: int
    limitations: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "points": [p.to_public_dict() for p in self.points],
            "current_portfolio_point": (
                self.current_portfolio_point.to_public_dict()
                if self.current_portfolio_point is not None
                else None
            ),
            "method_id": self.method_id,
            "samples": self.samples,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class MonteCarloSummary:
    """Monte Carlo bootstrap-resampling summary — approximation, never exact."""

    status: AnalyticsStatus
    paths: int
    horizon_days: int
    percentiles: dict[str, float] = field(default_factory=dict)
    mean_terminal_return: float | None = None
    method_id: str = "dsp.portfolio_analytics.method.monte_carlo.bootstrap.v1"
    seed: int | None = None
    limitations: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "paths": self.paths,
            "horizon_days": self.horizon_days,
            "percentiles": dict(self.percentiles),
            "mean_terminal_return": self.mean_terminal_return,
            "method_id": self.method_id,
            "seed": self.seed,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class ScenarioImpact:
    """Caller-defined shock scenario applied via beta-implied sensitivity."""

    scenario_name: str
    shock_pct: float
    portfolio_impact_pct: float | None
    per_position_impact_pct: dict[str, float] = field(default_factory=dict)
    method_id: str = "dsp.portfolio_analytics.method.scenario.beta_sensitivity.v1"

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "scenario_name": self.scenario_name,
            "shock_pct": self.shock_pct,
            "portfolio_impact_pct": self.portfolio_impact_pct,
            "per_position_impact_pct": dict(self.per_position_impact_pct),
            "method_id": self.method_id,
        }


@dataclass(frozen=True, slots=True)
class StressTestResult:
    """Historical crash-window replay result."""

    scenario_id: str
    description: str
    window_start: str
    window_end: str
    portfolio_return_pct: float | None
    per_position_return_pct: dict[str, float] = field(default_factory=dict)
    positions_with_history: int = 0
    positions_beta_scaled: int = 0

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "description": self.description,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "portfolio_return_pct": self.portfolio_return_pct,
            "per_position_return_pct": dict(self.per_position_return_pct),
            "positions_with_history": self.positions_with_history,
            "positions_beta_scaled": self.positions_beta_scaled,
        }


@dataclass(frozen=True, slots=True)
class PositionLimitBreach:
    """One breached (or clean) position/sector limit check."""

    label: str
    limit_type: str
    limit_value: float
    actual_value: float
    breached: bool

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "limit_type": self.limit_type,
            "limit_value": self.limit_value,
            "actual_value": self.actual_value,
            "breached": self.breached,
        }


@dataclass(frozen=True, slots=True)
class PositionLimitReport:
    """Collection of position/sector/cash limit checks for one portfolio."""

    status: AnalyticsStatus
    breaches: tuple[PositionLimitBreach, ...]
    checks: tuple[PositionLimitBreach, ...]

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "breaches": [b.to_public_dict() for b in self.breaches],
            "checks": [c.to_public_dict() for c in self.checks],
        }


@dataclass(frozen=True, slots=True)
class RebalancingTrade:
    """Suggested weight delta to restore a target allocation — analysis only."""

    symbol: str
    current_weight: float
    target_weight: float
    drift: float
    suggested_action: RebalancingAction
    suggested_delta_weight: float

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "current_weight": self.current_weight,
            "target_weight": self.target_weight,
            "drift": self.drift,
            "suggested_action": self.suggested_action.value,
            "suggested_delta_weight": self.suggested_delta_weight,
        }


@dataclass(frozen=True, slots=True)
class RebalancingPlan:
    """Full rebalancing analysis — explicitly not a trade/order instruction."""

    status: AnalyticsStatus
    trades: tuple[RebalancingTrade, ...]
    total_drift: float
    disclaimer: str = (
        "Analysis only — not a trade recommendation or order instruction."
    )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "trades": [t.to_public_dict() for t in self.trades],
            "total_drift": self.total_drift,
            "disclaimer": self.disclaimer,
        }


@dataclass(frozen=True, slots=True)
class TaxLotAnalysis:
    """Unrealized gain/loss and holding-period classification for one position."""

    symbol: str
    available: bool
    unrealized_gain_loss_pct: float | None = None
    unrealized_gain_loss_per_unit: float | None = None
    holding_period_days: int | None = None
    term: TaxTerm | None = None
    harvesting_candidate: bool = False
    reason_unavailable: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "available": self.available,
            "unrealized_gain_loss_pct": self.unrealized_gain_loss_pct,
            "unrealized_gain_loss_per_unit": self.unrealized_gain_loss_per_unit,
            "holding_period_days": self.holding_period_days,
            "term": self.term.value if self.term is not None else None,
            "harvesting_candidate": self.harvesting_candidate,
            "reason_unavailable": self.reason_unavailable,
        }


@dataclass(frozen=True, slots=True)
class TaxReport:
    """Tax optimization report for one portfolio."""

    status: AnalyticsStatus
    lots: tuple[TaxLotAnalysis, ...]
    harvesting_candidates: tuple[str, ...]
    limitations: tuple[str, ...] = (
        "Requires caller-supplied cost_basis_per_unit and purchase_date per "
        "position; no transaction/lot history is fabricated.",
    )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "lots": [lot.to_public_dict() for lot in self.lots],
            "harvesting_candidates": list(self.harvesting_candidates),
            "limitations": list(self.limitations),
        }
