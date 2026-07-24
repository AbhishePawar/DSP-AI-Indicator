"""Tests for TechnicalMember and FundamentalMember."""

from __future__ import annotations

import pytest

from contracts.enums import EngineSource, SignalDirection

from ai_committee.enums import Decision
from ai_committee.exceptions import CommitteeError
from ai_committee.members import FundamentalMember, TechnicalMember
from ai_committee.models import CommitteeInput


class TestTechnicalMember:
    """Tests for the Indicator Engine liaison member."""

    def test_name_and_source(self) -> None:
        member = TechnicalMember()
        assert member.name == "technical"
        assert member.source_engine is EngineSource.INDICATOR_ENGINE

    def test_analyze_buy(
        self, instrument, technical_factory, fundamental_factory
    ) -> None:
        context = CommitteeInput(
            instrument=instrument,
            technical=technical_factory(
                (SignalDirection.BULLISH, SignalDirection.BULLISH)
            ),
            fundamental=fundamental_factory((SignalDirection.NEUTRAL,)),
        )
        opinion = TechnicalMember().analyze(context)
        assert opinion.recommendation is Decision.BUY
        assert opinion.source == "technical"
        assert opinion.confidence is None
        assert len(opinion.evidence) == 2

    def test_analyze_hold_on_tie(
        self, instrument, technical_factory, fundamental_factory
    ) -> None:
        context = CommitteeInput(
            instrument=instrument,
            technical=technical_factory(
                (SignalDirection.BULLISH, SignalDirection.BEARISH)
            ),
            fundamental=fundamental_factory((SignalDirection.NEUTRAL,)),
        )
        opinion = TechnicalMember().analyze(context)
        assert opinion.recommendation is Decision.HOLD

    def test_missing_technical_raises(
        self, instrument, fundamental_factory
    ) -> None:
        context = CommitteeInput(
            instrument=instrument,
            technical=None,
            fundamental=fundamental_factory((SignalDirection.BULLISH,)),
        )
        with pytest.raises(CommitteeError, match="technical"):
            TechnicalMember().analyze(context)

    def test_instrument_mismatch_raises(
        self, instrument, technical_factory, fundamental_factory
    ) -> None:
        from contracts.domain.instrument import Instrument
        from contracts.enums import AssetClass

        other = Instrument(
            symbol="MSFT", asset_class=AssetClass.EQUITY, currency="USD"
        )
        context = CommitteeInput(
            instrument=instrument,
            technical=technical_factory(
                (SignalDirection.BULLISH,), for_instrument=other
            ),
            fundamental=fundamental_factory((SignalDirection.BULLISH,)),
        )
        with pytest.raises(CommitteeError, match="does not match"):
            TechnicalMember().analyze(context)


class TestFundamentalMember:
    """Tests for the Fundamental Engine liaison member."""

    def test_name_and_source(self) -> None:
        member = FundamentalMember()
        assert member.name == "fundamental"
        assert member.source_engine is EngineSource.FUNDAMENTAL_ENGINE

    def test_analyze_sell(
        self, instrument, technical_factory, fundamental_factory
    ) -> None:
        context = CommitteeInput(
            instrument=instrument,
            technical=technical_factory((SignalDirection.NEUTRAL,)),
            fundamental=fundamental_factory(
                (SignalDirection.BEARISH, SignalDirection.BEARISH)
            ),
        )
        opinion = FundamentalMember().analyze(context)
        assert opinion.recommendation is Decision.SELL
        assert opinion.source == "fundamental"

    def test_missing_fundamental_raises(
        self, instrument, technical_factory
    ) -> None:
        context = CommitteeInput(
            instrument=instrument,
            technical=technical_factory((SignalDirection.BULLISH,)),
            fundamental=None,
        )
        with pytest.raises(CommitteeError, match="fundamental"):
            FundamentalMember().analyze(context)

    def test_instrument_mismatch_raises(
        self, instrument, technical_factory, fundamental_factory
    ) -> None:
        from contracts.domain.instrument import Instrument
        from contracts.enums import AssetClass

        other = Instrument(
            symbol="MSFT", asset_class=AssetClass.EQUITY, currency="USD"
        )
        context = CommitteeInput(
            instrument=instrument,
            technical=technical_factory((SignalDirection.BULLISH,)),
            fundamental=fundamental_factory(
                (SignalDirection.BULLISH,), for_instrument=other
            ),
        )
        with pytest.raises(CommitteeError, match="does not match"):
            FundamentalMember().analyze(context)
