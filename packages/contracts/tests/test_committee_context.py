"""Tests for committee context contract DTOs."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from contracts import (
    AnalyticalStance,
    AssetClass,
    EconomicContext,
    EngineSource,
    Evidence,
    FundamentalContext,
    Instrument,
    MarginOfSafety,
    Signal,
    SignalDirection,
    TechnicalContext,
    ValuationConfidence,
    ValuationContext,
    ValuationSummary,
)
from contracts.exceptions import ContractValidationError

FIXED_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def instrument() -> Instrument:
    return Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")


def _signal(instrument: Instrument) -> Signal:
    return Signal(
        instrument=instrument,
        source_engine=EngineSource.INDICATOR_ENGINE,
        name="rsi",
        direction=SignalDirection.BULLISH,
        timestamp=FIXED_NOW,
        value=1.0,
        strength=0.5,
    )


def _evidence() -> Evidence:
    return Evidence(
        source_engine=EngineSource.VALUATION_ENGINE,
        claim="support",
        value=1.0,
        reference="test",
        weight=0.5,
    )


class TestCommitteeContexts:
    def test_technical_and_fundamental(self, instrument: Instrument) -> None:
        signal = _signal(instrument)
        tech = TechnicalContext(
            instrument=instrument, signals=(signal,), evidence=()
        )
        fund = FundamentalContext(
            instrument=instrument, signals=(signal,), evidence=()
        )
        assert tech.signals == (signal,)
        assert fund.instrument is instrument

    def test_economic_normalizes(self) -> None:
        ctx = EconomicContext(
            stance=AnalyticalStance.HOLD,
            overall_condition="SLOWING",
            country="US",
            reasoning="Mixed macro.",
            evidence=(_evidence(),),
        )
        assert ctx.overall_condition == "slowing"

    def test_economic_rejects_empty_reasoning(self) -> None:
        with pytest.raises(ContractValidationError, match="reasoning"):
            EconomicContext(
                stance=AnalyticalStance.BUY,
                overall_condition="expansion",
                country="US",
                reasoning="  ",
            )

    def test_valuation_context(self, instrument: Instrument) -> None:
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
            confidence="high",
            currency="USD",
            as_of=date(2024, 1, 1),
        )
        ctx = ValuationContext(
            instrument=instrument,
            margin_of_safety=mos,
            valuation_summary=summary,
            confidence=ValuationConfidence.HIGH,
            reasoning="Undervalued.",
            evidence=(_evidence(),),
        )
        assert ctx.confidence is ValuationConfidence.HIGH
        assert ctx.margin_of_safety is mos
