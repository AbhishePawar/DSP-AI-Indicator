"""Quantitative Risk Engine tests (E2.2)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from quantitative_risk import (
    BenchmarkDataPort,
    BenchmarkReference,
    EngineContext,
    EngineStatus,
    HistoricalReturnsPort,
    MarketDataPort,
    MetricType,
    MonitoringReference,
    PortfolioReference,
    QuantitativeRiskEngine,
    QuantitativeRiskError,
    QuantitativeRiskIdentity,
    ReturnPoint,
    WeightPoint,
)


class FakeMarketData:
    def __init__(self, weights: tuple[WeightPoint, ...] | None) -> None:
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
    def __init__(self, returns: tuple[ReturnPoint, ...] | None) -> None:
        self._returns = returns

    def get_returns(
        self,
        series_id: str,
        *,
        window_id: str,
    ) -> tuple[ReturnPoint, ...] | None:
        _ = (series_id, window_id)
        return self._returns


class FakeBenchmarkData:
    def __init__(self, returns: tuple[ReturnPoint, ...] | None) -> None:
        self._returns = returns

    def get_returns(
        self,
        benchmark_id: str,
        *,
        window_id: str,
    ) -> tuple[ReturnPoint, ...] | None:
        _ = (benchmark_id, window_id)
        return self._returns


def _weights() -> tuple[WeightPoint, ...]:
    return (
        WeightPoint(
            instrument_id="aaa",
            weight=Decimal("0.55"),
            sector="Technology",
            label="AAA",
        ),
        WeightPoint(
            instrument_id="bbb",
            weight=Decimal("0.45"),
            sector="Healthcare",
            label="BBB",
        ),
    )


def _returns() -> tuple[ReturnPoint, ...]:
    # Mild down then recovery — creates a measurable drawdown.
    return (
        ReturnPoint(timestamp="2026-01-01", value=Decimal("0.01")),
        ReturnPoint(timestamp="2026-01-02", value=Decimal("-0.05")),
        ReturnPoint(timestamp="2026-01-03", value=Decimal("-0.04")),
        ReturnPoint(timestamp="2026-01-04", value=Decimal("0.02")),
        ReturnPoint(timestamp="2026-01-05", value=Decimal("0.01")),
    )


def _context(
    *,
    weights: tuple[WeightPoint, ...] | None = ...,  # type: ignore[assignment]
    returns: tuple[ReturnPoint, ...] | None = ...,  # type: ignore[assignment]
    benchmark: tuple[ReturnPoint, ...] | None = ...,  # type: ignore[assignment]
    monitoring: MonitoringReference | None = None,
) -> EngineContext:
    w = _weights() if weights is ... else weights
    r = _returns() if returns is ... else returns
    b = _returns() if benchmark is ... else benchmark
    return EngineContext(
        identity=QuantitativeRiskIdentity(
            quantitative_risk_id="dsp.qrisk.demo",
            quantitative_risk_name="Demo Quant Risk",
            created_at="2026-07-21T00:00:00Z",
        ),
        portfolio_ref=PortfolioReference(
            portfolio_id="dsp.portfolio.demo",
            snapshot_id="dsp.snapshot.1",
        ),
        market_data=FakeMarketData(w),  # type: ignore[arg-type]
        historical_returns=FakeHistoricalReturns(r),  # type: ignore[arg-type]
        benchmark_data=FakeBenchmarkData(b),  # type: ignore[arg-type]
        benchmark_ref=BenchmarkReference(benchmark_id="dsp.benchmark.spx"),
        window_id="dsp.window.5d",
        as_of="2026-07-21",
        monitoring_ref=monitoring,
        calculation_timestamp="2026-07-21T12:00:00Z",
    )


class TestEngineHappyPath:
    def test_calculates_four_baseline_metrics(self) -> None:
        engine = QuantitativeRiskEngine()
        result = engine.calculate(_context())

        assert result.status is EngineStatus.COMPLETE
        assert result.quantitative_risk_id == "dsp.qrisk.demo"
        assert len(result.metrics) == 4
        types = {m.metric_type for m in result.metrics}
        assert types == {
            MetricType.CONCENTRATION,
            MetricType.EXPOSURE,
            MetricType.VOLATILITY,
            MetricType.DRAWDOWN,
        }
        assert len(result.concentrations) == 1
        assert result.concentrations[0].top_weight == Decimal("0.55000000")
        assert any(e.dimension == "instrument" for e in result.exposures)
        assert any(e.dimension == "sector" for e in result.exposures)
        assert len(result.volatilities) == 1
        assert len(result.drawdowns) == 1
        assert result.drawdowns[0].max_drawdown > Decimal("0")
        assert result.report.summary.metric_count == 4

        for metric in result.metrics:
            assert isinstance(metric.value, Decimal)
            assert metric.unit
            assert metric.method_id
            assert metric.provenance
            assert metric.calculation_timestamp
            assert not isinstance(metric.value, float)

    def test_report_immutable(self) -> None:
        result = QuantitativeRiskEngine().calculate(_context())
        with pytest.raises(AttributeError):
            result.report.metrics = ()  # type: ignore[misc]

    def test_ports_are_protocols(self) -> None:
        assert isinstance(FakeMarketData(_weights()), MarketDataPort)
        assert isinstance(FakeHistoricalReturns(_returns()), HistoricalReturnsPort)
        assert isinstance(FakeBenchmarkData(_returns()), BenchmarkDataPort)


class TestEngineValidation:
    def test_missing_market_data(self) -> None:
        with pytest.raises(QuantitativeRiskError, match="missing market data"):
            QuantitativeRiskEngine().calculate(_context(weights=None))

    def test_empty_market_data(self) -> None:
        with pytest.raises(QuantitativeRiskError, match="missing market data"):
            QuantitativeRiskEngine().calculate(_context(weights=()))

    def test_missing_historical_returns(self) -> None:
        with pytest.raises(QuantitativeRiskError, match="missing historical returns"):
            QuantitativeRiskEngine().calculate(_context(returns=None))

    def test_missing_benchmark(self) -> None:
        with pytest.raises(QuantitativeRiskError, match="missing benchmark"):
            QuantitativeRiskEngine().calculate(_context(benchmark=None))

    def test_foreign_monitoring(self) -> None:
        with pytest.raises(QuantitativeRiskError, match="foreign ownership"):
            _context(
                monitoring=MonitoringReference(portfolio_id="dsp.portfolio.other")
            )

    def test_negative_weight_rejected(self) -> None:
        bad = (
            WeightPoint(instrument_id="aaa", weight=Decimal("-0.1")),
        )
        with pytest.raises(QuantitativeRiskError, match="invalid Decimal"):
            QuantitativeRiskEngine().calculate(_context(weights=bad))

    def test_duplicate_identities_in_calculate_many(self) -> None:
        ctx = _context()
        with pytest.raises(QuantitativeRiskError, match="duplicate identities"):
            QuantitativeRiskEngine().calculate_many((ctx, ctx))

    def test_metric_contract_fields(self) -> None:
        result = QuantitativeRiskEngine().calculate(_context())
        conc = next(
            m for m in result.metrics if m.metric_type is MetricType.CONCENTRATION
        )
        assert "portfolio:dsp.portfolio.demo" in conc.provenance
        assert conc.method_id.endswith(".v1")
        assert conc.unit == "weight_fraction"
