"""Multi-stock analysis and failure isolation tests."""

from __future__ import annotations

from contracts import RecommendationAction
from universe import (
    BatchFailurePolicy,
    BatchStatus,
    InstrumentOutcomeStatus,
    InvestmentUniverse,
    MultiStockAnalysisRequest,
    MultiStockAnalysisService,
)

from .conftest import END, START, RecordingAnalyzer, make_instrument, make_pack


class TestMultiStockAnalysis:
    def test_empty_universe_success(self) -> None:
        universe = InvestmentUniverse(name="empty")
        result = MultiStockAnalysisService(RecordingAnalyzer()).analyze(
            MultiStockAnalysisRequest(
                universe=universe, start=START, end=END
            )
        )
        assert result.status is BatchStatus.SUCCESS
        assert result.outcomes == ()
        assert result.packs == ()

    def test_single_stock(self) -> None:
        universe = InvestmentUniverse.from_instruments(
            [make_instrument("HDFCBANK")], name="one"
        )
        analyzer = RecordingAnalyzer()
        result = MultiStockAnalysisService(analyzer).analyze(
            MultiStockAnalysisRequest(
                universe=universe, start=START, end=END
            )
        )
        assert result.status is BatchStatus.SUCCESS
        assert len(result.packs) == 1
        assert result.packs[0].recommendation.action is RecommendationAction.BUY
        assert analyzer.calls == ["HDFCBANK"]

    def test_multiple_stocks_preserve_order_and_packs(self) -> None:
        symbols = ("ZEE", "AA", "MM")
        universe = InvestmentUniverse(name="multi")
        for symbol in symbols:
            universe.add(make_instrument(symbol))
        analyzer = RecordingAnalyzer()
        result = MultiStockAnalysisService(analyzer).analyze(
            MultiStockAnalysisRequest(
                universe=universe, start=START, end=END
            )
        )
        assert result.status is BatchStatus.SUCCESS
        assert [o.instrument.symbol for o in result.outcomes] == [
            "AA",
            "MM",
            "ZEE",
        ]
        assert analyzer.calls == ["AA", "MM", "ZEE"]
        for outcome in result.outcomes:
            assert outcome.status is InstrumentOutcomeStatus.SUCCESS
            assert outcome.pack is not None
            assert (
                outcome.pack.assurance.assurance_level
                is outcome.pack.assurance.assurance_level
            )

    def test_partial_success_one_failure(self) -> None:
        universe = InvestmentUniverse(name="partial")
        for symbol in ("AA", "BB", "CC"):
            universe.add(make_instrument(symbol))
        analyzer = RecordingAnalyzer(fail_symbols={"BB"})
        result = MultiStockAnalysisService(analyzer).analyze(
            MultiStockAnalysisRequest(
                universe=universe,
                start=START,
                end=END,
                failure_policy=BatchFailurePolicy.PARTIAL,
            )
        )
        assert result.status is BatchStatus.PARTIAL_SUCCESS
        assert len(result.successes) == 2
        assert len(result.failures) == 1
        assert result.failures[0].instrument.symbol == "BB"
        assert result.failures[0].failure is not None
        assert analyzer.calls == ["AA", "BB", "CC"]

    def test_strict_stops_and_records_skips(self) -> None:
        universe = InvestmentUniverse(name="strict")
        for symbol in ("AA", "BB", "CC"):
            universe.add(make_instrument(symbol))
        analyzer = RecordingAnalyzer(fail_symbols={"BB"})
        result = MultiStockAnalysisService(analyzer).analyze(
            MultiStockAnalysisRequest(
                universe=universe,
                start=START,
                end=END,
                failure_policy=BatchFailurePolicy.STRICT,
            )
        )
        # One success + failures/skips => partial if any success, else failure.
        assert result.status is BatchStatus.PARTIAL_SUCCESS
        assert [o.instrument.symbol for o in result.outcomes] == ["AA", "BB", "CC"]
        assert result.outcomes[0].status is InstrumentOutcomeStatus.SUCCESS
        assert result.outcomes[1].status is InstrumentOutcomeStatus.FAILURE
        assert result.outcomes[2].failure is not None
        assert result.outcomes[2].failure.error_type == "SkippedDueToStrictPolicy"
        assert analyzer.calls == ["AA", "BB"]

    def test_all_failures(self) -> None:
        universe = InvestmentUniverse.from_instruments(
            [make_instrument("AA"), make_instrument("BB")], name="bad"
        )
        analyzer = RecordingAnalyzer(fail_symbols={"AA", "BB"})
        result = MultiStockAnalysisService(analyzer).analyze(
            MultiStockAnalysisRequest(
                universe=universe,
                start=START,
                end=END,
                failure_policy=BatchFailurePolicy.PARTIAL,
            )
        )
        assert result.status is BatchStatus.FAILURE
        assert result.packs == ()
        assert len(result.failures) == 2

    def test_decision_pack_fields_preserved(self) -> None:
        instrument = make_instrument("KOTAKBANK")
        pack = make_pack(instrument)

        class FixedAnalyzer:
            def __call__(self, inst):  # noqa: ANN001
                assert inst.symbol == instrument.symbol
                return pack

        universe = InvestmentUniverse.from_instruments([instrument], name="k")
        result = MultiStockAnalysisService(FixedAnalyzer()).analyze(
            MultiStockAnalysisRequest(
                universe=universe, start=START, end=END
            )
        )
        got = result.packs[0]
        assert got.recommendation.action is pack.recommendation.action
        assert got.assurance.assurance_level is pack.assurance.assurance_level
        assert (
            got.assurance.investor_guidance.stance
            is pack.assurance.investor_guidance.stance
        )
        assert got.recommendation.margin_of_safety == (
            pack.recommendation.margin_of_safety
        )

    def test_deterministic_repeat(self) -> None:
        universe = InvestmentUniverse.from_instruments(
            [make_instrument("AA"), make_instrument("BB")], name="d"
        )
        service = MultiStockAnalysisService(RecordingAnalyzer())
        request = MultiStockAnalysisRequest(
            universe=universe, start=START, end=END
        )
        first = service.analyze(request)
        second = MultiStockAnalysisService(RecordingAnalyzer()).analyze(request)
        assert [o.instrument.symbol for o in first.outcomes] == [
            o.instrument.symbol for o in second.outcomes
        ]
        assert first.status is second.status
