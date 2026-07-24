"""Tests for EconomicSnapshot, EconomicSignal, EconomicAssessment."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from contracts.domain.evidence import Evidence
from contracts.enums import EngineSource, SignalDirection
from core.exceptions import ValidationError

from economic.enums import EconomicCondition, Recommendation
from economic.models import (
    EconomicAssessment,
    EconomicSignal,
    EconomicSnapshot,
)

FIXED_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


class TestEconomicSnapshot:
    """Snapshot validation."""

    def test_normalizes_country(self) -> None:
        snap = EconomicSnapshot(as_of=date(2024, 1, 1), country=" us ")
        assert snap.country == "US"

    def test_empty_country_raises(self) -> None:
        with pytest.raises(ValidationError, match="country"):
            EconomicSnapshot(as_of=date(2024, 1, 1), country="  ")

    def test_invalid_liquidity_raises(self) -> None:
        with pytest.raises(ValidationError, match="liquidity"):
            EconomicSnapshot(
                as_of=date(2024, 1, 1),
                liquidity_indicator=1.5,
            )


class TestEconomicSignal:
    """Signal validation."""

    def test_normalizes_name(self) -> None:
        signal = EconomicSignal(
            name="  GDP  ",
            direction=SignalDirection.BULLISH,
            observation="Strong GDP Growth",
            reasoning="Growth is strong.",
            value=0.04,
        )
        assert signal.name == "gdp"

    def test_empty_observation_raises(self) -> None:
        with pytest.raises(ValidationError, match="observation"):
            EconomicSignal(
                name="gdp",
                direction=SignalDirection.NEUTRAL,
                observation="  ",
                reasoning="x",
            )

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValidationError, match="name"):
            EconomicSignal(
                name="  ",
                direction=SignalDirection.NEUTRAL,
                observation="x",
                reasoning="x",
            )

    def test_empty_reasoning_raises(self) -> None:
        with pytest.raises(ValidationError, match="reasoning"):
            EconomicSignal(
                name="gdp",
                direction=SignalDirection.NEUTRAL,
                observation="x",
                reasoning="  ",
            )


class TestEconomicAssessment:
    """Assessment validation."""

    def test_requires_signals(self) -> None:
        with pytest.raises(ValidationError, match="detected_signals"):
            EconomicAssessment(
                overall_condition=EconomicCondition.SLOWING,
                recommendation=Recommendation.HOLD,
                reasoning="Mixed.",
                evidence=(),
                detected_signals=(),
                as_of=date(2024, 1, 1),
                assessed_at=FIXED_NOW,
                country="US",
            )

    def test_valid_assessment(self) -> None:
        signal = EconomicSignal(
            name="gdp",
            direction=SignalDirection.BULLISH,
            observation="Strong GDP Growth",
            reasoning="Strong.",
            value=0.04,
        )
        evidence = Evidence(
            source_engine=EngineSource.ECONOMIC_ENGINE,
            claim="Strong.",
            value=0.04,
            reference="Strong GDP Growth",
        )
        assessment = EconomicAssessment(
            overall_condition=EconomicCondition.EXPANSION,
            recommendation=Recommendation.BUY,
            reasoning="Broadly bullish.",
            evidence=(evidence,),
            detected_signals=(signal,),
            as_of=date(2024, 1, 1),
            assessed_at=FIXED_NOW,
            country="US",
        )
        assert assessment.recommendation is Recommendation.BUY

    def test_empty_assessment_reasoning_raises(self) -> None:
        signal = EconomicSignal(
            name="gdp",
            direction=SignalDirection.NEUTRAL,
            observation="x",
            reasoning="x",
        )
        with pytest.raises(ValidationError, match="reasoning"):
            EconomicAssessment(
                overall_condition=EconomicCondition.SLOWING,
                recommendation=Recommendation.HOLD,
                reasoning="  ",
                evidence=(),
                detected_signals=(signal,),
                as_of=date(2024, 1, 1),
                assessed_at=FIXED_NOW,
                country="US",
            )
