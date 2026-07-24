"""Quantitative Risk domain models — contracts only (E2.1).

Immutable value objects and aggregate. No calculations or engines.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from core.exceptions import ValidationError

from quantitative_risk.enums import MetricStatus, MetricType, StressScenarioType
from quantitative_risk.exceptions import QuantitativeRiskError
from quantitative_risk.refs import (
    BenchmarkReference,
    HistoricalReturnsReference,
    MarketDataReference,
    MonitoringReference,
    PortfolioReference,
    ResearchReference,
    _normalize_id,
)

__all__ = [
    "DrawdownProfile",
    "QuantitativeRiskIdentity",
    "QuantitativeRiskProfile",
    "QuantitativeRiskReport",
    "QuantitativeRiskSummary",
    "RiskConcentration",
    "RiskCorrelation",
    "RiskDistribution",
    "RiskExposure",
    "RiskMetric",
    "RiskVolatility",
    "ScenarioResult",
    "StressScenario",
]


def _require_decimal(value: Any, *, field: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, Decimal):
        msg = f"{field} must be decimal.Decimal, never float or other numeric types"
        raise ValidationError(msg)
    if not value.is_finite():
        msg = f"{field} must be a finite Decimal"
        raise ValidationError(msg)
    return value


def _non_empty(text: str, *, field: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        msg = f"{field} must not be empty"
        raise ValidationError(msg)
    return cleaned


@dataclass(frozen=True, slots=True)
class QuantitativeRiskIdentity:
    """Canonical identity of a Quantitative Risk profile / session."""

    quantitative_risk_id: str
    quantitative_risk_name: str
    created_at: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        qid = _normalize_id(self.quantitative_risk_id, field="quantitative_risk_id")
        name = _non_empty(self.quantitative_risk_name, field="quantitative_risk_name")
        created_at = (
            None if self.created_at is None else self.created_at.strip() or None
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "quantitative_risk_id", qid)
        object.__setattr__(self, "quantitative_risk_name", name)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class RiskMetric:
    """Named measurable metric — value is Decimal; method provenance required."""

    metric_id: str
    metric_name: str
    metric_type: MetricType
    value: Decimal
    unit: str
    method_id: str
    provenance: tuple[str, ...]
    calculation_timestamp: str
    status: MetricStatus = MetricStatus.VALID
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        metric_id = _normalize_id(self.metric_id, field="metric_id")
        metric_name = _non_empty(self.metric_name, field="metric_name")
        value = _require_decimal(self.value, field="value")
        unit = _non_empty(self.unit, field="unit")
        method_id = _normalize_id(self.method_id, field="method_id")
        if not self.provenance:
            msg = "missing provenance: RiskMetric requires provenance"
            raise QuantitativeRiskError(msg)
        provenance = tuple(_non_empty(p, field="provenance") for p in self.provenance)
        timestamp = _non_empty(
            self.calculation_timestamp, field="calculation_timestamp"
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "metric_id", metric_id)
        object.__setattr__(self, "metric_name", metric_name)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "method_id", method_id)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "calculation_timestamp", timestamp)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class RiskExposure:
    """Exposure decomposition artifact — structure only."""

    exposure_id: str
    dimension: str
    weight: Decimal
    label: str
    method_id: str
    provenance: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        exposure_id = _normalize_id(self.exposure_id, field="exposure_id")
        dimension = _non_empty(self.dimension, field="dimension").lower().replace(
            " ", "_"
        )
        weight = _require_decimal(self.weight, field="weight")
        label = _non_empty(self.label, field="label")
        method_id = _normalize_id(self.method_id, field="method_id")
        provenance = tuple(p.strip() for p in self.provenance if p.strip())
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "exposure_id", exposure_id)
        object.__setattr__(self, "dimension", dimension)
        object.__setattr__(self, "weight", weight)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "method_id", method_id)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class RiskConcentration:
    """Concentration measure container — no algorithm in E2.1."""

    concentration_id: str
    metric: RiskMetric
    top_weight: Decimal | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        concentration_id = _normalize_id(
            self.concentration_id, field="concentration_id"
        )
        if self.metric.metric_type is not MetricType.CONCENTRATION:
            msg = "RiskConcentration.metric must have MetricType.CONCENTRATION"
            raise QuantitativeRiskError(msg)
        top_weight = (
            None
            if self.top_weight is None
            else _require_decimal(self.top_weight, field="top_weight")
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "concentration_id", concentration_id)
        object.__setattr__(self, "top_weight", top_weight)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class RiskCorrelation:
    """Correlation / covariance summary shell — no algorithm in E2.1."""

    correlation_id: str
    method_id: str
    pair_left: str
    pair_right: str
    value: Decimal
    provenance: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        correlation_id = _normalize_id(self.correlation_id, field="correlation_id")
        method_id = _normalize_id(self.method_id, field="method_id")
        pair_left = _non_empty(self.pair_left, field="pair_left").upper()
        pair_right = _non_empty(self.pair_right, field="pair_right").upper()
        value = _require_decimal(self.value, field="value")
        provenance = tuple(p.strip() for p in self.provenance if p.strip())
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "correlation_id", correlation_id)
        object.__setattr__(self, "method_id", method_id)
        object.__setattr__(self, "pair_left", pair_left)
        object.__setattr__(self, "pair_right", pair_right)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class RiskVolatility:
    """Volatility measure container — no algorithm in E2.1."""

    volatility_id: str
    metric: RiskMetric
    window_id: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        volatility_id = _normalize_id(self.volatility_id, field="volatility_id")
        if self.metric.metric_type is not MetricType.VOLATILITY:
            msg = "RiskVolatility.metric must have MetricType.VOLATILITY"
            raise QuantitativeRiskError(msg)
        window_id = (
            None
            if self.window_id is None
            else _normalize_id(self.window_id, field="window_id")
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "volatility_id", volatility_id)
        object.__setattr__(self, "window_id", window_id)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class DrawdownProfile:
    """Drawdown profile shell — no algorithm in E2.1."""

    drawdown_id: str
    metric: RiskMetric
    max_drawdown: Decimal
    peak_timestamp: str | None = None
    trough_timestamp: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        drawdown_id = _normalize_id(self.drawdown_id, field="drawdown_id")
        if self.metric.metric_type is not MetricType.DRAWDOWN:
            msg = "DrawdownProfile.metric must have MetricType.DRAWDOWN"
            raise QuantitativeRiskError(msg)
        max_drawdown = _require_decimal(self.max_drawdown, field="max_drawdown")
        peak = (
            None
            if self.peak_timestamp is None
            else self.peak_timestamp.strip() or None
        )
        trough = (
            None
            if self.trough_timestamp is None
            else self.trough_timestamp.strip() or None
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "drawdown_id", drawdown_id)
        object.__setattr__(self, "max_drawdown", max_drawdown)
        object.__setattr__(self, "peak_timestamp", peak)
        object.__setattr__(self, "trough_timestamp", trough)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class StressScenario:
    """Declared stress scenario definition — descriptive inputs only."""

    scenario_id: str
    scenario_name: str
    scenario_type: StressScenarioType
    method_id: str
    parameters: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        scenario_id = _normalize_id(self.scenario_id, field="scenario_id")
        scenario_name = _non_empty(self.scenario_name, field="scenario_name")
        method_id = _normalize_id(self.method_id, field="method_id")
        parameters = tuple(p.strip() for p in self.parameters if p.strip())
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "scenario_id", scenario_id)
        object.__setattr__(self, "scenario_name", scenario_name)
        object.__setattr__(self, "method_id", method_id)
        object.__setattr__(self, "parameters", parameters)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    """Scenario output bound to a scenario — no engine in E2.1."""

    result_id: str
    scenario_id: str
    method_id: str
    outcome_value: Decimal
    unit: str
    provenance: tuple[str, ...]
    calculation_timestamp: str
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        result_id = _normalize_id(self.result_id, field="result_id")
        scenario_id = _normalize_id(self.scenario_id, field="scenario_id")
        method_id = _normalize_id(self.method_id, field="method_id")
        outcome_value = _require_decimal(self.outcome_value, field="outcome_value")
        unit = _non_empty(self.unit, field="unit")
        if not self.provenance:
            msg = "missing provenance: ScenarioResult requires provenance"
            raise QuantitativeRiskError(msg)
        provenance = tuple(_non_empty(p, field="provenance") for p in self.provenance)
        timestamp = _non_empty(
            self.calculation_timestamp, field="calculation_timestamp"
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "result_id", result_id)
        object.__setattr__(self, "scenario_id", scenario_id)
        object.__setattr__(self, "method_id", method_id)
        object.__setattr__(self, "outcome_value", outcome_value)
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "calculation_timestamp", timestamp)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class RiskDistribution:
    """Distributional summary shell — deferred engines may populate later."""

    distribution_id: str
    method_id: str
    quantile_labels: tuple[str, ...]
    quantile_values: tuple[Decimal, ...]
    provenance: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        distribution_id = _normalize_id(
            self.distribution_id, field="distribution_id"
        )
        method_id = _normalize_id(self.method_id, field="method_id")
        labels = tuple(_non_empty(l, field="quantile_labels") for l in self.quantile_labels)
        values = tuple(
            _require_decimal(v, field="quantile_values") for v in self.quantile_values
        )
        if len(labels) != len(values):
            msg = "quantile_labels and quantile_values length mismatch"
            raise QuantitativeRiskError(msg)
        provenance = tuple(p.strip() for p in self.provenance if p.strip())
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "distribution_id", distribution_id)
        object.__setattr__(self, "method_id", method_id)
        object.__setattr__(self, "quantile_labels", labels)
        object.__setattr__(self, "quantile_values", values)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class QuantitativeRiskSummary:
    """High-level quantitative summary — descriptive counts only."""

    metric_count: int
    exposure_count: int = 0
    scenario_count: int = 0
    limitation_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("metric_count", "exposure_count", "scenario_count"):
            if getattr(self, name) < 0:
                msg = "counts must be >= 0"
                raise ValidationError(msg)
        limitations = tuple(
            n.strip() for n in self.limitation_notes if n.strip()
        )
        object.__setattr__(self, "limitation_notes", limitations)


@dataclass(frozen=True, slots=True)
class QuantitativeRiskReport:
    """Canonical immutable Quantitative Risk presentation snapshot."""

    quantitative_risk_id: str
    portfolio_ref: PortfolioReference
    summary: QuantitativeRiskSummary
    as_of: str
    metrics: tuple[RiskMetric, ...] = ()
    exposures: tuple[RiskExposure, ...] = ()
    concentrations: tuple[RiskConcentration, ...] = ()
    correlations: tuple[RiskCorrelation, ...] = ()
    volatilities: tuple[RiskVolatility, ...] = ()
    drawdowns: tuple[DrawdownProfile, ...] = ()
    scenarios: tuple[StressScenario, ...] = ()
    scenario_results: tuple[ScenarioResult, ...] = ()
    distributions: tuple[RiskDistribution, ...] = ()
    monitoring_ref: MonitoringReference | None = None
    benchmark_refs: tuple[BenchmarkReference, ...] = ()
    market_data_refs: tuple[MarketDataReference, ...] = ()
    historical_returns_refs: tuple[HistoricalReturnsReference, ...] = ()
    research_refs: tuple[ResearchReference, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        qid = _normalize_id(
            self.quantitative_risk_id, field="quantitative_risk_id"
        )
        as_of = _non_empty(self.as_of, field="as_of")
        metrics = _unique_metrics(self.metrics)
        exposures = _unique_exposures(self.exposures)
        concentrations = _unique_concentrations(self.concentrations)
        correlations = _unique_correlations(self.correlations)
        volatilities = _unique_volatilities(self.volatilities)
        drawdowns = _unique_drawdowns(self.drawdowns)
        scenarios = _unique_scenarios(self.scenarios)
        results = _unique_scenario_results(self.scenario_results)
        _validate_scenario_results(scenarios, results)
        distributions = _unique_distributions(self.distributions)
        if self.monitoring_ref is not None:
            if self.monitoring_ref.portfolio_id != self.portfolio_ref.portfolio_id:
                msg = (
                    "foreign ownership: monitoring portfolio_id "
                    f"{self.monitoring_ref.portfolio_id!r} does not match "
                    f"{self.portfolio_ref.portfolio_id!r}"
                )
                raise QuantitativeRiskError(msg)
        limitations = tuple(n.strip() for n in self.limitations if n.strip())
        object.__setattr__(self, "quantitative_risk_id", qid)
        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(self, "metrics", metrics)
        object.__setattr__(self, "exposures", exposures)
        object.__setattr__(self, "concentrations", concentrations)
        object.__setattr__(self, "correlations", correlations)
        object.__setattr__(self, "volatilities", volatilities)
        object.__setattr__(self, "drawdowns", drawdowns)
        object.__setattr__(self, "scenarios", scenarios)
        object.__setattr__(self, "scenario_results", results)
        object.__setattr__(self, "distributions", distributions)
        object.__setattr__(self, "benchmark_refs", tuple(self.benchmark_refs))
        object.__setattr__(self, "market_data_refs", tuple(self.market_data_refs))
        object.__setattr__(
            self, "historical_returns_refs", tuple(self.historical_returns_refs)
        )
        object.__setattr__(self, "research_refs", tuple(self.research_refs))
        object.__setattr__(self, "limitations", limitations)


@dataclass(frozen=True, slots=True)
class QuantitativeRiskProfile:
    """Aggregate root — cites Portfolio; owns only quantitative risk artifacts."""

    identity: QuantitativeRiskIdentity
    portfolio_ref: PortfolioReference
    monitoring_ref: MonitoringReference | None = None
    benchmark_refs: tuple[BenchmarkReference, ...] = ()
    market_data_refs: tuple[MarketDataReference, ...] = ()
    historical_returns_refs: tuple[HistoricalReturnsReference, ...] = ()
    research_refs: tuple[ResearchReference, ...] = ()
    metrics: tuple[RiskMetric, ...] = ()
    exposures: tuple[RiskExposure, ...] = ()
    concentrations: tuple[RiskConcentration, ...] = ()
    correlations: tuple[RiskCorrelation, ...] = ()
    volatilities: tuple[RiskVolatility, ...] = ()
    drawdowns: tuple[DrawdownProfile, ...] = ()
    scenarios: tuple[StressScenario, ...] = ()
    scenario_results: tuple[ScenarioResult, ...] = ()
    distributions: tuple[RiskDistribution, ...] = ()
    summary: QuantitativeRiskSummary | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.identity is None:
            msg = "missing identity: QuantitativeRiskIdentity is required"
            raise QuantitativeRiskError(msg)
        if self.portfolio_ref is None:
            msg = "broken references: portfolio_ref is required"
            raise QuantitativeRiskError(msg)
        if self.monitoring_ref is not None:
            if self.monitoring_ref.portfolio_id != self.portfolio_ref.portfolio_id:
                msg = (
                    "foreign ownership: monitoring portfolio_id "
                    f"{self.monitoring_ref.portfolio_id!r} does not match "
                    f"{self.portfolio_ref.portfolio_id!r}"
                )
                raise QuantitativeRiskError(msg)

        metrics = _unique_metrics(self.metrics)
        exposures = _unique_exposures(self.exposures)
        concentrations = _unique_concentrations(self.concentrations)
        correlations = _unique_correlations(self.correlations)
        volatilities = _unique_volatilities(self.volatilities)
        drawdowns = _unique_drawdowns(self.drawdowns)
        scenarios = _unique_scenarios(self.scenarios)
        results = _unique_scenario_results(self.scenario_results)
        _validate_scenario_results(scenarios, results)
        distributions = _unique_distributions(self.distributions)
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "metrics", metrics)
        object.__setattr__(self, "exposures", exposures)
        object.__setattr__(self, "concentrations", concentrations)
        object.__setattr__(self, "correlations", correlations)
        object.__setattr__(self, "volatilities", volatilities)
        object.__setattr__(self, "drawdowns", drawdowns)
        object.__setattr__(self, "scenarios", scenarios)
        object.__setattr__(self, "scenario_results", results)
        object.__setattr__(self, "distributions", distributions)
        object.__setattr__(self, "benchmark_refs", tuple(self.benchmark_refs))
        object.__setattr__(self, "market_data_refs", tuple(self.market_data_refs))
        object.__setattr__(
            self, "historical_returns_refs", tuple(self.historical_returns_refs)
        )
        object.__setattr__(self, "research_refs", tuple(self.research_refs))
        object.__setattr__(self, "notes", notes)

    @property
    def quantitative_risk_id(self) -> str:
        return self.identity.quantitative_risk_id

    @property
    def portfolio_id(self) -> str:
        return self.portfolio_ref.portfolio_id


def _unique_metrics(items: tuple[RiskMetric, ...]) -> tuple[RiskMetric, ...]:
    seen: set[str] = set()
    for metric in items:
        if metric.metric_id in seen:
            msg = f"duplicate metrics: id {metric.metric_id!r}"
            raise QuantitativeRiskError(msg)
        seen.add(metric.metric_id)
    return tuple(items)


def _unique_exposures(items: tuple[RiskExposure, ...]) -> tuple[RiskExposure, ...]:
    seen: set[str] = set()
    for item in items:
        if item.exposure_id in seen:
            msg = f"duplicate exposures: id {item.exposure_id!r}"
            raise QuantitativeRiskError(msg)
        seen.add(item.exposure_id)
    return tuple(items)


def _unique_concentrations(
    items: tuple[RiskConcentration, ...],
) -> tuple[RiskConcentration, ...]:
    seen: set[str] = set()
    for item in items:
        if item.concentration_id in seen:
            msg = f"duplicate concentrations: id {item.concentration_id!r}"
            raise QuantitativeRiskError(msg)
        seen.add(item.concentration_id)
    return tuple(items)


def _unique_correlations(
    items: tuple[RiskCorrelation, ...],
) -> tuple[RiskCorrelation, ...]:
    seen: set[str] = set()
    for item in items:
        if item.correlation_id in seen:
            msg = f"duplicate correlations: id {item.correlation_id!r}"
            raise QuantitativeRiskError(msg)
        seen.add(item.correlation_id)
    return tuple(items)


def _unique_volatilities(
    items: tuple[RiskVolatility, ...],
) -> tuple[RiskVolatility, ...]:
    seen: set[str] = set()
    for item in items:
        if item.volatility_id in seen:
            msg = f"duplicate volatilities: id {item.volatility_id!r}"
            raise QuantitativeRiskError(msg)
        seen.add(item.volatility_id)
    return tuple(items)


def _unique_drawdowns(
    items: tuple[DrawdownProfile, ...],
) -> tuple[DrawdownProfile, ...]:
    seen: set[str] = set()
    for item in items:
        if item.drawdown_id in seen:
            msg = f"duplicate drawdowns: id {item.drawdown_id!r}"
            raise QuantitativeRiskError(msg)
        seen.add(item.drawdown_id)
    return tuple(items)


def _unique_scenarios(
    items: tuple[StressScenario, ...],
) -> tuple[StressScenario, ...]:
    seen: set[str] = set()
    for item in items:
        if item.scenario_id in seen:
            msg = f"duplicate scenarios: id {item.scenario_id!r}"
            raise QuantitativeRiskError(msg)
        seen.add(item.scenario_id)
    return tuple(items)


def _unique_scenario_results(
    items: tuple[ScenarioResult, ...],
) -> tuple[ScenarioResult, ...]:
    seen: set[str] = set()
    for item in items:
        if item.result_id in seen:
            msg = f"duplicate scenario results: id {item.result_id!r}"
            raise QuantitativeRiskError(msg)
        seen.add(item.result_id)
    return tuple(items)


def _unique_distributions(
    items: tuple[RiskDistribution, ...],
) -> tuple[RiskDistribution, ...]:
    seen: set[str] = set()
    for item in items:
        if item.distribution_id in seen:
            msg = f"duplicate distributions: id {item.distribution_id!r}"
            raise QuantitativeRiskError(msg)
        seen.add(item.distribution_id)
    return tuple(items)


def _validate_scenario_results(
    scenarios: tuple[StressScenario, ...],
    results: tuple[ScenarioResult, ...],
) -> None:
    scenario_ids = {s.scenario_id for s in scenarios}
    for result in results:
        if result.scenario_id not in scenario_ids:
            msg = (
                f"broken references: scenario result {result.result_id!r} "
                f"references missing scenario {result.scenario_id!r}"
            )
            raise QuantitativeRiskError(msg)
