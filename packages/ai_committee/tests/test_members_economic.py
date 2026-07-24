"""Tests for EconomicMember."""

from __future__ import annotations

import pytest

from contracts import AnalyticalStance, EngineSource, SignalDirection

from ai_committee.enums import Decision
from ai_committee.exceptions import CommitteeError
from ai_committee.members import EconomicMember
from ai_committee.models import CommitteeInput


class TestEconomicMember:
    """EconomicContext → Opinion mapping."""

    def test_name_and_source(self) -> None:
        member = EconomicMember()
        assert member.name == "economic"
        assert member.source_engine is EngineSource.ECONOMIC_ENGINE

    def test_maps_buy(
        self, instrument, technical_factory, fundamental_factory, economic_factory
    ) -> None:
        assessment = economic_factory(AnalyticalStance.BUY)
        context = CommitteeInput(
            instrument=instrument,
            technical=technical_factory((SignalDirection.NEUTRAL,)),
            fundamental=fundamental_factory((SignalDirection.NEUTRAL,)),
            economic=assessment,
        )
        opinion = EconomicMember().analyze(context)
        assert opinion.recommendation is Decision.BUY
        assert opinion.source == "economic"
        assert opinion.confidence is None
        assert opinion.evidence == assessment.evidence
        assert assessment.reasoning in opinion.reasoning
        assert "expansion" in opinion.reasoning.lower()

    def test_maps_sell(
        self, instrument, technical_factory, fundamental_factory, economic_factory
    ) -> None:
        context = CommitteeInput(
            instrument=instrument,
            technical=technical_factory((SignalDirection.NEUTRAL,)),
            fundamental=fundamental_factory((SignalDirection.NEUTRAL,)),
            economic=economic_factory(AnalyticalStance.SELL),
        )
        opinion = EconomicMember().analyze(context)
        assert opinion.recommendation is Decision.SELL

    def test_maps_hold(
        self, instrument, technical_factory, fundamental_factory, economic_factory
    ) -> None:
        context = CommitteeInput(
            instrument=instrument,
            technical=technical_factory((SignalDirection.NEUTRAL,)),
            fundamental=fundamental_factory((SignalDirection.NEUTRAL,)),
            economic=economic_factory(AnalyticalStance.HOLD),
        )
        opinion = EconomicMember().analyze(context)
        assert opinion.recommendation is Decision.HOLD

    def test_missing_economic_raises(
        self, instrument, technical_factory, fundamental_factory
    ) -> None:
        context = CommitteeInput(
            instrument=instrument,
            technical=technical_factory((SignalDirection.BULLISH,)),
            fundamental=fundamental_factory((SignalDirection.BULLISH,)),
            economic=None,
        )
        with pytest.raises(CommitteeError, match="economic"):
            EconomicMember().analyze(context)
