"""Tests for Data Engine abstract ports."""

from datetime import UTC, date, datetime

import pytest

from contracts.domain.economic_series import EconomicDataPoint, EconomicSeries
from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from contracts.domain.price_series import PriceSeries
from contracts.domain.signal import Signal
from contracts.enums import (
    BarFrequency,
    EconomicFrequency,
    EngineSource,
    SignalDirection,
    StatementPeriodType,
)
from data_engine.ports import (
    AlternativeDataPort,
    EconomicDataPort,
    FundamentalsDataPort,
    MarketDataPort,
)


class TestMarketDataPort:
    """Tests for the MarketDataPort abstract interface."""

    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            MarketDataPort()  # type: ignore[abstract]

    def test_concrete_implementation_satisfies_interface(
        self, instrument: Instrument, sample_price_series: PriceSeries
    ) -> None:
        class StubMarketDataPort(MarketDataPort):
            def get_price_series(
                self,
                instrument: Instrument,
                frequency: BarFrequency,
                start: date,
                end: date,
            ) -> PriceSeries:
                return sample_price_series

        stub = StubMarketDataPort()
        result = stub.get_price_series(
            instrument, BarFrequency.DAILY, date(2026, 1, 1), date(2026, 1, 31)
        )
        assert result is sample_price_series
        assert isinstance(result, PriceSeries)


class TestFundamentalsDataPort:
    """Tests for the FundamentalsDataPort abstract interface."""

    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            FundamentalsDataPort()  # type: ignore[abstract]

    def test_concrete_implementation_satisfies_interface(
        self, instrument: Instrument
    ) -> None:
        statement = FundamentalStatement(
            instrument=instrument,
            period_end=date(2025, 12, 31),
            period_type=StatementPeriodType.ANNUAL,
            fiscal_year=2025,
            currency="USD",
            revenue=1_000_000.0,
        )

        class StubFundamentalsDataPort(FundamentalsDataPort):
            def get_fundamental_statements(
                self,
                instrument: Instrument,
                period_type: StatementPeriodType,
                *,
                limit: int | None = None,
            ) -> tuple[FundamentalStatement, ...]:
                return (statement,)

        stub = StubFundamentalsDataPort()
        result = stub.get_fundamental_statements(
            instrument, StatementPeriodType.ANNUAL
        )
        assert result == (statement,)


class TestEconomicDataPort:
    """Tests for the EconomicDataPort abstract interface."""

    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            EconomicDataPort()  # type: ignore[abstract]

    def test_concrete_implementation_satisfies_interface(self) -> None:
        series = EconomicSeries(
            indicator_code="CPI",
            indicator_name="Consumer Price Index",
            country="US",
            frequency=EconomicFrequency.MONTHLY,
            points=(EconomicDataPoint(observation_date=date(2026, 1, 1), value=3.1),),
        )

        class StubEconomicDataPort(EconomicDataPort):
            def get_economic_series(
                self, indicator_code: str, country: str
            ) -> EconomicSeries:
                return series

        stub = StubEconomicDataPort()
        assert stub.get_economic_series("CPI", "US") is series


class TestAlternativeDataPort:
    """Tests for the AlternativeDataPort abstract interface."""

    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            AlternativeDataPort()  # type: ignore[abstract]

    def test_concrete_implementation_satisfies_interface(
        self, instrument: Instrument
    ) -> None:
        signal = Signal(
            instrument=instrument,
            source_engine=EngineSource.BEHAVIORAL_ENGINE,
            name="social_sentiment",
            direction=SignalDirection.BULLISH,
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )

        class StubAlternativeDataPort(AlternativeDataPort):
            def get_signals(self, instrument: Instrument) -> tuple[Signal, ...]:
                return (signal,)

        stub = StubAlternativeDataPort()
        assert stub.get_signals(instrument) == (signal,)
