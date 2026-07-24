"""Tests for ``FredEconomicAdapter``."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

import pytest

from contracts.domain.economic_series import EconomicSeries
from contracts.enums import EconomicFrequency
from data_engine.adapters.fred.adapter import FredEconomicAdapter
from data_engine.exceptions import (
    DataEngineError,
    InvalidProviderDataError,
    ProviderRequestError,
)


def _fred_payload(
    observations: list[dict[str, Any]] | None = None,
    *,
    error_message: str | None = None,
) -> dict[str, Any]:
    if observations is None:
        observations = [
            {"date": "2023-01-01", "value": "100.0"},
            {"date": "2023-04-01", "value": "."},
            {"date": "2023-07-01", "value": "102.5"},
        ]
    payload: dict[str, Any] = {"observations": observations}
    if error_message is not None:
        payload["error_message"] = error_message
    return payload


class _FakeHttpClient:
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
        self.call_count = 0

    def get_json(
        self, url: str, *, params: Mapping[str, str] | None = None
    ) -> Mapping[str, Any]:
        self.call_count += 1
        self.last_url = url
        self.last_params = params
        if self._error is not None:
            raise self._error
        assert self._payload is not None
        return self._payload


class TestSuccessfulRetrieval:
    def test_returns_economic_series(self) -> None:
        adapter = FredEconomicAdapter(http_client=_FakeHttpClient(_fred_payload()))
        series = adapter.get_economic_series("GDP", "US")

        assert isinstance(series, EconomicSeries)
        assert series.indicator_code == "GDP"
        assert series.frequency is EconomicFrequency.QUARTERLY
        assert len(series.points) == 2
        assert series.points[0].observation_date == date(2023, 1, 1)
        assert series.points[1].value == pytest.approx(102.5)

    def test_maps_aliases_to_canonical_codes(self) -> None:
        client = _FakeHttpClient(_fred_payload())
        adapter = FredEconomicAdapter(http_client=client)
        series = adapter.get_economic_series("INFLATION", "us")
        assert series.indicator_code == "CPI"
        assert client.last_params is not None
        assert client.last_params["series_id"] == "CPIAUCSL"

    def test_requests_expected_params(self) -> None:
        client = _FakeHttpClient(_fred_payload())
        adapter = FredEconomicAdapter(http_client=client, api_key="test-key")
        adapter.get_economic_series("INTEREST_RATE", "US")
        assert client.last_params is not None
        assert client.last_params["series_id"] == "FEDFUNDS"
        assert client.last_params["api_key"] == "test-key"
        assert client.last_params["file_type"] == "json"

    def test_provider_name(self) -> None:
        assert FredEconomicAdapter(http_client=_FakeHttpClient({})).provider_name == "fred"

    def test_deterministic(self) -> None:
        payload = _fred_payload()
        a = FredEconomicAdapter(http_client=_FakeHttpClient(payload)).get_economic_series(
            "GDP", "US"
        )
        b = FredEconomicAdapter(http_client=_FakeHttpClient(payload)).get_economic_series(
            "GDP", "US"
        )
        assert a == b


class TestMissingAndPartial:
    def test_partial_dataset_skips_missing_values(self) -> None:
        adapter = FredEconomicAdapter(
            http_client=_FakeHttpClient(
                _fred_payload(
                    [
                        {"date": "2023-01-01", "value": "1.0"},
                        {"date": "2023-02-01", "value": "."},
                        {"date": "2023-03-01", "value": "3.0"},
                    ]
                )
            )
        )
        series = adapter.get_economic_series("UNEMPLOYMENT", "US")
        assert [p.value for p in series.points] == [1.0, 3.0]

    def test_unsupported_indicator_raises(self) -> None:
        adapter = FredEconomicAdapter(http_client=_FakeHttpClient(_fred_payload()))
        with pytest.raises(DataEngineError, match="unsupported"):
            adapter.get_economic_series("VIX", "US")

    def test_non_us_country_raises(self) -> None:
        adapter = FredEconomicAdapter(http_client=_FakeHttpClient(_fred_payload()))
        with pytest.raises(DataEngineError, match="US"):
            adapter.get_economic_series("GDP", "GB")


class TestValidationFailures:
    def test_error_message_raises(self) -> None:
        adapter = FredEconomicAdapter(
            http_client=_FakeHttpClient(
                _fred_payload(error_message="Bad Request. The series does not exist.")
            )
        )
        with pytest.raises(InvalidProviderDataError, match="reported an error"):
            adapter.get_economic_series("GDP", "US")

    def test_missing_observations_field_raises(self) -> None:
        adapter = FredEconomicAdapter(http_client=_FakeHttpClient({"foo": []}))
        with pytest.raises(InvalidProviderDataError, match="observations"):
            adapter.get_economic_series("GDP", "US")

    def test_all_missing_values_raises(self) -> None:
        adapter = FredEconomicAdapter(
            http_client=_FakeHttpClient(
                _fred_payload([{"date": "2023-01-01", "value": "."}])
            )
        )
        with pytest.raises(InvalidProviderDataError, match="no usable"):
            adapter.get_economic_series("GDP", "US")

    def test_http_failure(self) -> None:
        adapter = FredEconomicAdapter(
            http_client=_FakeHttpClient(error=ProviderRequestError("down"))
        )
        with pytest.raises(ProviderRequestError, match="down"):
            adapter.get_economic_series("GDP", "US")

    def test_live_client_requires_api_key(self) -> None:
        adapter = FredEconomicAdapter(api_key=None)
        with pytest.raises(DataEngineError, match="api_key"):
            adapter.get_economic_series("GDP", "US")
