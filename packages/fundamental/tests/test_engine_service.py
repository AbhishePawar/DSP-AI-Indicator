"""Tests for fundamental.engine.service.FundamentalEngine."""

from collections.abc import Callable
from datetime import UTC, date, datetime

import pytest

from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.signal import Signal
from contracts.enums import SignalDirection
from fundamental.analyzers.base import Analyzer
from fundamental.engine.service import DEFAULT_ANALYZER_NAMES, FundamentalEngine
from fundamental.enums import MetricUnit
from fundamental.exceptions import FundamentalError
from fundamental.models import FinancialSnapshot, FundamentalMetric

StatementFactory = Callable[..., FundamentalStatement]
SnapshotFactory = Callable[..., FinancialSnapshot]
_FIXED_NOW = datetime(2024, 6, 1, tzinfo=UTC)


class TestFundamentalEngineAnalyze:
    """Tests for FundamentalEngine.analyze end-to-end behavior."""

    @pytest.fixture(autouse=True)
    def _setup(
        self, statement_factory: StatementFactory, snapshot_factory: SnapshotFactory
    ) -> None:
        strong = statement_factory(
            revenue=1_100.0,
            net_income=250.0,
            operating_income=300.0,
            total_equity=1_000.0,
            total_debt=200.0,
            operating_cash_flow=280.0,
            capital_expenditures=20.0,
            eps_diluted=3.0,
            fiscal_year=2024,
            period_end=date(2024, 12, 31),
        )
        prior = statement_factory(
            revenue=1_000.0,
            eps_diluted=2.0,
            fiscal_year=2023,
            period_end=date(2023, 12, 31),
        )
        self.strong_snapshot = snapshot_factory([strong, prior])

    def test_default_analyzers_produce_the_expected_metric_count(self) -> None:
        engine = FundamentalEngine()
        result = engine.analyze(self.strong_snapshot)
        # profitability(3) + growth(2) + leverage(1) + quality(1) = 7
        assert len(result.analyses) == 7

    def test_returns_company_analysis_for_the_snapshot_instrument(self) -> None:
        engine = FundamentalEngine()
        result = engine.analyze(self.strong_snapshot)
        assert result.instrument is self.strong_snapshot.instrument

    def test_custom_analyzer_selection_is_honored_in_order(self) -> None:
        engine = FundamentalEngine()
        result = engine.analyze(
            self.strong_snapshot, analyzer_names=("leverage", "quality")
        )
        assert [r.analyzer_name for r in result.results] == ["leverage", "quality"]
        assert [a.metric.name for a in result.analyses] == [
            "debt_to_equity",
            "free_cash_flow",
        ]

    def test_strong_fundamentals_produce_bullish_signals(self) -> None:
        engine = FundamentalEngine()
        result = engine.analyze(
            self.strong_snapshot, analyzer_names=("profitability",)
        )
        directions = {signal.direction for signal in result.signals}
        assert directions == {SignalDirection.BULLISH}

    def test_every_analysis_has_matching_signal_explanation_evidence(self) -> None:
        engine = FundamentalEngine()
        result = engine.analyze(self.strong_snapshot)
        for analysis in result.analyses:
            assert analysis.explanation.summary == analysis.evidence.claim
            assert analysis.signal.explanation is analysis.explanation

    def test_unknown_analyzer_raises_fundamental_error(self) -> None:
        engine = FundamentalEngine()
        with pytest.raises(FundamentalError, match="unknown analyzer"):
            engine.analyze(self.strong_snapshot, analyzer_names=("valuation",))

    def test_deterministic_given_identical_inputs_and_clock(self) -> None:
        engine = FundamentalEngine(clock=lambda: _FIXED_NOW)
        first = engine.analyze(self.strong_snapshot)
        second = engine.analyze(self.strong_snapshot)
        assert first.signals == second.signals
        assert first.explanations == second.explanations
        assert first.evidence == second.evidence

    def test_default_analyzer_names_cover_every_built_in_analyzer(self) -> None:
        assert set(DEFAULT_ANALYZER_NAMES) == {
            "profitability",
            "growth",
            "leverage",
            "quality",
        }

    def test_injected_resolver_is_used_instead_of_default_registry(self) -> None:
        calls: list[str] = []

        class _FakeLeverageLikeAnalyzer(Analyzer):
            """A fake analyzer whose name has a registered rule."""

            @property
            def name(self) -> str:
                return "leverage"

            def analyze(
                self, snapshot: FinancialSnapshot
            ) -> tuple[FundamentalMetric, ...]:
                return (
                    FundamentalMetric(
                        instrument=snapshot.instrument,
                        name="debt_to_equity",
                        value=0.3,
                        unit=MetricUnit.RATIO,
                        period_end=snapshot.latest.period_end,
                    ),
                )

        def fake_resolver(name: str) -> Analyzer:
            calls.append(name)
            return _FakeLeverageLikeAnalyzer()

        engine = FundamentalEngine(resolve_analyzer=fake_resolver)
        engine.analyze(self.strong_snapshot, analyzer_names=("anything",))
        assert calls == ["anything"]

    def test_metric_without_a_registered_rule_raises_fundamental_error(self) -> None:
        class _CustomMetricAnalyzer(Analyzer):
            """A fake analyzer producing a metric with no registered rule."""

            @property
            def name(self) -> str:
                return "custom"

            def analyze(
                self, snapshot: FinancialSnapshot
            ) -> tuple[FundamentalMetric, ...]:
                return (
                    FundamentalMetric(
                        instrument=snapshot.instrument,
                        name="totally_custom_metric",
                        value=1.0,
                        unit=MetricUnit.RATIO,
                        period_end=snapshot.latest.period_end,
                    ),
                )

        engine = FundamentalEngine(
            resolve_analyzer=lambda name: _CustomMetricAnalyzer()
        )
        with pytest.raises(FundamentalError, match="No business rule registered"):
            engine.analyze(self.strong_snapshot, analyzer_names=("custom",))

    def test_analyzer_failure_is_wrapped_in_fundamental_error(self) -> None:
        class _BrokenAnalyzer(Analyzer):
            @property
            def name(self) -> str:
                return "broken"

            def analyze(
                self, snapshot: FinancialSnapshot
            ) -> tuple[FundamentalMetric, ...]:
                raise RuntimeError("boom")

        engine = FundamentalEngine(resolve_analyzer=lambda name: _BrokenAnalyzer())
        with pytest.raises(FundamentalError, match="analysis failed"):
            engine.analyze(self.strong_snapshot, analyzer_names=("broken",))

    def test_signal_returned_for_every_analysis_is_a_contract_type(self) -> None:
        engine = FundamentalEngine()
        result = engine.analyze(self.strong_snapshot)
        assert all(isinstance(signal, Signal) for signal in result.signals)
