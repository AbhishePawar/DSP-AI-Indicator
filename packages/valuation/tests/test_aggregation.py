"""Aggregation and confidence tests."""

from __future__ import annotations

import pytest

from valuation.aggregation import aggregate_estimates, confidence_from_count
from valuation.enums import ValuationConfidence, ValuationMethod
from valuation.models import IntrinsicValueEstimate, MarketSnapshot


def _est(
    method: ValuationMethod,
    value: float | None,
    *,
    applicable: bool,
) -> IntrinsicValueEstimate:
    return IntrinsicValueEstimate(
        method=method,
        intrinsic_value=value,
        applicable=applicable,
        formula="test",
        rationale="test rationale",
    )


class TestAggregation:
    def test_confidence_bands(self) -> None:
        assert confidence_from_count(0) is ValuationConfidence.INSUFFICIENT
        assert confidence_from_count(1) is ValuationConfidence.LOW
        assert confidence_from_count(2) is ValuationConfidence.MEDIUM
        assert confidence_from_count(4) is ValuationConfidence.HIGH

    def test_range_and_median(self) -> None:
        estimates = (
            _est(ValuationMethod.BOOK_VALUE, 100.0, applicable=True),
            _est(ValuationMethod.EARNINGS_MULTIPLE, 200.0, applicable=True),
            _est(ValuationMethod.DCF, 300.0, applicable=True),
            _est(ValuationMethod.OWNER_EARNINGS, None, applicable=False),
        )
        vr, mos, confidence, evidence, reasoning = aggregate_estimates(estimates)
        assert vr.low == 100.0
        assert vr.mid == 200.0
        assert vr.high == 300.0
        assert confidence is ValuationConfidence.MEDIUM
        assert mos.available is False
        assert len(evidence) == 4
        assert "3 applicable" in reasoning

    def test_margin_of_safety(self) -> None:
        estimates = (
            _est(ValuationMethod.BOOK_VALUE, 200.0, applicable=True),
            _est(ValuationMethod.EARNINGS_MULTIPLE, 200.0, applicable=True),
        )
        market = MarketSnapshot(market_cap=150.0)
        _vr, mos, _c, _e, reasoning = aggregate_estimates(estimates, market)
        assert mos.available is True
        assert mos.ratio == pytest.approx(0.25)
        assert "Margin of safety=25.00%" in reasoning

    def test_all_missing(self) -> None:
        estimates = (
            _est(ValuationMethod.BOOK_VALUE, None, applicable=False),
            _est(ValuationMethod.DCF, None, applicable=False),
        )
        vr, mos, confidence, _e, reasoning = aggregate_estimates(estimates)
        assert vr.mid is None
        assert confidence is ValuationConfidence.INSUFFICIENT
        assert mos.available is False
        assert "No valuation methods" in reasoning

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            aggregate_estimates(())
