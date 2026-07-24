"""Tests for MarginOfSafety shared-kernel contract."""

from __future__ import annotations

import pytest

from contracts import MARKET_CAPITALIZATION_KEY, MarginOfSafety
from contracts.exceptions import ContractValidationError


class TestMarginOfSafety:
    def test_available_mos(self) -> None:
        mos = MarginOfSafety(
            ratio=0.25,
            intrinsic_value=1000.0,
            market_value=750.0,
            available=True,
        )
        assert mos.available is True
        assert mos.ratio == pytest.approx(0.25)

    def test_unavailable_mos(self) -> None:
        mos = MarginOfSafety(
            ratio=None,
            intrinsic_value=1000.0,
            market_value=None,
            available=False,
        )
        assert mos.available is False
        assert mos.ratio is None

    def test_available_requires_ratio(self) -> None:
        with pytest.raises(ContractValidationError, match="ratio"):
            MarginOfSafety(
                ratio=None,
                intrinsic_value=100.0,
                market_value=80.0,
                available=True,
            )

    def test_unavailable_forbids_ratio(self) -> None:
        with pytest.raises(ContractValidationError, match="ratio"):
            MarginOfSafety(
                ratio=0.1,
                intrinsic_value=100.0,
                market_value=90.0,
                available=False,
            )

    def test_rejects_negative_market_value(self) -> None:
        with pytest.raises(ContractValidationError, match="market_value"):
            MarginOfSafety(
                ratio=0.1,
                intrinsic_value=100.0,
                market_value=-1.0,
                available=True,
            )

    def test_canonical_market_cap_key(self) -> None:
        assert MARKET_CAPITALIZATION_KEY == "market_capitalization"
