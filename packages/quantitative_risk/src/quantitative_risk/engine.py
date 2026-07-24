"""Quantitative Risk Engine — initial metric catalog (E2.2).

Calculates concentration, exposure, realized volatility, and maximum drawdown
via package-local ports. No reporter, vendor SDKs, or deferred metrics (VaR,
Sharpe, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from quantitative_risk.enums import EngineStatus, MetricStatus, MetricType
from quantitative_risk.exceptions import QuantitativeRiskError
from quantitative_risk.models import (
    DrawdownProfile,
    QuantitativeRiskIdentity,
    QuantitativeRiskProfile,
    QuantitativeRiskReport,
    QuantitativeRiskSummary,
    RiskConcentration,
    RiskExposure,
    RiskMetric,
    RiskVolatility,
)
from quantitative_risk.ports import (
    BenchmarkDataPort,
    HistoricalReturnsPort,
    MarketDataPort,
    ReturnPoint,
    WeightPoint,
)
from quantitative_risk.precision import (
    ANNUALIZATION_FACTOR_DAILY,
    quantize_metric,
    quantize_return,
    quantize_weight,
)
from quantitative_risk.refs import (
    BenchmarkReference,
    HistoricalReturnsReference,
    MarketDataReference,
    MonitoringReference,
    PortfolioReference,
)

__all__ = [
    "EngineContext",
    "EngineResult",
    "QuantitativeRiskEngine",
]

METHOD_CONCENTRATION_TOP_WEIGHT = "dsp.qrisk.method.concentration.top_weight.v1"
METHOD_EXPOSURE_WEIGHT = "dsp.qrisk.method.exposure.weight.v1"
METHOD_VOLATILITY_REALIZED = "dsp.qrisk.method.volatility.realized_stdev_daily.v1"
METHOD_DRAWDOWN_MAX = "dsp.qrisk.method.drawdown.max.v1"


@dataclass(frozen=True, slots=True)
class EngineContext:
    """Inputs for quantitative metric calculation — refs + ports only."""

    identity: QuantitativeRiskIdentity
    portfolio_ref: PortfolioReference
    market_data: MarketDataPort
    historical_returns: HistoricalReturnsPort
    benchmark_data: BenchmarkDataPort
    benchmark_ref: BenchmarkReference
    window_id: str
    as_of: str
    monitoring_ref: MonitoringReference | None = None
    returns_series_id: str | None = None
    calculation_timestamp: str | None = None

    def __post_init__(self) -> None:
        if self.identity is None:
            msg = "missing identity: QuantitativeRiskIdentity is required"
            raise QuantitativeRiskError(msg)
        if self.portfolio_ref is None:
            msg = "broken references: portfolio_ref is required"
            raise QuantitativeRiskError(msg)
        if self.market_data is None:
            msg = "missing market data: MarketDataPort is required"
            raise QuantitativeRiskError(msg)
        if self.historical_returns is None:
            msg = "missing historical returns: HistoricalReturnsPort is required"
            raise QuantitativeRiskError(msg)
        if self.benchmark_data is None:
            msg = "missing benchmark: BenchmarkDataPort is required"
            raise QuantitativeRiskError(msg)
        if self.benchmark_ref is None:
            msg = "missing benchmark: BenchmarkReference is required"
            raise QuantitativeRiskError(msg)

        window_id = self.window_id.strip().lower()
        if not window_id or any(ch.isspace() for ch in window_id):
            msg = "window_id must be a non-empty id without whitespace"
            raise QuantitativeRiskError(msg)
        as_of = self.as_of.strip()
        if not as_of:
            msg = "as_of must not be empty"
            raise QuantitativeRiskError(msg)
        series_id = (
            self.portfolio_ref.portfolio_id
            if self.returns_series_id is None
            else self.returns_series_id.strip().lower()
        )
        if not series_id or any(ch.isspace() for ch in series_id):
            msg = "returns_series_id must be a non-empty id without whitespace"
            raise QuantitativeRiskError(msg)
        timestamp = (
            as_of
            if self.calculation_timestamp is None
            else self.calculation_timestamp.strip()
        )
        if not timestamp:
            msg = "calculation_timestamp must not be empty"
            raise QuantitativeRiskError(msg)
        if self.monitoring_ref is not None:
            if self.monitoring_ref.portfolio_id != self.portfolio_ref.portfolio_id:
                msg = (
                    "foreign ownership: monitoring portfolio_id "
                    f"{self.monitoring_ref.portfolio_id!r} does not match "
                    f"{self.portfolio_ref.portfolio_id!r}"
                )
                raise QuantitativeRiskError(msg)

        object.__setattr__(self, "window_id", window_id)
        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(self, "returns_series_id", series_id)
        object.__setattr__(self, "calculation_timestamp", timestamp)


@dataclass(frozen=True, slots=True)
class EngineResult:
    """Immutable engine output."""

    quantitative_risk_id: str
    status: EngineStatus
    report: QuantitativeRiskReport
    profile: QuantitativeRiskProfile
    metrics: tuple[RiskMetric, ...]
    exposures: tuple[RiskExposure, ...]
    concentrations: tuple[RiskConcentration, ...]
    volatilities: tuple[RiskVolatility, ...]
    drawdowns: tuple[DrawdownProfile, ...]
    summary: QuantitativeRiskSummary
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "metrics", tuple(self.metrics))
        object.__setattr__(self, "exposures", tuple(self.exposures))
        object.__setattr__(self, "concentrations", tuple(self.concentrations))
        object.__setattr__(self, "volatilities", tuple(self.volatilities))
        object.__setattr__(self, "drawdowns", tuple(self.drawdowns))
        object.__setattr__(self, "warnings", tuple(self.warnings))


class QuantitativeRiskEngine:
    """Canonical calculation layer for the initial Quantitative Risk catalog."""

    def validate_inputs(self, context: EngineContext) -> None:
        """Reject broken refs and missing port payloads before calculation."""
        if context is None:
            msg = "EngineContext is required"
            raise QuantitativeRiskError(msg)

        weights = context.market_data.get_portfolio_weights(
            context.portfolio_ref.portfolio_id,
            as_of=context.as_of,
            snapshot_id=context.portfolio_ref.snapshot_id,
        )
        if weights is None or len(weights) == 0:
            msg = "missing market data: portfolio weights unavailable"
            raise QuantitativeRiskError(msg)
        self._validate_weights(weights)

        returns = context.historical_returns.get_returns(
            context.returns_series_id,  # type: ignore[arg-type]
            window_id=context.window_id,
        )
        if returns is None or len(returns) == 0:
            msg = "missing historical returns: series unavailable"
            raise QuantitativeRiskError(msg)
        self._validate_returns(returns, field="historical returns")

        benchmark = context.benchmark_data.get_returns(
            context.benchmark_ref.benchmark_id,
            window_id=context.window_id,
        )
        if benchmark is None or len(benchmark) == 0:
            msg = "missing benchmark: benchmark returns unavailable"
            raise QuantitativeRiskError(msg)
        self._validate_returns(benchmark, field="benchmark returns")

    def calculate(self, context: EngineContext) -> EngineResult:
        """Run the initial metric catalog and emit an immutable report."""
        self.validate_inputs(context)
        warnings: list[str] = []

        weights = context.market_data.get_portfolio_weights(
            context.portfolio_ref.portfolio_id,
            as_of=context.as_of,
            snapshot_id=context.portfolio_ref.snapshot_id,
        )
        assert weights is not None  # validated
        returns = context.historical_returns.get_returns(
            context.returns_series_id,  # type: ignore[arg-type]
            window_id=context.window_id,
        )
        assert returns is not None  # validated

        timestamp = context.calculation_timestamp  # type: ignore[assignment]
        provenance = self._provenance(context)

        concentration_metric, concentration = self._concentration(
            weights=weights,
            portfolio_id=context.portfolio_ref.portfolio_id,
            provenance=provenance,
            timestamp=timestamp,
        )
        exposure_metric, exposures = self._exposures(
            weights=weights,
            portfolio_id=context.portfolio_ref.portfolio_id,
            provenance=provenance,
            timestamp=timestamp,
        )
        volatility_metric, volatility = self._volatility(
            returns=returns,
            portfolio_id=context.portfolio_ref.portfolio_id,
            window_id=context.window_id,
            provenance=provenance,
            timestamp=timestamp,
        )
        drawdown_metric, drawdown = self._drawdown(
            returns=returns,
            portfolio_id=context.portfolio_ref.portfolio_id,
            provenance=provenance,
            timestamp=timestamp,
        )

        metrics = (
            concentration_metric,
            exposure_metric,
            volatility_metric,
            drawdown_metric,
        )
        self._reject_duplicate_metric_ids(metrics)

        concentrations = (concentration,)
        volatilities = (volatility,)
        drawdowns = (drawdown,)

        if len(returns) < 2:
            warnings.append(
                "historical returns series has fewer than 2 observations; "
                "volatility uses available sample"
            )

        summary = QuantitativeRiskSummary(
            metric_count=len(metrics),
            exposure_count=len(exposures),
            scenario_count=0,
            limitation_notes=(
                "Initial E2.2 catalog only: concentration, exposure, "
                "realized volatility, maximum drawdown.",
                "Benchmark series validated but not used in baseline metrics.",
                *tuple(warnings),
            ),
        )

        market_ref = MarketDataReference(
            series_id=context.portfolio_ref.portfolio_id,
            as_of=context.as_of,
        )
        hist_ref = HistoricalReturnsReference(
            series_id=context.returns_series_id,  # type: ignore[arg-type]
            window_id=context.window_id,
        )

        profile = QuantitativeRiskProfile(
            identity=context.identity,
            portfolio_ref=context.portfolio_ref,
            monitoring_ref=context.monitoring_ref,
            benchmark_refs=(context.benchmark_ref,),
            market_data_refs=(market_ref,),
            historical_returns_refs=(hist_ref,),
            metrics=metrics,
            exposures=exposures,
            concentrations=concentrations,
            volatilities=volatilities,
            drawdowns=drawdowns,
            summary=summary,
        )

        report = QuantitativeRiskReport(
            quantitative_risk_id=context.identity.quantitative_risk_id,
            portfolio_ref=context.portfolio_ref,
            summary=summary,
            as_of=context.as_of,
            metrics=metrics,
            exposures=exposures,
            concentrations=concentrations,
            volatilities=volatilities,
            drawdowns=drawdowns,
            monitoring_ref=context.monitoring_ref,
            benchmark_refs=(context.benchmark_ref,),
            market_data_refs=(market_ref,),
            historical_returns_refs=(hist_ref,),
            limitations=summary.limitation_notes,
        )

        status = EngineStatus.PARTIAL if warnings else EngineStatus.COMPLETE
        return EngineResult(
            quantitative_risk_id=context.identity.quantitative_risk_id,
            status=status,
            report=report,
            profile=profile,
            metrics=metrics,
            exposures=exposures,
            concentrations=concentrations,
            volatilities=volatilities,
            drawdowns=drawdowns,
            summary=summary,
            warnings=tuple(warnings),
        )

    def calculate_many(
        self, contexts: tuple[EngineContext, ...]
    ) -> tuple[EngineResult, ...]:
        """Calculate many contexts; reject duplicate quantitative_risk identities."""
        seen: set[str] = set()
        results: list[EngineResult] = []
        for context in contexts:
            qid = context.identity.quantitative_risk_id
            if qid in seen:
                msg = f"duplicate identities: quantitative_risk_id {qid!r}"
                raise QuantitativeRiskError(msg)
            seen.add(qid)
            results.append(self.calculate(context))
        return tuple(results)

    def _provenance(self, context: EngineContext) -> tuple[str, ...]:
        items = [
            f"portfolio:{context.portfolio_ref.portfolio_id}",
            f"as_of:{context.as_of}",
            f"window:{context.window_id}",
            f"returns:{context.returns_series_id}",
            f"benchmark:{context.benchmark_ref.benchmark_id}",
        ]
        if context.portfolio_ref.snapshot_id is not None:
            items.append(f"snapshot:{context.portfolio_ref.snapshot_id}")
        if context.monitoring_ref is not None:
            items.append(f"monitoring:{context.monitoring_ref.portfolio_id}")
        return tuple(items)

    def _validate_weights(self, weights: tuple[WeightPoint, ...]) -> None:
        seen: set[str] = set()
        for point in weights:
            if point.instrument_id in seen:
                msg = f"duplicate metrics: weight instrument {point.instrument_id!r}"
                raise QuantitativeRiskError(msg)
            seen.add(point.instrument_id)
            if point.weight < Decimal("0"):
                msg = "invalid Decimal values: weight must be >= 0"
                raise QuantitativeRiskError(msg)

    def _validate_returns(
        self, returns: tuple[ReturnPoint, ...], *, field: str
    ) -> None:
        for point in returns:
            # ReturnPoint already enforces Decimal; reject pathological values.
            if not point.value.is_finite():
                msg = f"invalid Decimal values: {field} contains non-finite value"
                raise QuantitativeRiskError(msg)

    def _reject_duplicate_metric_ids(self, metrics: tuple[RiskMetric, ...]) -> None:
        seen: set[str] = set()
        for metric in metrics:
            if metric.metric_id in seen:
                msg = f"duplicate metric ids: {metric.metric_id!r}"
                raise QuantitativeRiskError(msg)
            seen.add(metric.metric_id)

    def _concentration(
        self,
        *,
        weights: tuple[WeightPoint, ...],
        portfolio_id: str,
        provenance: tuple[str, ...],
        timestamp: str,
    ) -> tuple[RiskMetric, RiskConcentration]:
        top = max(weights, key=lambda w: w.weight)
        value = quantize_metric(quantize_weight(top.weight))
        metric = RiskMetric(
            metric_id=f"dsp.qrisk.metric.concentration.top_weight.{portfolio_id}",
            metric_name="Top holding weight",
            metric_type=MetricType.CONCENTRATION,
            value=value,
            unit="weight_fraction",
            method_id=METHOD_CONCENTRATION_TOP_WEIGHT,
            provenance=provenance,
            calculation_timestamp=timestamp,
            status=MetricStatus.VALID,
            notes=(f"instrument:{top.instrument_id}",),
        )
        concentration = RiskConcentration(
            concentration_id=f"dsp.qrisk.conc.top.{portfolio_id}",
            metric=metric,
            top_weight=value,
        )
        return metric, concentration

    def _exposures(
        self,
        *,
        weights: tuple[WeightPoint, ...],
        portfolio_id: str,
        provenance: tuple[str, ...],
        timestamp: str,
    ) -> tuple[RiskMetric, tuple[RiskExposure, ...]]:
        exposures: list[RiskExposure] = []
        for point in weights:
            weight = quantize_weight(point.weight)
            label = point.label or point.instrument_id.upper()
            exposures.append(
                RiskExposure(
                    exposure_id=(
                        f"dsp.qrisk.exposure.instrument."
                        f"{portfolio_id}.{point.instrument_id}"
                    ),
                    dimension="instrument",
                    weight=weight,
                    label=label,
                    method_id=METHOD_EXPOSURE_WEIGHT,
                    provenance=provenance,
                )
            )
            if point.sector is not None:
                exposures.append(
                    RiskExposure(
                        exposure_id=(
                            f"dsp.qrisk.exposure.sector."
                            f"{portfolio_id}.{point.instrument_id}."
                            f"{point.sector.lower().replace(' ', '_')}"
                        ),
                        dimension="sector",
                        weight=weight,
                        label=point.sector,
                        method_id=METHOD_EXPOSURE_WEIGHT,
                        provenance=provenance,
                    )
                )

        max_weight = quantize_metric(
            quantize_weight(max(w.weight for w in weights))
        )
        metric = RiskMetric(
            metric_id=f"dsp.qrisk.metric.exposure.max_weight.{portfolio_id}",
            metric_name="Maximum single-name exposure weight",
            metric_type=MetricType.EXPOSURE,
            value=max_weight,
            unit="weight_fraction",
            method_id=METHOD_EXPOSURE_WEIGHT,
            provenance=provenance,
            calculation_timestamp=timestamp,
            status=MetricStatus.VALID,
        )
        return metric, tuple(exposures)

    def _volatility(
        self,
        *,
        returns: tuple[ReturnPoint, ...],
        portfolio_id: str,
        window_id: str,
        provenance: tuple[str, ...],
        timestamp: str,
    ) -> tuple[RiskMetric, RiskVolatility]:
        values = tuple(quantize_return(p.value) for p in returns)
        realized = self._sample_stdev(values)
        annualized = quantize_metric(
            realized * ANNUALIZATION_FACTOR_DAILY.sqrt()
        )
        metric = RiskMetric(
            metric_id=f"dsp.qrisk.metric.volatility.realized.{portfolio_id}",
            metric_name="Annualized realized volatility (daily)",
            metric_type=MetricType.VOLATILITY,
            value=annualized,
            unit="return_fraction_annualized",
            method_id=METHOD_VOLATILITY_REALIZED,
            provenance=provenance,
            calculation_timestamp=timestamp,
            status=MetricStatus.VALID,
            notes=(
                "Sample standard deviation of period returns, "
                "annualized by sqrt(252).",
            ),
        )
        volatility = RiskVolatility(
            volatility_id=f"dsp.qrisk.vol.realized.{portfolio_id}",
            metric=metric,
            window_id=window_id,
        )
        return metric, volatility

    def _drawdown(
        self,
        *,
        returns: tuple[ReturnPoint, ...],
        portfolio_id: str,
        provenance: tuple[str, ...],
        timestamp: str,
    ) -> tuple[RiskMetric, DrawdownProfile]:
        equity = Decimal("1")
        peak = Decimal("1")
        max_dd = Decimal("0")
        peak_ts: str | None = None
        trough_ts: str | None = None
        current_peak_ts: str | None = returns[0].timestamp if returns else None

        for point in returns:
            r = quantize_return(point.value)
            equity = quantize_metric(equity * (Decimal("1") + r))
            if equity > peak:
                peak = equity
                current_peak_ts = point.timestamp
            dd = Decimal("0")
            if peak > Decimal("0"):
                dd = quantize_metric((peak - equity) / peak)
            if dd > max_dd:
                max_dd = dd
                peak_ts = current_peak_ts
                trough_ts = point.timestamp

        metric = RiskMetric(
            metric_id=f"dsp.qrisk.metric.drawdown.max.{portfolio_id}",
            metric_name="Maximum drawdown",
            metric_type=MetricType.DRAWDOWN,
            value=max_dd,
            unit="drawdown_fraction",
            method_id=METHOD_DRAWDOWN_MAX,
            provenance=provenance,
            calculation_timestamp=timestamp,
            status=MetricStatus.VALID,
        )
        drawdown = DrawdownProfile(
            drawdown_id=f"dsp.qrisk.dd.max.{portfolio_id}",
            metric=metric,
            max_drawdown=max_dd,
            peak_timestamp=peak_ts,
            trough_timestamp=trough_ts,
        )
        return metric, drawdown

    def _sample_stdev(self, values: tuple[Decimal, ...]) -> Decimal:
        n = len(values)
        if n == 0:
            msg = "missing historical returns: empty series after validation"
            raise QuantitativeRiskError(msg)
        if n == 1:
            return Decimal("0")
        total = sum(values, start=Decimal("0"))
        mean = total / Decimal(n)
        squared = sum(((v - mean) ** 2 for v in values), start=Decimal("0"))
        variance = squared / Decimal(n - 1)
        return variance.sqrt()
