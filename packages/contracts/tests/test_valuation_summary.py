"""Tests for ValuationSummary shared-kernel contract."""

from __future__ import annotations

from datetime import date

import pytest

from contracts import MarginOfSafety, ValuationSummary
from contracts.exceptions import ContractValidationError


class TestValuationSummary:
    def test_constructs(self) -> None:
        mos = MarginOfSafety(
            ratio=0.2,
            intrinsic_value=100.0,
            market_value=80.0,
            available=True,
        )
        summary = ValuationSummary(
            intrinsic_low=90.0,
            intrinsic_mid=100.0,
            intrinsic_high=110.0,
            margin_of_safety=mos,
            confidence="HIGH",
            currency="usd",
            as_of=date(2024, 1, 1),
        )
        assert summary.confidence == "high"
        assert summary.currency == "USD"
        assert summary.margin_of_safety is mos

    def test_rejects_inverted_range(self) -> None:
        mos = MarginOfSafety(
            ratio=None,
            intrinsic_value=None,
            market_value=None,
            available=False,
        )
        with pytest.raises(ContractValidationError, match="intrinsic_low"):
            ValuationSummary(
                intrinsic_low=120.0,
                intrinsic_mid=100.0,
                intrinsic_high=90.0,
                margin_of_safety=mos,
                confidence="low",
                currency="USD",
                as_of=date(2024, 1, 1),
            )
