"""Tests for portfolio_intelligence_engine.models — HoldingSignal validation."""

from __future__ import annotations

import pytest

from portfolio_intelligence_engine import (
    HoldingSignal,
    PortfolioIntelligenceEngineError,
)


class TestHoldingSignal:
    def test_normalizes_symbol(self) -> None:
        holding = HoldingSignal(symbol=" aapl ", weight=0.1)
        assert holding.symbol == "AAPL"

    def test_rejects_empty_symbol(self) -> None:
        with pytest.raises(PortfolioIntelligenceEngineError):
            HoldingSignal(symbol="  ", weight=0.1)

    def test_to_public_dict_roundtrip(self) -> None:
        holding = HoldingSignal(
            symbol="MSFT",
            weight=0.2,
            sector="Information Technology",
            margin_of_safety=0.1,
        )
        payload = holding.to_public_dict()
        assert payload["symbol"] == "MSFT"
        assert payload["sector"] == "Information Technology"
        assert payload["margin_of_safety"] == 0.1
