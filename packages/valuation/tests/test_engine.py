"""ValuationEngine service tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from contracts.enums import EngineSource
from fundamental.models import FinancialSnapshot
from valuation import (
    MarketSnapshot,
    ValuationAssumptions,
    ValuationConfidence,
    ValuationEngine,
    ValuationError,
    ValuationMethod,
)

FIXED_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


class TestEngine:
    def test_full_assessment(self, snapshot: FinancialSnapshot) -> None:
        engine = ValuationEngine(clock=lambda: FIXED_NOW)
        assessment = engine.analyze(snapshot)

        assert assessment.instrument == snapshot.instrument
        assert assessment.assessed_at == FIXED_NOW
        assert assessment.currency == "USD"
        assert len(assessment.estimates) == 5
        assert len(assessment.applicable_estimates) == 5
        assert assessment.confidence is ValuationConfidence.HIGH
        assert assessment.valuation_range.mid is not None
        assert all(
            e.source_engine is EngineSource.VALUATION_ENGINE
            for e in assessment.evidence
        )

    def test_with_margin_of_safety(self, snapshot: FinancialSnapshot) -> None:
        engine = ValuationEngine(clock=lambda: FIXED_NOW)
        assessment = engine.analyze(
            snapshot, MarketSnapshot(market_cap=1_000.0)
        )
        assert assessment.margin_of_safety.available is True
        assert assessment.margin_of_safety.ratio is not None
        assert assessment.summary.margin_of_safety is assessment.margin_of_safety
        assert assessment.summary.intrinsic_mid == assessment.valuation_range.mid
        assert any(
            e.reference == "margin_of_safety" for e in assessment.evidence
        )

    def test_summary_without_market(self, snapshot: FinancialSnapshot) -> None:
        engine = ValuationEngine(clock=lambda: FIXED_NOW)
        assessment = engine.analyze(snapshot)
        assert assessment.margin_of_safety.available is False
        assert assessment.summary.margin_of_safety.available is False
        assert assessment.summary.confidence == assessment.confidence.value

    def test_sparse_inputs_degrade(
        self, sparse_snapshot: FinancialSnapshot
    ) -> None:
        engine = ValuationEngine(clock=lambda: FIXED_NOW)
        assessment = engine.analyze(sparse_snapshot)
        applicable = {e.method for e in assessment.applicable_estimates}
        assert ValuationMethod.BOOK_VALUE in applicable
        assert ValuationMethod.DCF not in applicable
        assert assessment.confidence in {
            ValuationConfidence.LOW,
            ValuationConfidence.MEDIUM,
        }

    def test_all_missing_still_returns_assessment(
        self, empty_inputs_snapshot: FinancialSnapshot
    ) -> None:
        engine = ValuationEngine(clock=lambda: FIXED_NOW)
        assessment = engine.analyze(empty_inputs_snapshot)
        assert assessment.confidence is ValuationConfidence.INSUFFICIENT
        assert assessment.valuation_range.mid is None
        assert len(assessment.estimates) == 5

    def test_deterministic(self, snapshot: FinancialSnapshot) -> None:
        engine = ValuationEngine(clock=lambda: FIXED_NOW)
        first = engine.analyze(snapshot)
        second = engine.analyze(snapshot)
        assert first.valuation_range == second.valuation_range
        assert first.confidence is second.confidence
        assert first.reasoning == second.reasoning
        assert [e.intrinsic_value for e in first.estimates] == [
            e.intrinsic_value for e in second.estimates
        ]

    def test_subset_of_methods(self, snapshot: FinancialSnapshot) -> None:
        engine = ValuationEngine(clock=lambda: FIXED_NOW)
        assessment = engine.analyze(
            snapshot, method_names=("book_value", "earnings_multiple")
        )
        assert len(assessment.estimates) == 2
        assert {e.method for e in assessment.estimates} == {
            ValuationMethod.BOOK_VALUE,
            ValuationMethod.EARNINGS_MULTIPLE,
        }

    def test_unknown_method(self, snapshot: FinancialSnapshot) -> None:
        engine = ValuationEngine(clock=lambda: FIXED_NOW)
        with pytest.raises(ValuationError, match="unknown valuation method"):
            engine.analyze(snapshot, method_names=("magic",))

    def test_custom_assumptions(self, snapshot: FinancialSnapshot) -> None:
        engine = ValuationEngine(
            assumptions=ValuationAssumptions(earnings_multiple=8.0),
            clock=lambda: FIXED_NOW,
        )
        assessment = engine.analyze(
            snapshot, method_names=("earnings_multiple",)
        )
        assert assessment.estimates[0].intrinsic_value == pytest.approx(800.0)

    def test_method_failure_wrapped(self, snapshot: FinancialSnapshot) -> None:
        class Boom:
            def estimate(self, *args, **kwargs):  # noqa: ANN001
                raise RuntimeError("boom")

        engine = ValuationEngine(
            resolve_method=lambda name: Boom(),  # type: ignore[arg-type, return-value]
            clock=lambda: FIXED_NOW,
        )
        with pytest.raises(ValuationError, match="failed"):
            engine.analyze(snapshot, method_names=("book_value",))
