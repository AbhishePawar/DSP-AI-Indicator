"""Concrete Yahoo Finance market-data adapter.

This is the platform's first real provider integration, and the only
class anywhere in the codebase aware that "Yahoo Finance" exists — its
URL structure, query parameters, and response shape are all handled
here and nowhere else. Everything downstream of this module (the
normalization framework, ``MarketDataService``, every future engine)
only ever sees ``contracts`` types.

Scope for this sprint is deliberately narrow: historical **daily**
OHLCV bars only. Intraday, options, dividends/splits, and any other
Yahoo Finance capability are out of scope — see
``packages/data_engine/README.md`` for the full rationale.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from typing import Any

from contracts.domain.instrument import Instrument
from contracts.domain.price_series import PriceSeries
from contracts.enums import BarFrequency
from data_engine.adapters import BaseAdapter
from data_engine.adapters.yahoo_finance.http_client import (
    JsonHttpClient,
    UrllibJsonHttpClient,
)
from data_engine.exceptions import (
    DataEngineError,
    InvalidProviderDataError,
    TransformationError,
)
from data_engine.normalization import DefaultMarketDataNormalizer, MarketDataNormalizer
from data_engine.ports import MarketDataPort
from data_engine.raw_models import RawMarketBar, RawMarketSeries

__all__ = ["YahooFinanceAdapter"]

_DEFAULT_BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
_PROVIDER_ID = "yahoo_finance"


def _at(sequence: Sequence[Any], index: int) -> Any:
    """Return ``sequence[index]``, or ``None`` if ``index`` is out of range.

    Yahoo Finance occasionally returns indicator arrays that are shorter
    than the ``timestamp`` array; treating a missing trailing entry as
    ``None`` lets the normal missing-value handling deal with it rather
    than raising an ``IndexError`` here.
    """
    return sequence[index] if index < len(sequence) else None


class YahooFinanceAdapter(BaseAdapter, MarketDataPort):
    """Retrieves historical daily OHLCV data from Yahoo Finance.

    Responsibilities, and nothing more:

    1. Build the Yahoo Finance chart-API request for a symbol and date
       range and fetch it via an injected :class:`JsonHttpClient`.
    2. Map the resulting payload onto provider-neutral
       :class:`RawMarketSeries`/:class:`RawMarketBar` instances.
    3. Hand that raw series to a :class:`MarketDataNormalizer` and
       return the validated ``contracts.PriceSeries`` it produces.

    No HTTP call, JSON shape, or field mapping happens anywhere else in
    the Data Engine — a caller only ever sees this class raise
    ``DataEngineError`` subclasses, never a ``urllib`` exception, a raw
    ``dict``, or any other Yahoo-Finance-specific type.
    """

    def __init__(
        self,
        *,
        http_client: JsonHttpClient | None = None,
        normalizer: MarketDataNormalizer | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout_seconds: float = 10.0,
    ) -> None:
        """Initialize the adapter.

        Args:
            http_client: The HTTP client to use. Defaults to
                :class:`UrllibJsonHttpClient`. Tests should inject a
                fake implementation instead of relying on this default.
            normalizer: The normalizer used to convert raw responses
                into ``contracts`` objects. Defaults to
                :class:`DefaultMarketDataNormalizer` configured for
                daily bars, since this adapter only ever requests daily
                data.
            base_url: Base URL of the Yahoo Finance chart endpoint.
                Overridable for testing; there is no reason to change
                it in production use.
            timeout_seconds: Timeout passed to the default HTTP client.
                Ignored if ``http_client`` is provided explicitly.
        """
        self._http_client = http_client or UrllibJsonHttpClient(
            timeout_seconds=timeout_seconds
        )
        self._normalizer = normalizer or DefaultMarketDataNormalizer(
            frequency=BarFrequency.DAILY
        )
        self._base_url = base_url

    @property
    def provider_name(self) -> str:
        """Return the canonical id this adapter registers under."""
        return _PROVIDER_ID

    def get_price_series(
        self,
        instrument: Instrument,
        frequency: BarFrequency,
        start: date,
        end: date,
    ) -> PriceSeries:
        """Retrieve a daily price series for an instrument over a date range.

        Args:
            instrument: The instrument to retrieve prices for.
            frequency: Must be ``BarFrequency.DAILY`` — this adapter
                does not support any other sampling frequency.
            start: Inclusive start date of the requested range.
            end: Inclusive end date of the requested range.

        Returns:
            A validated ``PriceSeries`` covering the requested range.

        Raises:
            DataEngineError: If ``frequency`` is not ``DAILY``.
            ProviderRequestError: If the HTTP request to Yahoo Finance
                fails, times out, or returns an unparsable body.
            InvalidProviderDataError: If Yahoo Finance's response has an
                unexpected shape, reports an error, or contains no
                usable bars for the requested range.
            NormalizationError: If a returned bar is otherwise malformed
                (see ``data_engine.normalization``).
        """
        if frequency is not BarFrequency.DAILY:
            msg = (
                f"YahooFinanceAdapter only supports BarFrequency.DAILY, "
                f"got {frequency!r}"
            )
            raise DataEngineError(msg)

        payload = self._fetch_chart_payload(instrument.symbol, start, end)
        raw = self._to_raw_series(payload, instrument.symbol)

        if not raw.bars:
            msg = (
                f"yahoo_finance returned no usable bars for "
                f"'{instrument.symbol}' between {start} and {end}"
            )
            raise InvalidProviderDataError(msg)

        try:
            return self._normalizer.normalize(raw, instrument)
        except DataEngineError:
            raise
        except Exception as exc:
            msg = (
                f"failed to normalize yahoo_finance data for "
                f"'{instrument.symbol}': {exc}"
            )
            raise TransformationError(msg) from exc

    def _fetch_chart_payload(
        self, symbol: str, start: date, end: date
    ) -> Mapping[str, Any]:
        """Fetch the raw chart-API JSON payload for ``symbol``.

        Raises:
            ProviderRequestError: If the request fails for any reason,
                including a bug in an injected, non-conforming
                ``http_client``.
        """
        params = {
            "period1": str(self._to_unix_seconds(start, end_of_day=False)),
            "period2": str(self._to_unix_seconds(end, end_of_day=True)),
            "interval": "1d",
        }
        try:
            return self._http_client.get_json(
                f"{self._base_url}/{symbol}", params=params
            )
        except DataEngineError:
            raise
        except Exception as exc:
            msg = f"yahoo_finance request failed for '{symbol}': {exc}"
            raise DataEngineError(msg) from exc

    @staticmethod
    def _to_unix_seconds(day: date, *, end_of_day: bool) -> int:
        """Convert a calendar date into a UTC Unix timestamp in seconds."""
        if end_of_day:
            moment = datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=UTC)
        else:
            moment = datetime(day.year, day.month, day.day, tzinfo=UTC)
        return int(moment.timestamp())

    def _to_raw_series(
        self, payload: Mapping[str, Any], symbol: str
    ) -> RawMarketSeries:
        """Map a Yahoo Finance chart-API payload onto a ``RawMarketSeries``.

        Raises:
            InvalidProviderDataError: If ``payload`` does not have the
                expected ``chart`` shape, reports an error, or contains
                no result set.
        """
        chart = payload.get("chart") if isinstance(payload, Mapping) else None
        if not isinstance(chart, Mapping):
            msg = f"yahoo_finance returned an unexpected payload shape for '{symbol}'"
            raise InvalidProviderDataError(msg)

        error = chart.get("error")
        if error:
            msg = f"yahoo_finance reported an error for '{symbol}': {error}"
            raise InvalidProviderDataError(msg)

        results = chart.get("result") or []
        if not results:
            msg = f"yahoo_finance returned no chart result for '{symbol}'"
            raise InvalidProviderDataError(msg)

        result = results[0]
        timestamps = result.get("timestamp") or []
        indicators = result.get("indicators") or {}
        quotes = (indicators.get("quote") or [{}])[0]
        adjusted = (indicators.get("adjclose") or [{}])[0]

        opens = quotes.get("open") or []
        highs = quotes.get("high") or []
        lows = quotes.get("low") or []
        closes = quotes.get("close") or []
        volumes = quotes.get("volume") or []
        adjusted_closes = adjusted.get("adjclose") or []

        bars: list[RawMarketBar] = []
        for index, timestamp in enumerate(timestamps):
            open_ = _at(opens, index)
            high = _at(highs, index)
            low = _at(lows, index)
            close = _at(closes, index)

            if open_ is None and high is None and low is None and close is None:
                # Yahoo Finance's convention for "no trading session at
                # this timestamp" (e.g. an exchange holiday) rather than
                # a genuine data-quality problem — skip, don't fail.
                continue

            bars.append(
                RawMarketBar(
                    provider_id=_PROVIDER_ID,
                    timestamp=timestamp,
                    open=open_,
                    high=high,
                    low=low,
                    close=close,
                    volume=_at(volumes, index),
                    adjusted_close=_at(adjusted_closes, index),
                )
            )

        return RawMarketSeries(
            provider_id=_PROVIDER_ID, symbol=symbol, bars=tuple(bars)
        )
