"""Public API and model tests."""

from __future__ import annotations

from datetime import date

import pytest

from valuation import (
    IntrinsicValueEstimate,
    MarginOfSafety,
    MarketSnapshot,
    ValuationAssessment,
    ValuationAssumptions,
    ValuationConfidence,
    ValuationEngine,
    ValuationError,
    ValuationMethod,
    ValuationRange,
)


class TestPublicApi:
    def test_exports(self) -> None:
        assert ValuationEngine is not None
        assert ValuationAssessment is not None
        assert ValuationAssumptions is not None
        assert issubclass(ValuationError, Exception)
        assert ValuationMethod.DCF.value == "dcf"
        assert ValuationConfidence.HIGH.value == "high"

    def test_version(self) -> None:
        import valuation

        assert valuation.__version__ == "0.1.1"


class TestAssumptions:
    def test_defaults(self) -> None:
        a = ValuationAssumptions()
        assert a.discount_rate == 0.10
        assert a.earnings_multiple == 12.0

    def test_terminal_must_be_below_discount(self) -> None:
        with pytest.raises(ValuationError, match="terminal_growth_rate"):
            ValuationAssumptions(discount_rate=0.05, terminal_growth_rate=0.05)

    def test_market_snapshot_rejects_negative(self) -> None:
        from core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            MarketSnapshot(market_cap=-1.0)


class TestModels:
    def test_estimate_applicable_requires_value(self) -> None:
        from core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            IntrinsicValueEstimate(
                method=ValuationMethod.BOOK_VALUE,
                intrinsic_value=None,
                applicable=True,
                formula="IV = E",
                rationale="bad",
            )

    def test_range_and_mos(self) -> None:
        from contracts import MarginOfSafety as ContractsMoS

        vr = ValuationRange(low=100.0, mid=150.0, high=200.0)
        assert vr.mid == 150.0
        mos = MarginOfSafety(
            ratio=0.25,
            intrinsic_value=200.0,
            market_value=150.0,
            available=True,
        )
        assert mos.available is True
        assert MarginOfSafety is ContractsMoS
