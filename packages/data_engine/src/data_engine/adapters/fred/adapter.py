"""Concrete FRED macroeconomic adapter.

This is the platform's first real ``EconomicDataPort`` integration. It
is the only class that knows FRED's observations API URL shape, missing
value sentinel (``"."``), and series-id catalog. Everything downstream
(``DefaultEconomicNormalizer``, ``EconomicDataService``, the Economic
Engine) only ever sees ``contracts.EconomicSeries``.

Scope: US macroeconomic series listed in
:mod:`data_engine.adapters.fred.catalog` (GDP, CPI, interest rate, PMI,
M2/liquidity, unemployment, industrial production). Additional countries
or series require a new adapter or catalog extension — not a change to
the Economic Engine.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from contracts.domain.economic_series import EconomicSeries
from data_engine.adapters import BaseAdapter
from data_engine.adapters.fred.catalog import FredSeriesSpec, resolve_fred_series
from data_engine.adapters.yahoo_finance.http_client import (
    JsonHttpClient,
    UrllibJsonHttpClient,
)
from data_engine.exceptions import (
    DataEngineError,
    InvalidProviderDataError,
    TransformationError,
)
from data_engine.normalization import DefaultEconomicNormalizer, EconomicDataNormalizer
from data_engine.ports import EconomicDataPort
from data_engine.raw_models import RawEconomicDataPoint, RawEconomicSeries

__all__ = ["FredEconomicAdapter"]

_DEFAULT_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
_PROVIDER_ID = "fred"


class FredEconomicAdapter(BaseAdapter, EconomicDataPort):
    """Retrieves macroeconomic series from the St. Louis Fed FRED API.

    Responsibilities, and nothing more:

    1. Resolve a platform indicator code to a FRED series id via the
       local catalog.
    2. Fetch observations via an injected :class:`JsonHttpClient`.
    3. Map the payload onto :class:`RawEconomicSeries`.
    4. Hand the raw series to a :class:`EconomicDataNormalizer` and
       return the validated ``contracts.EconomicSeries``.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        http_client: JsonHttpClient | None = None,
        normalizer: EconomicDataNormalizer | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout_seconds: float = 10.0,
    ) -> None:
        """Initialize the adapter.

        Args:
            api_key: FRED API key. Required for live requests; tests
                inject a fake ``http_client`` and may omit the key.
            http_client: The HTTP client to use. Defaults to
                :class:`UrllibJsonHttpClient`.
            normalizer: Defaults to :class:`DefaultEconomicNormalizer`.
            base_url: FRED observations endpoint base URL.
            timeout_seconds: Timeout for the default HTTP client.
        """
        self._api_key = api_key
        self._http_client = http_client or UrllibJsonHttpClient(
            timeout_seconds=timeout_seconds
        )
        self._normalizer = normalizer or DefaultEconomicNormalizer()
        self._base_url = base_url

    @property
    def provider_name(self) -> str:
        """Return the canonical id this adapter registers under."""
        return _PROVIDER_ID

    def get_economic_series(self, indicator_code: str, country: str) -> EconomicSeries:
        """Retrieve one macroeconomic series.

        Args:
            indicator_code: Provider-agnostic code (e.g. ``"GDP"``,
                ``"CPI"``) or a documented alias.
            country: ISO 3166-1 alpha-2 country code (``"US"`` only for
                this adapter).

        Returns:
            A validated ``EconomicSeries``.

        Raises:
            DataEngineError: If the indicator/country is unsupported or
                ``api_key`` is missing for a live request.
            ProviderRequestError: If the HTTP request fails.
            InvalidProviderDataError: If FRED's response is malformed or
                contains no usable observations.
            TransformationError: If normalization fails unexpectedly.
        """
        spec = resolve_fred_series(indicator_code, country)
        payload = self._fetch_observations(spec.fred_series_id)
        raw = self._to_raw_series(payload, spec)

        if not raw.points:
            msg = (
                f"fred returned no observations for '{spec.platform_code}' "
                f"({spec.fred_series_id})"
            )
            raise InvalidProviderDataError(msg)

        try:
            return self._normalizer.normalize(raw)
        except DataEngineError:
            raise
        except Exception as exc:
            msg = (
                f"failed to normalize fred data for '{spec.platform_code}': {exc}"
            )
            raise TransformationError(msg) from exc

    def _fetch_observations(self, fred_series_id: str) -> Mapping[str, Any]:
        """Fetch the raw FRED observations JSON payload."""
        if not self._api_key:
            # Fake HTTP clients used in tests never need a key; the live
            # default client does. Detect "about to call real HTTP".
            if type(self._http_client) is UrllibJsonHttpClient:
                msg = "fred adapter requires an api_key for live requests"
                raise DataEngineError(msg)

        params = {
            "series_id": fred_series_id,
            "file_type": "json",
        }
        if self._api_key:
            params["api_key"] = self._api_key

        try:
            return self._http_client.get_json(self._base_url, params=params)
        except DataEngineError:
            raise
        except Exception as exc:
            msg = f"fred request failed for series '{fred_series_id}': {exc}"
            raise DataEngineError(msg) from exc

    def _to_raw_series(
        self, payload: Mapping[str, Any], spec: FredSeriesSpec
    ) -> RawEconomicSeries:
        """Map a FRED observations payload onto ``RawEconomicSeries``."""
        if not isinstance(payload, Mapping):
            msg = (
                f"fred returned an unexpected payload shape for "
                f"'{spec.fred_series_id}'"
            )
            raise InvalidProviderDataError(msg)

        error_message = payload.get("error_message")
        if error_message:
            msg = (
                f"fred reported an error for '{spec.fred_series_id}': "
                f"{error_message}"
            )
            raise InvalidProviderDataError(msg)

        observations = payload.get("observations")
        if observations is None:
            msg = (
                f"fred returned no observations field for '{spec.fred_series_id}'"
            )
            raise InvalidProviderDataError(msg)
        if not isinstance(observations, Sequence) or isinstance(
            observations, (str, bytes)
        ):
            msg = (
                f"fred returned a malformed observations list for "
                f"'{spec.fred_series_id}'"
            )
            raise InvalidProviderDataError(msg)

        points: list[RawEconomicDataPoint] = []
        for row in observations:
            if not isinstance(row, Mapping):
                continue
            points.append(
                RawEconomicDataPoint(
                    observation_date=row.get("date"),
                    value=row.get("value"),
                )
            )

        return RawEconomicSeries(
            provider_id=_PROVIDER_ID,
            indicator_code=spec.platform_code,
            country=spec.country,
            points=tuple(points),
            frequency=spec.frequency,
            indicator_name=spec.indicator_name,
            unit=spec.unit,
        )
