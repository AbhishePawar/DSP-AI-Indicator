"""Quantitative Risk Reporter tests (E2.3) — presentation only."""

from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path

import pytest

from quantitative_risk import (
    BenchmarkReference,
    EngineContext,
    EngineResult,
    HistoricalReturnsPort,
    MarketDataPort,
    MetricType,
    PortfolioReference,
    QuantitativeRiskEngine,
    QuantitativeRiskError,
    QuantitativeRiskIdentity,
    QuantitativeRiskReport,
    QuantitativeRiskReporter,
    QuantitativeRiskSummary,
    ReportingContext,
    ReportingStatus,
    ReturnPoint,
    RiskMetric,
    WeightPoint,
)
from quantitative_risk.enums import MetricStatus


class FakeMarketData:
    def __init__(self, weights: tuple[WeightPoint, ...]) -> None:
        self._weights = weights

    def get_portfolio_weights(
        self,
        portfolio_id: str,
        *,
        as_of: str,
        snapshot_id: str | None = None,
    ) -> tuple[WeightPoint, ...] | None:
        _ = (portfolio_id, as_of, snapshot_id)
        return self._weights


class FakeHistoricalReturns:
    def __init__(self, returns: tuple[ReturnPoint, ...]) -> None:
        self._returns = returns

    def get_returns(
        self, series_id: str, *, window_id: str
    ) -> tuple[ReturnPoint, ...] | None:
        _ = (series_id, window_id)
        return self._returns


class FakeBenchmarkData:
    def __init__(self, returns: tuple[ReturnPoint, ...]) -> None:
        self._returns = returns

    def get_returns(
        self, benchmark_id: str, *, window_id: str
    ) -> tuple[ReturnPoint, ...] | None:
        _ = (benchmark_id, window_id)
        return self._returns


def _engine_result() -> EngineResult:
    weights = (
        WeightPoint(
            instrument_id="aaa",
            weight=Decimal("0.55"),
            sector="Technology",
        ),
        WeightPoint(
            instrument_id="bbb",
            weight=Decimal("0.45"),
            sector="Healthcare",
        ),
    )
    returns = (
        ReturnPoint(timestamp="2026-01-01", value=Decimal("0.01")),
        ReturnPoint(timestamp="2026-01-02", value=Decimal("-0.05")),
        ReturnPoint(timestamp="2026-01-03", value=Decimal("-0.04")),
        ReturnPoint(timestamp="2026-01-04", value=Decimal("0.02")),
        ReturnPoint(timestamp="2026-01-05", value=Decimal("0.01")),
    )
    ctx = EngineContext(
        identity=QuantitativeRiskIdentity(
            quantitative_risk_id="dsp.qrisk.demo",
            quantitative_risk_name="Demo Quant Risk",
        ),
        portfolio_ref=PortfolioReference(
            portfolio_id="dsp.portfolio.demo",
            snapshot_id="dsp.snapshot.1",
        ),
        market_data=FakeMarketData(weights),  # type: ignore[arg-type]
        historical_returns=FakeHistoricalReturns(returns),  # type: ignore[arg-type]
        benchmark_data=FakeBenchmarkData(returns),  # type: ignore[arg-type]
        benchmark_ref=BenchmarkReference(benchmark_id="dsp.benchmark.spx"),
        window_id="dsp.window.5d",
        as_of="2026-07-21",
        calculation_timestamp="2026-07-21T12:00:00Z",
    )
    return QuantitativeRiskEngine().calculate(ctx)


class TestReporterHappyPath:
    def test_report_from_engine_result(self) -> None:
        engine_result = _engine_result()
        result = QuantitativeRiskReporter().report(engine_result)

        assert result.status is ReportingStatus.COMPLETE
        assert result.report.quantitative_risk_id == "dsp.qrisk.demo"
        assert result.metadata.metric_count == 4
        assert {c.section_key for c in result.metric_collections} == {
            "concentration",
            "exposure",
            "volatility",
            "drawdown",
        }
        assert result.exposures
        assert result.concentrations
        assert result.volatilities
        assert result.drawdowns
        assert "overview" in result.summary_sections
        assert any("presentation only" in note for note in result.report.limitations)

    def test_report_from_quantitative_risk_report(self) -> None:
        engine_result = _engine_result()
        result = QuantitativeRiskReporter().report(engine_result.report)
        assert result.status is ReportingStatus.COMPLETE
        assert result.report.metrics == engine_result.report.metrics

    def test_preserves_decimal_values_exactly(self) -> None:
        engine_result = _engine_result()
        source_values = {m.metric_id: m.value for m in engine_result.metrics}
        result = QuantitativeRiskReporter().report(
            ReportingContext(engine_result=engine_result)
        )
        for metric in result.report.metrics:
            assert metric.value == source_values[metric.metric_id]
            assert metric.value is source_values[metric.metric_id]
            assert isinstance(metric.value, Decimal)

    def test_immutable_output(self) -> None:
        result = QuantitativeRiskReporter().report(_engine_result())
        with pytest.raises(AttributeError):
            result.report.metrics = ()  # type: ignore[misc]
        with pytest.raises(AttributeError):
            result.metric_collections = ()  # type: ignore[misc]


class TestReporterValidation:
    def test_missing_inputs(self) -> None:
        with pytest.raises(QuantitativeRiskError, match="missing report identity"):
            ReportingContext()

    def test_duplicate_summary_sections(self) -> None:
        engine_result = _engine_result()
        with pytest.raises(QuantitativeRiskError, match="duplicate summary sections"):
            QuantitativeRiskReporter().report(
                ReportingContext(
                    engine_result=engine_result,
                    summary_sections=("overview", "Overview"),
                )
            )

    def test_engine_report_identity_mismatch(self) -> None:
        engine_result = _engine_result()
        other = QuantitativeRiskReport(
            quantitative_risk_id="dsp.qrisk.other",
            portfolio_ref=PortfolioReference(portfolio_id="dsp.portfolio.demo"),
            summary=QuantitativeRiskSummary(metric_count=0),
            as_of="2026-07-21",
        )
        with pytest.raises(QuantitativeRiskError, match="broken references"):
            QuantitativeRiskReporter().report(
                ReportingContext(engine_result=engine_result, report=other)
            )

    def test_duplicate_metric_ids_rejected_by_domain(self) -> None:
        metric = RiskMetric(
            metric_id="dsp.qrisk.metric.dup",
            metric_name="Dup",
            metric_type=MetricType.CONCENTRATION,
            value=Decimal("0.1"),
            unit="weight_fraction",
            method_id="dsp.qrisk.method.x",
            provenance=("portfolio:dsp.portfolio.demo",),
            calculation_timestamp="2026-07-21T00:00:00Z",
            status=MetricStatus.VALID,
        )
        with pytest.raises(QuantitativeRiskError, match="duplicate metrics"):
            QuantitativeRiskReport(
                quantitative_risk_id="dsp.qrisk.demo",
                portfolio_ref=PortfolioReference(portfolio_id="dsp.portfolio.demo"),
                summary=QuantitativeRiskSummary(metric_count=2),
                as_of="2026-07-21",
                metrics=(metric, metric),
            )

    def test_report_many_duplicate_identity(self) -> None:
        engine_result = _engine_result()
        with pytest.raises(QuantitativeRiskError, match="duplicate report identity"):
            QuantitativeRiskReporter().report_many((engine_result, engine_result))


class TestReporterNoCalculation:
    def test_reporter_source_has_no_math_ops(self) -> None:
        path = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "quantitative_risk"
            / "reporter.py"
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))
        forbidden_names = {
            "sqrt",
            "quantize_metric",
            "quantize_weight",
            "quantize_return",
            "stdev",
            "variance",
        }
        found: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in forbidden_names:
                found.add(node.id)
            if isinstance(node, ast.Attribute) and node.attr in forbidden_names:
                found.add(node.attr)
        assert found == set()

    def test_ports_not_imported(self) -> None:
        assert MarketDataPort is not None
        assert HistoricalReturnsPort is not None
        source = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "quantitative_risk"
            / "reporter.py"
        ).read_text(encoding="utf-8")
        assert "MarketDataPort" not in source
        assert "HistoricalReturnsPort" not in source
        assert "BenchmarkDataPort" not in source
