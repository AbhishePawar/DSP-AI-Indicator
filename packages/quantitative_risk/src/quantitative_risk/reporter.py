"""Quantitative Risk Reporter — presentation only (E2.3).

Organizes existing engine / report artifacts for presentation.
Never calculates metrics, rounds Decimals, infers values, or recommends.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from quantitative_risk.engine import EngineResult
from quantitative_risk.enums import MetricType, ReportingStatus
from quantitative_risk.exceptions import QuantitativeRiskError
from quantitative_risk.models import (
    DrawdownProfile,
    QuantitativeRiskReport,
    RiskConcentration,
    RiskExposure,
    RiskMetric,
    RiskVolatility,
)

__all__ = [
    "MetricCollection",
    "QuantitativeRiskReporter",
    "ReportMetadata",
    "ReportingContext",
    "ReportingResult",
]

_DEFAULT_SUMMARY_SECTIONS: tuple[str, ...] = (
    "overview",
    "concentration",
    "exposure",
    "volatility",
    "drawdown",
    "provenance",
    "limitations",
)


@dataclass(frozen=True, slots=True)
class MetricCollection:
    """Presentation grouping of metrics — values preserved exactly."""

    section_key: str
    title: str
    metric_type: MetricType | None
    metrics: tuple[RiskMetric, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "metrics", tuple(self.metrics))


@dataclass(frozen=True, slots=True)
class ReportMetadata:
    """Presentation metadata — descriptive only."""

    quantitative_risk_id: str
    portfolio_id: str
    as_of: str
    metric_count: int
    exposure_count: int
    concentration_count: int
    volatility_count: int
    drawdown_count: int
    section_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "section_keys", tuple(self.section_keys))


@dataclass(frozen=True, slots=True)
class ReportingContext:
    """Inputs for Quantitative Risk presentation.

    Consume ``QuantitativeRiskReport`` and/or ``EngineResult`` only.
    Never executes the engine or touches providers.
    """

    report: QuantitativeRiskReport | None = None
    engine_result: EngineResult | None = None
    summary_sections: tuple[str, ...] | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.report is None and self.engine_result is None:
            msg = "missing report identity: QuantitativeRiskReport or EngineResult required"
            raise QuantitativeRiskError(msg)
        if self.summary_sections is not None:
            object.__setattr__(
                self, "summary_sections", tuple(self.summary_sections)
            )
        object.__setattr__(
            self,
            "limitations",
            tuple(n.strip() for n in self.limitations if n.strip()),
        )


@dataclass(frozen=True, slots=True)
class ReportingResult:
    """Presentation output — immutable, calculation-free."""

    report: QuantitativeRiskReport
    status: ReportingStatus
    metadata: ReportMetadata
    metric_collections: tuple[MetricCollection, ...]
    exposures: tuple[RiskExposure, ...]
    concentrations: tuple[RiskConcentration, ...]
    volatilities: tuple[RiskVolatility, ...]
    drawdowns: tuple[DrawdownProfile, ...]
    summary_sections: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "metric_collections", tuple(self.metric_collections))
        object.__setattr__(self, "exposures", tuple(self.exposures))
        object.__setattr__(self, "concentrations", tuple(self.concentrations))
        object.__setattr__(self, "volatilities", tuple(self.volatilities))
        object.__setattr__(self, "drawdowns", tuple(self.drawdowns))
        object.__setattr__(self, "summary_sections", tuple(self.summary_sections))
        object.__setattr__(self, "warnings", tuple(self.warnings))


class QuantitativeRiskReporter:
    """Canonical presentation layer for Quantitative Risk Intelligence.

    Formats and groups existing artifacts — never invents metrics.
    """

    def validate_inputs(self, context: ReportingContext) -> None:
        """Reject invalid presentation inputs."""
        source = self._resolve_source(context)
        if not source.quantitative_risk_id:
            msg = "missing report identity: quantitative_risk_id is required"
            raise QuantitativeRiskError(msg)
        if source.portfolio_ref is None or not source.portfolio_ref.portfolio_id:
            msg = "broken references: portfolio_ref is required"
            raise QuantitativeRiskError(msg)

        if context.engine_result is not None and context.report is not None:
            if (
                context.engine_result.quantitative_risk_id
                != context.report.quantitative_risk_id
            ):
                msg = (
                    "broken references: EngineResult quantitative_risk_id "
                    f"{context.engine_result.quantitative_risk_id!r} does not "
                    f"match report {context.report.quantitative_risk_id!r}"
                )
                raise QuantitativeRiskError(msg)
            if (
                context.engine_result.report.portfolio_ref.portfolio_id
                != context.report.portfolio_ref.portfolio_id
            ):
                msg = "broken references: portfolio_id mismatch between engine and report"
                raise QuantitativeRiskError(msg)

        self._reject_duplicate_metric_ids(source.metrics)
        self._validate_metric_contracts(source.metrics)
        self._validate_exposure_contracts(source.exposures)
        if source.monitoring_ref is not None:
            if source.monitoring_ref.portfolio_id != source.portfolio_ref.portfolio_id:
                msg = (
                    "broken references: monitoring portfolio_id "
                    f"{source.monitoring_ref.portfolio_id!r} does not match "
                    f"{source.portfolio_ref.portfolio_id!r}"
                )
                raise QuantitativeRiskError(msg)

        sections = (
            context.summary_sections
            if context.summary_sections is not None
            else _DEFAULT_SUMMARY_SECTIONS
        )
        self._reject_duplicate_summary_sections(sections)

    def report(
        self,
        context: ReportingContext | QuantitativeRiskReport | EngineResult,
    ) -> ReportingResult:
        """Build presentation artifacts from an existing report or engine result."""
        ctx = self._as_context(context)
        self.validate_inputs(ctx)
        source = self._resolve_source(ctx)
        warnings: list[str] = []

        sections = (
            ctx.summary_sections
            if ctx.summary_sections is not None
            else _DEFAULT_SUMMARY_SECTIONS
        )
        self._reject_duplicate_summary_sections(sections)

        # Pass-through exact artifact tuples — no value mutation / re-quantize.
        metrics = source.metrics
        exposures = source.exposures
        concentrations = source.concentrations
        volatilities = source.volatilities
        drawdowns = source.drawdowns
        summary = source.summary

        collections = self._format_metric_collections(metrics)
        limitations = tuple(
            dict.fromkeys(
                (
                    *source.limitations,
                    *summary.limitation_notes,
                    *ctx.limitations,
                    "QuantitativeRiskReport presentation only — "
                    "no calculation performed by reporter.",
                )
            )
        )

        presented = QuantitativeRiskReport(
            quantitative_risk_id=source.quantitative_risk_id,
            portfolio_ref=source.portfolio_ref,
            summary=summary,
            as_of=source.as_of,
            metrics=metrics,
            exposures=exposures,
            concentrations=concentrations,
            correlations=source.correlations,
            volatilities=volatilities,
            drawdowns=drawdowns,
            scenarios=source.scenarios,
            scenario_results=source.scenario_results,
            distributions=source.distributions,
            monitoring_ref=source.monitoring_ref,
            benchmark_refs=source.benchmark_refs,
            market_data_refs=source.market_data_refs,
            historical_returns_refs=source.historical_returns_refs,
            research_refs=source.research_refs,
            limitations=limitations,
        )

        metadata = ReportMetadata(
            quantitative_risk_id=presented.quantitative_risk_id,
            portfolio_id=presented.portfolio_ref.portfolio_id,
            as_of=presented.as_of,
            metric_count=len(metrics),
            exposure_count=len(exposures),
            concentration_count=len(concentrations),
            volatility_count=len(volatilities),
            drawdown_count=len(drawdowns),
            section_keys=sections,
        )

        status = self._status(metrics, exposures, concentrations, volatilities, drawdowns)
        if status is ReportingStatus.PARTIAL:
            warnings.append("Report sections are incomplete.")
        if status is ReportingStatus.EMPTY:
            warnings.append("Report contains no quantitative metrics.")

        return ReportingResult(
            report=presented,
            status=status,
            metadata=metadata,
            metric_collections=collections,
            exposures=exposures,
            concentrations=concentrations,
            volatilities=volatilities,
            drawdowns=drawdowns,
            summary_sections=sections,
            warnings=tuple(warnings),
        )

    def report_many(
        self,
        contexts: tuple[
            ReportingContext | QuantitativeRiskReport | EngineResult, ...
        ],
    ) -> tuple[ReportingResult, ...]:
        """Present many reports; reject duplicate quantitative_risk identities."""
        seen: set[str] = set()
        results: list[ReportingResult] = []
        for item in contexts:
            result = self.report(item)
            qid = result.report.quantitative_risk_id
            if qid in seen:
                msg = f"duplicate report identity: quantitative_risk_id {qid!r}"
                raise QuantitativeRiskError(msg)
            seen.add(qid)
            results.append(result)
        return tuple(results)

    def _as_context(
        self,
        context: ReportingContext | QuantitativeRiskReport | EngineResult,
    ) -> ReportingContext:
        if isinstance(context, ReportingContext):
            return context
        if isinstance(context, EngineResult):
            return ReportingContext(engine_result=context)
        if isinstance(context, QuantitativeRiskReport):
            return ReportingContext(report=context)
        msg = "invalid reporting input"
        raise QuantitativeRiskError(msg)

    def _resolve_source(self, context: ReportingContext) -> QuantitativeRiskReport:
        if context.engine_result is not None:
            return context.engine_result.report
        if context.report is not None:
            return context.report
        msg = "missing report identity: QuantitativeRiskReport or EngineResult required"
        raise QuantitativeRiskError(msg)

    def _format_metric_collections(
        self, metrics: tuple[RiskMetric, ...]
    ) -> tuple[MetricCollection, ...]:
        """Group metrics by type — preserve exact Decimal values."""
        order: tuple[tuple[str, str, MetricType], ...] = (
            ("concentration", "Concentration metrics", MetricType.CONCENTRATION),
            ("exposure", "Exposure metrics", MetricType.EXPOSURE),
            ("volatility", "Volatility metrics", MetricType.VOLATILITY),
            ("drawdown", "Drawdown metrics", MetricType.DRAWDOWN),
        )
        collections: list[MetricCollection] = []
        for key, title, metric_type in order:
            grouped = tuple(m for m in metrics if m.metric_type is metric_type)
            if grouped:
                collections.append(
                    MetricCollection(
                        section_key=key,
                        title=title,
                        metric_type=metric_type,
                        metrics=grouped,
                    )
                )
        other = tuple(
            m
            for m in metrics
            if m.metric_type
            not in {
                MetricType.CONCENTRATION,
                MetricType.EXPOSURE,
                MetricType.VOLATILITY,
                MetricType.DRAWDOWN,
            }
        )
        if other:
            collections.append(
                MetricCollection(
                    section_key="other",
                    title="Other metrics",
                    metric_type=None,
                    metrics=other,
                )
            )
        return tuple(collections)

    def _status(
        self,
        metrics: tuple[RiskMetric, ...],
        exposures: tuple[RiskExposure, ...],
        concentrations: tuple[RiskConcentration, ...],
        volatilities: tuple[RiskVolatility, ...],
        drawdowns: tuple[DrawdownProfile, ...],
    ) -> ReportingStatus:
        if not metrics and not exposures and not concentrations:
            return ReportingStatus.EMPTY
        expected_types = {
            MetricType.CONCENTRATION,
            MetricType.EXPOSURE,
            MetricType.VOLATILITY,
            MetricType.DRAWDOWN,
        }
        present = {m.metric_type for m in metrics}
        if (
            not expected_types.issubset(present)
            or not concentrations
            or not volatilities
            or not drawdowns
            or not exposures
        ):
            return ReportingStatus.PARTIAL
        return ReportingStatus.COMPLETE

    def _reject_duplicate_metric_ids(self, metrics: tuple[RiskMetric, ...]) -> None:
        seen: set[str] = set()
        for metric in metrics:
            if metric.metric_id in seen:
                msg = f"duplicate metric ids: {metric.metric_id!r}"
                raise QuantitativeRiskError(msg)
            seen.add(metric.metric_id)

    def _reject_duplicate_summary_sections(self, sections: tuple[str, ...]) -> None:
        seen: set[str] = set()
        for section in sections:
            key = section.strip().lower()
            if not key:
                msg = "duplicate summary sections: empty section key"
                raise QuantitativeRiskError(msg)
            if key in seen:
                msg = f"duplicate summary sections: {key!r}"
                raise QuantitativeRiskError(msg)
            seen.add(key)

    def _validate_metric_contracts(self, metrics: tuple[RiskMetric, ...]) -> None:
        for metric in metrics:
            if not metric.provenance:
                msg = f"missing provenance: metric {metric.metric_id!r}"
                raise QuantitativeRiskError(msg)
            if not metric.method_id or not metric.method_id.strip():
                msg = f"missing method_id: metric {metric.metric_id!r}"
                raise QuantitativeRiskError(msg)
            if not metric.unit or not metric.unit.strip():
                msg = f"missing units: metric {metric.metric_id!r}"
                raise QuantitativeRiskError(msg)
            if isinstance(metric.value, bool) or not isinstance(metric.value, Decimal):
                msg = f"invalid Decimal values: metric {metric.metric_id!r}"
                raise QuantitativeRiskError(msg)

    def _validate_exposure_contracts(
        self, exposures: tuple[RiskExposure, ...]
    ) -> None:
        for exposure in exposures:
            if not exposure.method_id or not exposure.method_id.strip():
                msg = f"missing method_id: exposure {exposure.exposure_id!r}"
                raise QuantitativeRiskError(msg)
            if isinstance(exposure.weight, bool) or not isinstance(
                exposure.weight, Decimal
            ):
                msg = f"invalid Decimal values: exposure {exposure.exposure_id!r}"
                raise QuantitativeRiskError(msg)
