"""Quantitative Risk domain model tests (E2.1)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from core.exceptions import ValidationError

from quantitative_risk import (
    DrawdownProfile,
    MetricStatus,
    MetricType,
    MonitoringReference,
    PortfolioReference,
    QuantitativeRiskError,
    QuantitativeRiskIdentity,
    QuantitativeRiskProfile,
    QuantitativeRiskReport,
    QuantitativeRiskSummary,
    RiskConcentration,
    RiskExposure,
    RiskMetric,
    RiskVolatility,
    ScenarioResult,
    StressScenario,
    StressScenarioType,
)


def _identity() -> QuantitativeRiskIdentity:
    return QuantitativeRiskIdentity(
        quantitative_risk_id="dsp.qrisk.demo",
        quantitative_risk_name="Demo Quant Risk",
        created_at="2026-07-21T00:00:00Z",
    )


def _portfolio() -> PortfolioReference:
    return PortfolioReference(
        portfolio_id="dsp.portfolio.demo",
        snapshot_id="dsp.snapshot.1",
    )


def _metric(
    *,
    metric_id: str = "dsp.qrisk.metric.conc",
    metric_type: MetricType = MetricType.CONCENTRATION,
    value: Decimal = Decimal("0.42"),
) -> RiskMetric:
    return RiskMetric(
        metric_id=metric_id,
        metric_name="Top holding weight",
        metric_type=metric_type,
        value=value,
        unit="weight_fraction",
        method_id="dsp.qrisk.method.top_weight.v1",
        provenance=("portfolio:dsp.portfolio.demo",),
        calculation_timestamp="2026-07-21T12:00:00Z",
        status=MetricStatus.VALID,
    )


class TestIdentityAndConstruction:
    def test_identity(self) -> None:
        identity = _identity()
        assert identity.quantitative_risk_id == "dsp.qrisk.demo"

    def test_profile_aggregate(self) -> None:
        metric = _metric()
        profile = QuantitativeRiskProfile(
            identity=_identity(),
            portfolio_ref=_portfolio(),
            monitoring_ref=MonitoringReference(portfolio_id="dsp.portfolio.demo"),
            metrics=(metric,),
            exposures=(
                RiskExposure(
                    exposure_id="dsp.qrisk.exposure.aaa",
                    dimension="instrument",
                    weight=Decimal("0.42"),
                    label="AAA weight",
                    method_id="dsp.qrisk.method.exposure.v1",
                    provenance=("portfolio:dsp.portfolio.demo",),
                ),
            ),
            concentrations=(
                RiskConcentration(
                    concentration_id="dsp.qrisk.conc.1",
                    metric=metric,
                    top_weight=Decimal("0.42"),
                ),
            ),
            volatilities=(
                RiskVolatility(
                    volatility_id="dsp.qrisk.vol.1",
                    metric=_metric(
                        metric_id="dsp.qrisk.metric.vol",
                        metric_type=MetricType.VOLATILITY,
                        value=Decimal("0.18"),
                    ),
                    window_id="dsp.window.252d",
                ),
            ),
            drawdowns=(
                DrawdownProfile(
                    drawdown_id="dsp.qrisk.dd.1",
                    metric=_metric(
                        metric_id="dsp.qrisk.metric.dd",
                        metric_type=MetricType.DRAWDOWN,
                        value=Decimal("0.12"),
                    ),
                    max_drawdown=Decimal("0.12"),
                ),
            ),
            scenarios=(
                StressScenario(
                    scenario_id="dsp.qrisk.scenario.market",
                    scenario_name="Market down",
                    scenario_type=StressScenarioType.MARKET,
                    method_id="dsp.qrisk.method.stress.v1",
                    parameters=("equity:-0.10",),
                ),
            ),
            scenario_results=(
                ScenarioResult(
                    result_id="dsp.qrisk.result.1",
                    scenario_id="dsp.qrisk.scenario.market",
                    method_id="dsp.qrisk.method.stress.v1",
                    outcome_value=Decimal("-0.08"),
                    unit="portfolio_return",
                    provenance=("portfolio:dsp.portfolio.demo",),
                    calculation_timestamp="2026-07-21T12:00:00Z",
                ),
            ),
            summary=QuantitativeRiskSummary(
                metric_count=3,
                exposure_count=1,
                scenario_count=1,
                limitation_notes=("Contracts only — no engine.",),
            ),
        )
        assert profile.quantitative_risk_id == "dsp.qrisk.demo"
        assert profile.portfolio_id == "dsp.portfolio.demo"

    def test_report_immutable(self) -> None:
        report = QuantitativeRiskReport(
            quantitative_risk_id="dsp.qrisk.demo",
            portfolio_ref=_portfolio(),
            summary=QuantitativeRiskSummary(metric_count=1),
            as_of="2026-07-21",
            metrics=(_metric(),),
            limitations=("Immutable snapshot.",),
        )
        with pytest.raises(AttributeError):
            report.metrics = ()  # type: ignore[misc]


class TestValidation:
    def test_reject_float_metric_value(self) -> None:
        with pytest.raises(ValidationError, match="decimal.Decimal"):
            RiskMetric(
                metric_id="dsp.qrisk.metric.x",
                metric_name="Bad",
                metric_type=MetricType.EXPOSURE,
                value=0.5,  # type: ignore[arg-type]
                unit="weight_fraction",
                method_id="dsp.qrisk.method.x",
                provenance=("p",),
                calculation_timestamp="2026-07-21T00:00:00Z",
            )

    def test_missing_method_id(self) -> None:
        with pytest.raises(ValidationError, match="method_id"):
            RiskMetric(
                metric_id="dsp.qrisk.metric.x",
                metric_name="Bad",
                metric_type=MetricType.EXPOSURE,
                value=Decimal("0.5"),
                unit="weight_fraction",
                method_id=" ",
                provenance=("p",),
                calculation_timestamp="2026-07-21T00:00:00Z",
            )

    def test_missing_unit(self) -> None:
        with pytest.raises(ValidationError, match="unit"):
            RiskMetric(
                metric_id="dsp.qrisk.metric.x",
                metric_name="Bad",
                metric_type=MetricType.EXPOSURE,
                value=Decimal("0.5"),
                unit=" ",
                method_id="dsp.qrisk.method.x",
                provenance=("p",),
                calculation_timestamp="2026-07-21T00:00:00Z",
            )

    def test_missing_provenance(self) -> None:
        with pytest.raises(QuantitativeRiskError, match="provenance"):
            RiskMetric(
                metric_id="dsp.qrisk.metric.x",
                metric_name="Bad",
                metric_type=MetricType.EXPOSURE,
                value=Decimal("0.5"),
                unit="weight_fraction",
                method_id="dsp.qrisk.method.x",
                provenance=(),
                calculation_timestamp="2026-07-21T00:00:00Z",
            )

    def test_duplicate_metrics(self) -> None:
        metric = _metric()
        with pytest.raises(QuantitativeRiskError, match="duplicate metrics"):
            QuantitativeRiskProfile(
                identity=_identity(),
                portfolio_ref=_portfolio(),
                metrics=(metric, metric),
            )

    def test_duplicate_scenarios(self) -> None:
        scenario = StressScenario(
            scenario_id="dsp.qrisk.scenario.x",
            scenario_name="X",
            scenario_type=StressScenarioType.CUSTOM,
            method_id="dsp.qrisk.method.stress.v1",
        )
        with pytest.raises(QuantitativeRiskError, match="duplicate scenarios"):
            QuantitativeRiskProfile(
                identity=_identity(),
                portfolio_ref=_portfolio(),
                scenarios=(scenario, scenario),
            )

    def test_foreign_monitoring(self) -> None:
        with pytest.raises(QuantitativeRiskError, match="foreign ownership"):
            QuantitativeRiskProfile(
                identity=_identity(),
                portfolio_ref=_portfolio(),
                monitoring_ref=MonitoringReference(
                    portfolio_id="dsp.portfolio.other"
                ),
            )

    def test_broken_scenario_result_ref(self) -> None:
        with pytest.raises(QuantitativeRiskError, match="broken references"):
            QuantitativeRiskProfile(
                identity=_identity(),
                portfolio_ref=_portfolio(),
                scenario_results=(
                    ScenarioResult(
                        result_id="dsp.qrisk.result.x",
                        scenario_id="dsp.qrisk.scenario.missing",
                        method_id="dsp.qrisk.method.stress.v1",
                        outcome_value=Decimal("0"),
                        unit="portfolio_return",
                        provenance=("p",),
                        calculation_timestamp="2026-07-21T00:00:00Z",
                    ),
                ),
            )

    def test_concentration_type_mismatch(self) -> None:
        with pytest.raises(QuantitativeRiskError, match="CONCENTRATION"):
            RiskConcentration(
                concentration_id="dsp.qrisk.conc.bad",
                metric=_metric(metric_type=MetricType.VOLATILITY),
            )


class TestIdentityValidation:
    def test_empty_identity_rejected(self) -> None:
        with pytest.raises(ValidationError):
            QuantitativeRiskIdentity(
                quantitative_risk_id=" ",
                quantitative_risk_name="Demo",
            )


class TestPlatformExport:
    def test_platform_exports(self) -> None:
        import dsp_platform as platform

        assert platform.QuantitativeRiskIdentity is QuantitativeRiskIdentity
        assert platform.RiskMetric is RiskMetric
        assert platform.MetricType.VOLATILITY.value == "volatility"
        assert (
            platform.QuantitativeRiskPortfolioReference is PortfolioReference
        )
        assert platform.QuantitativeRiskEngine is not None
        assert platform.EngineStatus.COMPLETE.value == "complete"
        assert platform.QuantitativeRiskReporter is not None
        assert platform.ReportingStatus.COMPLETE.value == "complete"
