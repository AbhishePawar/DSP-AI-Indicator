"""Tests for ValuationMember."""

from __future__ import annotations

import pytest

from contracts import (
    AssetClass,
    EngineSource,
    Instrument,
    SignalDirection,
    ValuationConfidence,
)

from ai_committee.enums import Decision
from ai_committee.exceptions import CommitteeError
from ai_committee.members import ValuationMember
from ai_committee.members.valuation import map_valuation_decision
from ai_committee.models import CommitteeInput


class TestValuationMember:
    def test_name_and_source(self) -> None:
        member = ValuationMember()
        assert member.name == "valuation"
        assert member.source_engine is EngineSource.VALUATION_ENGINE

    def test_maps_buy(
        self, instrument, technical_factory, fundamental_factory, valuation_factory
    ) -> None:
        assessment = valuation_factory(
            mos_ratio=0.25, confidence=ValuationConfidence.HIGH
        )
        context = CommitteeInput(
            instrument=instrument,
            technical=technical_factory((SignalDirection.NEUTRAL,)),
            fundamental=fundamental_factory((SignalDirection.NEUTRAL,)),
            valuation=assessment,
        )
        opinion = ValuationMember().analyze(context)
        assert opinion.recommendation is Decision.BUY
        assert opinion.source == "valuation"
        assert opinion.confidence == pytest.approx(0.85)
        assert opinion.evidence == assessment.evidence
        assert opinion.margin_of_safety is assessment.margin_of_safety
        assert opinion.valuation_summary is assessment.valuation_summary
        assert "25.00%" in opinion.reasoning
        assert assessment.reasoning in opinion.reasoning

    def test_maps_sell(
        self, instrument, technical_factory, fundamental_factory, valuation_factory
    ) -> None:
        context = CommitteeInput(
            instrument=instrument,
            technical=technical_factory((SignalDirection.NEUTRAL,)),
            fundamental=fundamental_factory((SignalDirection.NEUTRAL,)),
            valuation=valuation_factory(
                mos_ratio=-0.30, confidence=ValuationConfidence.MEDIUM
            ),
        )
        opinion = ValuationMember().analyze(context)
        assert opinion.recommendation is Decision.SELL
        assert opinion.confidence == pytest.approx(0.65)

    def test_maps_hold_narrow_mos(
        self, instrument, technical_factory, fundamental_factory, valuation_factory
    ) -> None:
        context = CommitteeInput(
            instrument=instrument,
            technical=technical_factory((SignalDirection.NEUTRAL,)),
            fundamental=fundamental_factory((SignalDirection.NEUTRAL,)),
            valuation=valuation_factory(
                mos_ratio=0.05, confidence=ValuationConfidence.HIGH
            ),
        )
        opinion = ValuationMember().analyze(context)
        assert opinion.recommendation is Decision.HOLD

    def test_hold_when_mos_unavailable(
        self, instrument, technical_factory, fundamental_factory, valuation_factory
    ) -> None:
        context = CommitteeInput(
            instrument=instrument,
            technical=technical_factory((SignalDirection.NEUTRAL,)),
            fundamental=fundamental_factory((SignalDirection.NEUTRAL,)),
            valuation=valuation_factory(
                mos_ratio=None, confidence=ValuationConfidence.HIGH
            ),
        )
        opinion = ValuationMember().analyze(context)
        assert opinion.recommendation is Decision.HOLD

    def test_hold_when_confidence_low(
        self, instrument, technical_factory, fundamental_factory, valuation_factory
    ) -> None:
        context = CommitteeInput(
            instrument=instrument,
            technical=technical_factory((SignalDirection.NEUTRAL,)),
            fundamental=fundamental_factory((SignalDirection.NEUTRAL,)),
            valuation=valuation_factory(
                mos_ratio=0.40, confidence=ValuationConfidence.LOW
            ),
        )
        opinion = ValuationMember().analyze(context)
        assert opinion.recommendation is Decision.HOLD

    def test_missing_valuation_raises(
        self, instrument, technical_factory, fundamental_factory
    ) -> None:
        context = CommitteeInput(
            instrument=instrument,
            technical=technical_factory((SignalDirection.BULLISH,)),
            fundamental=fundamental_factory((SignalDirection.BULLISH,)),
            valuation=None,
        )
        with pytest.raises(CommitteeError, match="valuation"):
            ValuationMember().analyze(context)

    def test_instrument_mismatch_raises(
        self, instrument, technical_factory, fundamental_factory, valuation_factory
    ) -> None:
        other = Instrument(
            symbol="MSFT", asset_class=AssetClass.EQUITY, currency="USD"
        )
        context = CommitteeInput(
            instrument=instrument,
            technical=technical_factory((SignalDirection.BULLISH,)),
            fundamental=fundamental_factory((SignalDirection.BULLISH,)),
            valuation=valuation_factory(for_instrument=other),
        )
        with pytest.raises(CommitteeError, match="does not match"):
            ValuationMember().analyze(context)

    def test_map_valuation_decision_helpers(self, valuation_factory) -> None:
        assert (
            map_valuation_decision(
                valuation_factory(mos_ratio=0.20, confidence=ValuationConfidence.HIGH)
            )
            is Decision.BUY
        )
        assert (
            map_valuation_decision(
                valuation_factory(mos_ratio=-0.20, confidence=ValuationConfidence.HIGH)
            )
            is Decision.SELL
        )
