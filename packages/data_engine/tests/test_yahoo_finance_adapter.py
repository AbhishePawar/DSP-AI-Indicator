"""Tests for ``YahooFinanceAdapter``.

All tests inject a fake ``JsonHttpClient`` implementation and never
touch the network. Test names track the categories the sprint mission
calls out explicitly: successful retrieval, normalization, validation,
error handling, empty responses, and invalid payloads.
"""

from collections.abc import Mapping
from datetime import date
from typing import Any

import pytest

from contracts.domain.instrument import Instrument
from contracts.domain.price_series import PriceSeries
from contracts.enums import AssetClass, BarFrequency
from data_engine.adapters.yahoo_finance.adapter import YahooFinanceAdapter
from data_engine.exceptions import (
    DataEngineError,
    InvalidProviderDataError,
    MissingFieldError,
    ProviderRequestError,
)

_AAPL_TIMESTAMPS = (1704240000, 1704326400, 1704412800)  # 2024-01-03..05 (UTC)


class _FakeHttpClient:
    """Stub ``JsonHttpClient`` that returns a canned payload or raises."""

    def __init__(
        self,
        payload: Mapping[str, Any] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._payload = payload
        self._error = error
        self.last_url: str | None = None
        self.last_params: Mapping[str, str] | None = None

    def get_json(
        self, url: str, *, params: Mapping[str, str] | None = None
    ) -> Mapping[str, Any]:
        self.last_url = url
        self.last_params = params
        if self._error is not None:
            raise self._error
        assert self._payload is not None
        return self._payload


def _chart_payload(
    *,
    timestamps: tuple[Any, ...] = _AAPL_TIMESTAMPS,
    opens: tuple[Any, ...] = (185.0, 186.0, 187.0),
    highs: tuple[Any, ...] = (186.5, 187.5, 188.5),
    lows: tuple[Any, ...] = (184.5, 185.5, 186.5),
    closes: tuple[Any, ...] = (186.0, 187.0, 188.0),
    volumes: tuple[Any, ...] = (1_000_000, 1_100_000, 1_200_000),
    adjcloses: tuple[Any, ...] | None = (185.9, 186.9, 187.9),
) -> dict[str, Any]:
    """Build a realistic Yahoo Finance ``chart`` API response payload."""
    return {
        "chart": {
            "result": [
                {
                    "meta": {"symbol": "AAPL"},
                    "timestamp": list(timestamps),
                    "indicators": {
                        "quote": [
                            {
                                "open": list(opens),
                                "high": list(highs),
                                "low": list(lows),
                                "close": list(closes),
                                "volume": list(volumes),
                            }
                        ],
                        "adjclose": (
                            [{"adjclose": list(adjcloses)}]
                            if adjcloses is not None
                            else [{}]
                        ),
                    },
                }
            ],
            "error": None,
        }
    }


@pytest.fixture
def instrument() -> Instrument:
    return Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")


@pytest.fixture
def date_range() -> tuple[date, date]:
    return date(2024, 1, 1), date(2024, 1, 5)


class TestSuccessfulRetrieval:
    def test_returns_price_series_with_expected_bars(
        self, instrument: Instrument, date_range: tuple[date, date]
    ) -> None:
        client = _FakeHttpClient(_chart_payload())
        adapter = YahooFinanceAdapter(http_client=client)

        series = adapter.get_price_series(
            instrument, BarFrequency.DAILY, *date_range
        )

        assert isinstance(series, PriceSeries)
        assert series.instrument is instrument
        assert series.frequency is BarFrequency.DAILY
        assert len(series.bars) == 3
        assert series.bars[0].close == pytest.approx(186.0)
        assert series.bars[0].adjusted_close == pytest.approx(185.9)

    def test_requests_daily_interval_for_the_requested_range(
        self, instrument: Instrument, date_range: tuple[date, date]
    ) -> None:
        client = _FakeHttpClient(_chart_payload())
        adapter = YahooFinanceAdapter(http_client=client)

        adapter.get_price_series(instrument, BarFrequency.DAILY, *date_range)

        expected_url = "https://query1.finance.yahoo.com/v8/finance/chart/AAPL"
        assert client.last_url == expected_url
        assert client.last_params is not None
        assert client.last_params["interval"] == "1d"
        assert int(client.last_params["period1"]) < int(client.last_params["period2"])

    def test_provider_name_is_yahoo_finance(self) -> None:
        assert YahooFinanceAdapter().provider_name == "yahoo_finance"


class TestNormalization:
    def test_skips_fully_null_bars_representing_no_trading_session(
        self, instrument: Instrument, date_range: tuple[date, date]
    ) -> None:
        payload = _chart_payload(
            timestamps=(*_AAPL_TIMESTAMPS, 1704499200),
            opens=(185.0, 186.0, 187.0, None),
            highs=(186.5, 187.5, 188.5, None),
            lows=(184.5, 185.5, 186.5, None),
            closes=(186.0, 187.0, 188.0, None),
            volumes=(1_000_000, 1_100_000, 1_200_000, None),
            adjcloses=(185.9, 186.9, 187.9, None),
        )
        client = _FakeHttpClient(payload)
        adapter = YahooFinanceAdapter(http_client=client)

        series = adapter.get_price_series(
            instrument, BarFrequency.DAILY, *date_range
        )

        assert len(series.bars) == 3

    def test_normalizes_epoch_timestamps_into_datetimes(
        self, instrument: Instrument, date_range: tuple[date, date]
    ) -> None:
        client = _FakeHttpClient(_chart_payload())
        adapter = YahooFinanceAdapter(http_client=client)

        series = adapter.get_price_series(
            instrument, BarFrequency.DAILY, *date_range
        )

        assert series.bars[0].timestamp.year == 2024


class TestValidation:
    def test_inconsistent_ohlc_raises_invalid_provider_data_error(
        self, instrument: Instrument, date_range: tuple[date, date]
    ) -> None:
        payload = _chart_payload(highs=(180.0, 187.5, 188.5))  # high < low for bar 0
        client = _FakeHttpClient(payload)
        adapter = YahooFinanceAdapter(http_client=client)

        with pytest.raises(InvalidProviderDataError):
            adapter.get_price_series(instrument, BarFrequency.DAILY, *date_range)

    def test_partial_null_bar_raises_missing_field_error(
        self, instrument: Instrument, date_range: tuple[date, date]
    ) -> None:
        payload = _chart_payload(closes=(186.0, None, 188.0))
        client = _FakeHttpClient(payload)
        adapter = YahooFinanceAdapter(http_client=client)

        with pytest.raises(MissingFieldError):
            adapter.get_price_series(instrument, BarFrequency.DAILY, *date_range)

    def test_negative_volume_raises_invalid_provider_data_error(
        self, instrument: Instrument, date_range: tuple[date, date]
    ) -> None:
        payload = _chart_payload(volumes=(1_000_000, -5, 1_200_000))
        client = _FakeHttpClient(payload)
        adapter = YahooFinanceAdapter(http_client=client)

        with pytest.raises(InvalidProviderDataError):
            adapter.get_price_series(instrument, BarFrequency.DAILY, *date_range)


class TestErrorHandling:
    def test_transport_failure_propagates_as_provider_request_error(
        self, instrument: Instrument, date_range: tuple[date, date]
    ) -> None:
        client = _FakeHttpClient(error=ProviderRequestError("network unreachable"))
        adapter = YahooFinanceAdapter(http_client=client)

        with pytest.raises(ProviderRequestError):
            adapter.get_price_series(instrument, BarFrequency.DAILY, *date_range)

    def test_unexpected_http_client_exception_is_translated(
        self, instrument: Instrument, date_range: tuple[date, date]
    ) -> None:
        client = _FakeHttpClient(error=ValueError("boom, some non-DataEngine error"))
        adapter = YahooFinanceAdapter(http_client=client)

        with pytest.raises(DataEngineError):
            adapter.get_price_series(instrument, BarFrequency.DAILY, *date_range)

    def test_provider_reported_error_raises_invalid_provider_data_error(
        self, instrument: Instrument, date_range: tuple[date, date]
    ) -> None:
        payload = {
            "chart": {
                "result": None,
                "error": {"code": "Not Found", "description": "No data found"},
            }
        }
        client = _FakeHttpClient(payload)
        adapter = YahooFinanceAdapter(http_client=client)

        with pytest.raises(InvalidProviderDataError):
            adapter.get_price_series(instrument, BarFrequency.DAILY, *date_range)

    def test_non_daily_frequency_is_rejected(
        self, instrument: Instrument, date_range: tuple[date, date]
    ) -> None:
        client = _FakeHttpClient(_chart_payload())
        adapter = YahooFinanceAdapter(http_client=client)

        with pytest.raises(DataEngineError):
            adapter.get_price_series(instrument, BarFrequency.WEEKLY, *date_range)


class TestEmptyResponses:
    def test_empty_result_list_raises_invalid_provider_data_error(
        self, instrument: Instrument, date_range: tuple[date, date]
    ) -> None:
        payload = {"chart": {"result": [], "error": None}}
        client = _FakeHttpClient(payload)
        adapter = YahooFinanceAdapter(http_client=client)

        with pytest.raises(InvalidProviderDataError):
            adapter.get_price_series(instrument, BarFrequency.DAILY, *date_range)

    def test_empty_timestamp_array_raises_invalid_provider_data_error(
        self, instrument: Instrument, date_range: tuple[date, date]
    ) -> None:
        payload = _chart_payload(
            timestamps=(),
            opens=(),
            highs=(),
            lows=(),
            closes=(),
            volumes=(),
            adjcloses=(),
        )
        client = _FakeHttpClient(payload)
        adapter = YahooFinanceAdapter(http_client=client)

        with pytest.raises(InvalidProviderDataError):
            adapter.get_price_series(instrument, BarFrequency.DAILY, *date_range)


class TestInvalidPayloads:
    def test_missing_chart_key_raises_invalid_provider_data_error(
        self, instrument: Instrument, date_range: tuple[date, date]
    ) -> None:
        client = _FakeHttpClient({"unexpected": "shape"})
        adapter = YahooFinanceAdapter(http_client=client)

        with pytest.raises(InvalidProviderDataError):
            adapter.get_price_series(instrument, BarFrequency.DAILY, *date_range)

    def test_chart_not_a_mapping_raises_invalid_provider_data_error(
        self, instrument: Instrument, date_range: tuple[date, date]
    ) -> None:
        client = _FakeHttpClient({"chart": "not-a-mapping"})
        adapter = YahooFinanceAdapter(http_client=client)

        with pytest.raises(InvalidProviderDataError):
            adapter.get_price_series(instrument, BarFrequency.DAILY, *date_range)
