"""U3 — Authenticated Upstox historical market candles via U1 identity.

Flow:
  human symbol → U1 resolver → instrument_key
  → GET /v2/historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}
  → AuthenticatedHistoricalBundle (ohlcv)

Daily candles are the priority (Upstox interval ``day`` → DSP ``daily``).
Weekly/monthly are supported when requested; minute intervals are documented
but not implemented (D004 bars are calendar-date only).

Does NOT silently prefer NSE on AMBIGUOUS.
Does NOT accept client instrument_key / candle / provider / exchange / currency.
Does NOT wire into /analyse, valuation, Buffett, MoS, or recommendation.
Does NOT clear G2.

Credential: DSP_UPSTOX_ANALYTICS_TOKEN (U0).

Official Upstox depth (per docs):
  day ≈ 1 year per request to ``to_date``
  week / month ≈ 10 years per request
  1minute / 30minute — not implemented in U3

Chunking: bounded windows when the requested range exceeds vendor depth.
"""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal
from urllib.parse import quote

from contracts.domain.instrument import Instrument
from data_engine.connector_framework.http import JsonHttpClient, UrllibJsonHttpClient
from data_engine.connector_framework.production_profile import is_production_environment
from data_engine.exceptions import InvalidProviderDataError, ProviderRequestError
from data_engine.historical_series.models import (
    AuthenticatedHistoricalBundle,
    AuthenticatedOhlcvBar,
    HistoricalCompanyIdentity,
    HistoricalField,
    HistoricalProvenance,
    utc_now as hist_utc_now,
)
from data_engine.historical_series.service import (
    HistoricalProviderHealth,
    HistoricalSeriesPort,
    HistoricalSeriesQuery,
)
from data_engine.historical_series.validation import (
    validate_authenticated_historical_bundle,
)
from data_engine.upstox_connectivity import (
    UPSTOX_ANALYTICS_TOKEN_ENV,
    redact_secret,
    resolve_u0_upstox_analytics_token,
)
from data_engine.upstox_instrument_resolver import (
    UpstoxInstrumentCandidate,
    UpstoxInstrumentResolver,
    UpstoxResolveRequest,
    UpstoxResolveResult,
)
from data_engine.upstox_investment import UPSTOX_BASE_URL

__all__ = [
    "UPSTOX_HISTORICAL_CANDLE_PATH",
    "UPSTOX_SUPPORTED_INTERVALS",
    "UPSTOX_DAY_MAX_SPAN_DAYS",
    "UPSTOX_WEEK_MONTH_MAX_SPAN_DAYS",
    "UpstoxHistoricalCandleClient",
    "UpstoxHistoricalCandleRequest",
    "UpstoxHistoricalCandleResult",
    "UpstoxHistoricalCandleStatus",
    "UpstoxHistoricalSeriesAdapter",
]

# Official path relative to https://api.upstox.com/v2/
UPSTOX_HISTORICAL_CANDLE_PATH = "historical-candle"

# Documented Upstox intervals (U3 implements day/week/month only).
UPSTOX_SUPPORTED_INTERVALS = frozenset({"1minute", "30minute", "day", "week", "month"})
_U3_IMPLEMENTED_INTERVALS = frozenset({"day", "week", "month"})

# Vendor depth windows (official docs) — drive bounded chunking.
UPSTOX_DAY_MAX_SPAN_DAYS = 365
UPSTOX_WEEK_MONTH_MAX_SPAN_DAYS = 3650  # ~10 years
_MAX_CHUNKS = 15  # hard cap — never unbounded request loops

_DSP_TO_UPSTOX_INTERVAL = {
    "daily": "day",
    "weekly": "week",
    "monthly": "month",
    "day": "day",
    "week": "week",
    "month": "month",
}
_UPSTOX_TO_DSP_FREQUENCY = {
    "day": "daily",
    "week": "weekly",
    "month": "monthly",
}

UpstoxHistoricalCandleStatus = Literal[
    "OK",
    "AMBIGUOUS",
    "NOT_FOUND",
    "UNAVAILABLE",
    "REJECTED",
    "EMPTY",
]


@dataclass(frozen=True, slots=True)
class UpstoxHistoricalCandleRequest:
    """Server-side historical candle request.

    Client-supplied instrument_key / candles / provider / exchange / currency
    are rejected. ``preferred_exchange`` may disambiguate after U1 AMBIGUOUS.
    """

    symbol: str
    from_date: date
    to_date: date
    interval: str = "daily"  # DSP: daily|weekly|monthly (or Upstox day|week|month)
    preferred_exchange: str | None = None
    client_instrument_key: str | None = None
    client_isin: str | None = None
    client_provider: str | None = None
    client_exchange: str | None = None
    client_currency: str | None = None
    client_candles: Sequence[Any] | None = None


@dataclass(frozen=True, slots=True)
class UpstoxHistoricalCandleResult:
    status: UpstoxHistoricalCandleStatus
    query: str
    detail: str
    retrieved_at: datetime
    from_date: date | None = None
    to_date: date | None = None
    interval: str | None = None
    latency_ms: float | None = None
    http_status: int | None = None
    resolve: UpstoxResolveResult | None = None
    identity: UpstoxInstrumentCandidate | None = None
    series: AuthenticatedHistoricalBundle | None = None
    candle_count: int = 0
    chunks_requested: int = 0

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "query": self.query,
            "detail": self.detail,
            "retrieved_at": self.retrieved_at.isoformat(),
            "from_date": self.from_date.isoformat() if self.from_date else None,
            "to_date": self.to_date.isoformat() if self.to_date else None,
            "interval": self.interval,
            "latency_ms": self.latency_ms,
            "http_status": self.http_status,
            "candle_count": self.candle_count,
            "chunks_requested": self.chunks_requested,
            "identity": None if self.identity is None else self.identity.to_public_dict(),
            "series": None if self.series is None else self.series.to_public_dict(),
            "resolve_status": None if self.resolve is None else self.resolve.status,
        }


@dataclass
class UpstoxHistoricalCandleClient:
    """U1 identity → authenticated Upstox historical OHLCV candles."""

    access_token: str | None = None
    base_url: str = UPSTOX_BASE_URL
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    max_attempts: int = 2
    max_chunks: int = _MAX_CHUNKS
    provider_id: str = "upstox_historical_candles"
    provider_name: str = "Upstox"
    resolver: UpstoxInstrumentResolver | None = None

    def __post_init__(self) -> None:
        if self.access_token is None:
            object.__setattr__(
                self, "access_token", resolve_u0_upstox_analytics_token()
            )
        object.__setattr__(self, "access_token", str(self.access_token or "").strip())
        object.__setattr__(self, "max_attempts", max(1, min(int(self.max_attempts), 3)))
        object.__setattr__(self, "max_chunks", max(1, min(int(self.max_chunks), _MAX_CHUNKS)))
        if self.resolver is None:
            object.__setattr__(
                self,
                "resolver",
                UpstoxInstrumentResolver(
                    access_token=self.access_token,
                    base_url=self.base_url,
                    timeout_seconds=self.timeout_seconds,
                    http_client=self.http_client,
                ),
            )

    def configured(self) -> bool:
        return bool(self.access_token)

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(
            timeout_seconds=self.timeout_seconds
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }

    def get_history(
        self, request: UpstoxHistoricalCandleRequest | str, **kwargs: Any
    ) -> UpstoxHistoricalCandleResult:
        retrieved_at = datetime.now(tz=UTC)
        if isinstance(request, str):
            from_date = kwargs.get("from_date")
            to_date = kwargs.get("to_date")
            if not isinstance(from_date, date) or not isinstance(to_date, date):
                return UpstoxHistoricalCandleResult(
                    status="REJECTED",
                    query=str(request).strip().upper(),
                    detail="from_date and to_date (date) are required",
                    retrieved_at=retrieved_at,
                )
            request = UpstoxHistoricalCandleRequest(
                symbol=request,
                from_date=from_date,
                to_date=to_date,
                interval=str(kwargs.get("interval") or "daily"),
                preferred_exchange=kwargs.get("preferred_exchange"),
            )

        query = str(request.symbol or "").strip().upper()

        # --- reject client authority ---
        if (
            str(request.client_instrument_key or "").strip()
            or str(request.client_isin or "").strip()
            or str(request.client_provider or "").strip()
            or str(request.client_exchange or "").strip()
            or str(request.client_currency or "").strip()
            or request.client_candles is not None
        ):
            return UpstoxHistoricalCandleResult(
                status="REJECTED",
                query=query,
                detail=(
                    "client-supplied instrument_key / isin / provider / exchange / "
                    "currency / candles are not authoritative"
                ),
                retrieved_at=retrieved_at,
                from_date=request.from_date,
                to_date=request.to_date,
            )

        interval_key = str(request.interval or "daily").strip().lower()
        upstox_interval = _DSP_TO_UPSTOX_INTERVAL.get(interval_key)
        if upstox_interval is None or upstox_interval not in _U3_IMPLEMENTED_INTERVALS:
            return UpstoxHistoricalCandleResult(
                status="REJECTED",
                query=query,
                detail=(
                    f"invalid or unsupported interval {request.interval!r}; "
                    "U3 supports daily|weekly|monthly (Upstox day|week|month)"
                ),
                retrieved_at=retrieved_at,
                from_date=request.from_date,
                to_date=request.to_date,
                interval=interval_key,
            )

        if not isinstance(request.from_date, date) or not isinstance(request.to_date, date):
            return UpstoxHistoricalCandleResult(
                status="REJECTED",
                query=query,
                detail="from_date and to_date must be date values",
                retrieved_at=retrieved_at,
            )
        if request.from_date > request.to_date:
            return UpstoxHistoricalCandleResult(
                status="REJECTED",
                query=query,
                detail="invalid date range: from_date after to_date",
                retrieved_at=retrieved_at,
                from_date=request.from_date,
                to_date=request.to_date,
                interval=_UPSTOX_TO_DSP_FREQUENCY[upstox_interval],
            )

        if not self.configured():
            detail = (
                "production fail-closed: Upstox analytics token absent — "
                "no fixture history substitution"
                if is_production_environment()
                else f"provider unavailable: {UPSTOX_ANALYTICS_TOKEN_ENV} absent"
            )
            return UpstoxHistoricalCandleResult(
                status="UNAVAILABLE",
                query=query,
                detail=detail,
                retrieved_at=retrieved_at,
                from_date=request.from_date,
                to_date=request.to_date,
                interval=_UPSTOX_TO_DSP_FREQUENCY[upstox_interval],
            )

        started = time.perf_counter()
        assert self.resolver is not None
        resolve = self.resolver.resolve(
            UpstoxResolveRequest(
                symbol=request.symbol,
                preferred_exchange=request.preferred_exchange,
            )
        )

        dsp_freq = _UPSTOX_TO_DSP_FREQUENCY[upstox_interval]
        common = dict(
            query=resolve.query,
            retrieved_at=retrieved_at,
            from_date=request.from_date,
            to_date=request.to_date,
            interval=dsp_freq,
            latency_ms=round((time.perf_counter() - started) * 1000.0, 2),
            http_status=resolve.http_status,
            resolve=resolve,
        )

        if resolve.status == "AMBIGUOUS":
            return UpstoxHistoricalCandleResult(
                status="AMBIGUOUS",
                detail=(
                    "instrument identity ambiguous; supply preferred_exchange "
                    "(NSE or BSE) — no silent exchange selection"
                ),
                **common,
            )
        if resolve.status == "NOT_FOUND":
            return UpstoxHistoricalCandleResult(
                status="NOT_FOUND",
                detail=resolve.detail,
                **common,
            )
        if resolve.status in {"UNAVAILABLE", "REJECTED"}:
            return UpstoxHistoricalCandleResult(
                status="UNAVAILABLE" if resolve.status == "UNAVAILABLE" else "REJECTED",
                detail=resolve.detail,
                **common,
            )
        if resolve.status != "RESOLVED" or resolve.identity is None:
            return UpstoxHistoricalCandleResult(
                status="UNAVAILABLE",
                detail="instrument not resolved",
                **common,
            )

        identity = resolve.identity
        key = identity.provider_instrument_id
        if not str(key or "").strip():
            return UpstoxHistoricalCandleResult(
                status="UNAVAILABLE",
                detail="resolved identity missing instrument_key",
                identity=identity,
                **common,
            )

        if not self.base_url.lower().startswith("https://"):
            return UpstoxHistoricalCandleResult(
                status="UNAVAILABLE",
                detail="HTTPS required for Upstox historical candles",
                identity=identity,
                **common,
            )

        windows = _chunk_date_windows(
            request.from_date,
            request.to_date,
            interval=upstox_interval,
            max_chunks=self.max_chunks,
        )
        if not windows:
            return UpstoxHistoricalCandleResult(
                status="REJECTED",
                detail="date range exceeds bounded chunk limit",
                identity=identity,
                **common,
            )

        raw_candles: list[Any] = []
        last_http: int | None = None
        last_error = "Upstox historical candle request failed"
        for win_from, win_to in windows:
            payload, status_code, err = self._fetch_window(
                instrument_key=key,
                interval=upstox_interval,
                from_date=win_from,
                to_date=win_to,
            )
            last_http = status_code if status_code is not None else last_http
            if err is not None:
                last_error = err
                return UpstoxHistoricalCandleResult(
                    status="UNAVAILABLE",
                    query=resolve.query,
                    detail=last_error,
                    retrieved_at=retrieved_at,
                    from_date=request.from_date,
                    to_date=request.to_date,
                    interval=dsp_freq,
                    latency_ms=round((time.perf_counter() - started) * 1000.0, 2),
                    http_status=last_http,
                    resolve=resolve,
                    identity=identity,
                    chunks_requested=len(windows),
                )
            assert payload is not None
            chunk_rows = _extract_candle_rows(payload)
            if chunk_rows is None:
                return UpstoxHistoricalCandleResult(
                    status="UNAVAILABLE",
                    query=resolve.query,
                    detail="malformed historical candle response",
                    retrieved_at=retrieved_at,
                    from_date=request.from_date,
                    to_date=request.to_date,
                    interval=dsp_freq,
                    latency_ms=round((time.perf_counter() - started) * 1000.0, 2),
                    http_status=200,
                    resolve=resolve,
                    identity=identity,
                    chunks_requested=len(windows),
                )
            raw_candles.extend(chunk_rows)

        bars, malformed = _normalize_candles(
            raw_candles,
            frequency=dsp_freq,
            from_date=request.from_date,
            to_date=request.to_date,
        )
        if not bars:
            detail = (
                "empty history for requested range"
                if not malformed
                else "malformed candle rows — no usable OHLC bars"
            )
            return UpstoxHistoricalCandleResult(
                status="EMPTY" if not malformed else "UNAVAILABLE",
                query=resolve.query,
                detail=detail,
                retrieved_at=retrieved_at,
                from_date=request.from_date,
                to_date=request.to_date,
                interval=dsp_freq,
                latency_ms=round((time.perf_counter() - started) * 1000.0, 2),
                http_status=last_http or 200,
                resolve=resolve,
                identity=identity,
                candle_count=0,
                chunks_requested=len(windows),
            )

        series = _build_bundle(
            identity=identity,
            bars=bars,
            frequency=dsp_freq,
            from_date=request.from_date,
            to_date=request.to_date,
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            base_url=self.base_url,
            instrument_key=key,
            chunks_requested=len(windows),
            upstox_interval=upstox_interval,
        )
        try:
            validate_authenticated_historical_bundle(series)
        except InvalidProviderDataError as exc:
            return UpstoxHistoricalCandleResult(
                status="UNAVAILABLE",
                query=resolve.query,
                detail=redact_secret(str(exc), self.access_token),
                retrieved_at=retrieved_at,
                from_date=request.from_date,
                to_date=request.to_date,
                interval=dsp_freq,
                latency_ms=round((time.perf_counter() - started) * 1000.0, 2),
                http_status=last_http or 200,
                resolve=resolve,
                identity=identity,
                chunks_requested=len(windows),
            )

        return UpstoxHistoricalCandleResult(
            status="OK",
            query=resolve.query,
            detail="authenticated Upstox historical candles",
            retrieved_at=retrieved_at,
            from_date=request.from_date,
            to_date=request.to_date,
            interval=dsp_freq,
            latency_ms=round((time.perf_counter() - started) * 1000.0, 2),
            http_status=last_http or 200,
            resolve=resolve,
            identity=identity,
            series=series,
            candle_count=len(bars),
            chunks_requested=len(windows),
        )

    def _fetch_window(
        self,
        *,
        instrument_key: str,
        interval: str,
        from_date: date,
        to_date: date,
    ) -> tuple[Any | None, int | None, str | None]:
        url = _historical_url(
            self.base_url,
            instrument_key=instrument_key,
            interval=interval,
            to_date=to_date,
            from_date=from_date,
        )
        last_error = "Upstox historical candle request failed"
        status_code: int | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                payload = self._client().get_json(url, headers=self._headers())
                return payload, 200, None
            except ProviderRequestError as exc:
                safe = redact_secret(str(exc), self.access_token)
                last_error = safe
                status_code = _status_from_detail(safe)
                msg = safe.lower()
                if "401" in msg or "403" in msg or "authentication failed" in msg:
                    break
                if "404" in msg:
                    break
                if "429" in msg or "rate limited" in msg:
                    if attempt >= self.max_attempts:
                        break
                    continue
                if attempt >= self.max_attempts:
                    break
            except Exception as exc:  # noqa: BLE001
                last_error = redact_secret(type(exc).__name__, self.access_token)
                break
        return None, status_code, last_error


@dataclass
class UpstoxHistoricalSeriesAdapter(HistoricalSeriesPort):
    """Thin HistoricalSeriesPort over U3 — not registered as production default."""

    access_token: str | None = None
    base_url: str = UPSTOX_BASE_URL
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    _provider_id: str = "upstox_historical_candles"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _client(self) -> UpstoxHistoricalCandleClient:
        return UpstoxHistoricalCandleClient(
            access_token=self.access_token,
            base_url=self.base_url,
            timeout_seconds=self.timeout_seconds,
            http_client=self.http_client,
            provider_id=self.provider_id,
        )

    def get_series(
        self, query: HistoricalSeriesQuery
    ) -> AuthenticatedHistoricalBundle | None:
        if str(query.series_kind or "").strip().lower() != "ohlcv":
            return None
        if query.start_date is None or query.end_date is None:
            return None
        freq = str(query.frequency or "daily").strip().lower()
        result = self._client().get_history(
            UpstoxHistoricalCandleRequest(
                symbol=query.instrument.symbol,
                from_date=query.start_date,
                to_date=query.end_date,
                interval=freq,
                preferred_exchange=query.instrument.exchange,
            )
        )
        if result.status != "OK" or result.series is None:
            return None
        bars = result.series.bars
        if query.limit and len(bars) > query.limit:
            bars = bars[-int(query.limit) :]
            series = AuthenticatedHistoricalBundle(
                identity=result.series.identity,
                series_kind=result.series.series_kind,
                frequency=result.series.frequency,
                start_date=result.series.start_date,
                end_date=result.series.end_date,
                bars=bars,
                points=(),
                snapshots=(),
                provenance=result.series.provenance,
                currency=result.series.currency,
            )
            return series
        return result.series

    def resolve_company(
        self, instrument: Instrument
    ) -> HistoricalCompanyIdentity | None:
        client = self._client()
        assert client.resolver is not None
        resolved = client.resolver.resolve(
            UpstoxResolveRequest(
                symbol=instrument.symbol,
                preferred_exchange=instrument.exchange,
            )
        )
        if resolved.status != "RESOLVED" or resolved.identity is None:
            return None
        ident = resolved.identity
        currency = "INR" if ident.exchange in {"NSE", "BSE"} else None
        return HistoricalCompanyIdentity(
            symbol=ident.trading_symbol,
            exchange=ident.exchange,
            company_name=ident.company_name,
            isin=ident.isin,
            provider_company_id=ident.isin,
            currency=currency,
        )

    def health(self) -> HistoricalProviderHealth:
        token = str(self.access_token or resolve_u0_upstox_analytics_token() or "").strip()
        ok = bool(token)
        return HistoricalProviderHealth(
            provider_id=self.provider_id,
            healthy=ok,
            authenticated=ok,
            detail="configured analytics token" if ok else "missing analytics token",
        )


def _historical_url(
    base_url: str,
    *,
    instrument_key: str,
    interval: str,
    to_date: date,
    from_date: date,
) -> str:
    encoded = quote(str(instrument_key), safe="")
    return (
        f"{base_url.rstrip('/')}/{UPSTOX_HISTORICAL_CANDLE_PATH}/"
        f"{encoded}/{interval}/{to_date.isoformat()}/{from_date.isoformat()}"
    )


def _chunk_date_windows(
    from_date: date,
    to_date: date,
    *,
    interval: str,
    max_chunks: int,
) -> list[tuple[date, date]]:
    """Bounded reverse windows respecting Upstox per-request depth."""
    span = (
        UPSTOX_DAY_MAX_SPAN_DAYS
        if interval == "day"
        else UPSTOX_WEEK_MONTH_MAX_SPAN_DAYS
    )
    windows: list[tuple[date, date]] = []
    cur_end = to_date
    while cur_end >= from_date:
        if len(windows) >= max_chunks:
            # Would need another chunk to cover remaining range — fail closed.
            return []
        cur_start = max(from_date, cur_end - timedelta(days=span - 1))
        windows.append((cur_start, cur_end))
        if cur_start <= from_date:
            break
        cur_end = cur_start - timedelta(days=1)
    windows.reverse()
    return windows


def _extract_candle_rows(payload: Any) -> list[Any] | None:
    if not isinstance(payload, Mapping):
        return None
    data = payload.get("data")
    if not isinstance(data, Mapping):
        return None
    candles = data.get("candles")
    if candles is None:
        return []
    if not isinstance(candles, list):
        return None
    return list(candles)


def _normalize_candles(
    rows: Sequence[Any],
    *,
    frequency: str,
    from_date: date,
    to_date: date,
) -> tuple[tuple[AuthenticatedOhlcvBar, ...], int]:
    """Map Upstox candle tuples → ascending unique DSP bars.

    Candle layout (official):
      [timestamp, open, high, low, close, volume, open_interest]
    Timestamp is IST offset (e.g. +05:30); bar_date uses the calendar date
    of that provider timestamp (no fabricated conversion of OHLCV fields).
    """
    by_date: dict[date, AuthenticatedOhlcvBar] = {}
    malformed = 0
    for row in rows:
        bar = _parse_candle_row(row, frequency=frequency)
        if bar is None:
            malformed += 1
            continue
        if bar.bar_date < from_date or bar.bar_date > to_date:
            continue
        # Deterministic: later duplicate date overwrites (provider may repeat)
        by_date[bar.bar_date] = bar
    ordered = tuple(by_date[d] for d in sorted(by_date))
    return ordered, malformed


def _parse_candle_row(row: Any, *, frequency: str) -> AuthenticatedOhlcvBar | None:
    if not isinstance(row, (list, tuple)) or len(row) < 5:
        return None
    bar_date = _parse_provider_timestamp(row[0])
    if bar_date is None:
        return None
    # Require OHLC — do not invent missing price legs
    open_f = HistoricalField.of(row[1])
    high_f = HistoricalField.of(row[2])
    low_f = HistoricalField.of(row[3])
    close_f = HistoricalField.of(row[4])
    if not (open_f.available and high_f.available and low_f.available and close_f.available):
        return None
    volume_f = (
        HistoricalField.of(row[5]) if len(row) > 5 else HistoricalField.missing()
    )
    # open_interest (index 6) — not in AuthenticatedOhlcvBar; equity often 0
    return AuthenticatedOhlcvBar(
        bar_date=bar_date,
        open=open_f,
        high=high_f,
        low=low_f,
        close=close_f,
        volume=volume_f,
        frequency=frequency,
    )


def _parse_provider_timestamp(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def _build_bundle(
    *,
    identity: UpstoxInstrumentCandidate,
    bars: tuple[AuthenticatedOhlcvBar, ...],
    frequency: str,
    from_date: date,
    to_date: date,
    provider_id: str,
    provider_name: str,
    base_url: str,
    instrument_key: str,
    chunks_requested: int,
    upstox_interval: str,
) -> AuthenticatedHistoricalBundle:
    exchange = identity.exchange
    if exchange not in {"NSE", "BSE"}:
        # Exchange-implied INR only for Indian equity listings
        raise InvalidProviderDataError("unsupported exchange for Upstox INR history")
    currency = "INR"
    hist_identity = HistoricalCompanyIdentity(
        symbol=identity.trading_symbol,
        exchange=exchange,
        company_name=identity.company_name,
        isin=identity.isin,
        provider_company_id=identity.isin,
        currency=currency,
    )
    provenance = HistoricalProvenance(
        provider_id=provider_id,
        provider_name=provider_name,
        source_type="licensed_vendor",
        retrieved_at=hist_utc_now(),
        as_of=None,
        auth_mode="bearer_token",
        metadata={
            "base_url": base_url,
            "vendor": "upstox",
            "instrument_key": instrument_key,
            "exchange": exchange,
            "isin": identity.isin or "",
            "u1_resolution": "RESOLVED",
            "upstox_interval": upstox_interval,
            "chunks_requested": str(chunks_requested),
            "timezone_note": "provider timestamps IST (+05:30); bar_date = calendar date",
        },
    )
    return AuthenticatedHistoricalBundle(
        identity=hist_identity,
        series_kind="ohlcv",
        frequency=frequency,
        start_date=from_date,
        end_date=to_date,
        bars=bars,
        points=(),
        snapshots=(),
        provenance=provenance,
        currency=currency,
    )


def _status_from_detail(detail: str) -> int | None:
    for code in (429, 401, 403, 404, 500, 502, 503):
        if str(code) in detail:
            return code
    return None
