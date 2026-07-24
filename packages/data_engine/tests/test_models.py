"""Tests for data_engine.models."""

from datetime import date

import pytest

from contracts.domain.instrument import Instrument
from contracts.enums import BarFrequency, StatementPeriodType
from data_engine.exceptions import DataEngineError
from data_engine.models import EconomicRequest, FundamentalsRequest, PriceSeriesRequest


class TestPriceSeriesRequest:
    """Tests for the PriceSeriesRequest internal model."""

    def test_valid_request_is_constructed(self, instrument: Instrument) -> None:
        request = PriceSeriesRequest(
            instrument=instrument,
            frequency=BarFrequency.DAILY,
            start=date(2026, 1, 1),
            end=date(2026, 1, 31),
        )
        assert request.provider_name is None

    def test_start_after_end_raises(self, instrument: Instrument) -> None:
        with pytest.raises(DataEngineError, match="must not be after"):
            PriceSeriesRequest(
                instrument=instrument,
                frequency=BarFrequency.DAILY,
                start=date(2026, 1, 31),
                end=date(2026, 1, 1),
            )

    def test_start_equal_end_is_valid(self, instrument: Instrument) -> None:
        request = PriceSeriesRequest(
            instrument=instrument,
            frequency=BarFrequency.DAILY,
            start=date(2026, 1, 1),
            end=date(2026, 1, 1),
        )
        assert request.start == request.end


class TestFundamentalsRequest:
    def test_valid_request(self, instrument: Instrument) -> None:
        request = FundamentalsRequest(
            instrument=instrument, period_type=StatementPeriodType.ANNUAL, limit=4
        )
        assert request.provider_name is None
        assert request.limit == 4

    def test_negative_limit_raises(self, instrument: Instrument) -> None:
        with pytest.raises(DataEngineError, match="limit"):
            FundamentalsRequest(
                instrument=instrument,
                period_type=StatementPeriodType.QUARTERLY,
                limit=-1,
            )


class TestEconomicRequest:
    def test_valid_request(self) -> None:
        request = EconomicRequest(indicator_code="GDP", country="US", limit=12)
        assert request.provider_name is None
        assert request.limit == 12

    def test_empty_indicator_raises(self) -> None:
        with pytest.raises(DataEngineError, match="indicator_code"):
            EconomicRequest(indicator_code="  ", country="US")

    def test_negative_limit_raises(self) -> None:
        with pytest.raises(DataEngineError, match="limit"):
            EconomicRequest(indicator_code="GDP", country="US", limit=-1)
