"""Authenticated Upstox v3 market-quote adapter.

Only resolves an instrument when the domain object provides both a valid ISIN
and an explicit supported Indian exchange. No ticker-to-instrument guessing.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

from contracts.domain.instrument import Instrument
from data_engine.exceptions import ProviderRequestError
from data_engine.market_quote.models import (
    AuthenticatedMarketQuote,
    MarketQuoteProvenance,
    utc_now,
)
from data_engine.market_quote.service import MarketQuotePort, QuoteProviderHealth

_UPSTOX_QUOTES_URL = "https://api.upstox.com/v3/market-quote/quotes"
_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{10}$")
_EXCHANGE_SEGMENTS = {
    "NSE": "NSE_EQ",
    "NSE_EQ": "NSE_EQ",
    "NSE EQUITY": "NSE_EQ",
    "BSE": "BSE_EQ",
    "BSE_EQ": "BSE_EQ",
    "BSE EQUITY": "BSE_EQ",
}


def _parse_source_time(value: Any) -> datetime | None:
    """Parse an explicitly supplied ISO timestamp or Unix epoch (ms/s)."""
    if value is None or isinstance(value, bool):
        return None
    try:
        if isinstance(value, (int, float)):
            epoch = float(value)
            if epoch > 10_000_000_000:
                epoch /= 1000.0
            return datetime.fromtimestamp(epoch, tz=UTC)
        text = str(value).strip()
        if not text:
            return None
        if text.isdigit():
            return _parse_source_time(int(text))
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else parsed.astimezone()
    except (OverflowError, OSError, TypeError, ValueError):
        return None


def resolve_upstox_instrument_key(instrument: Instrument) -> str | None:
    """Resolve only from verified identity fields; never infer from ticker."""
    isin = str(instrument.isin or "").strip().upper()
    exchange = str(instrument.exchange or "").strip().upper()
    segment = _EXCHANGE_SEGMENTS.get(exchange)
    if not segment or not _ISIN_RE.fullmatch(isin):
        return None
    return f"{segment}|{isin}"


def _extract_quote(payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
    data = payload.get("data")
    if not isinstance(data, Mapping):
        return None
    if "last_price" in data or "ohlc" in data:
        return data

    candidates = [value for value in data.values() if isinstance(value, Mapping)]
    candidates = [
        value
        for value in candidates
        if "last_price" in value or isinstance(value.get("ohlc"), Mapping)
    ]
    # A single instrument was requested. Refuse ambiguous multi-quote payloads.
    return candidates[0] if len(candidates) == 1 else None


@dataclass
class UpstoxQuoteAdapter(MarketQuotePort):
    """Fetch and validate genuine market quotes from Upstox v3."""

    access_token: str
    timeout_seconds: float = 10.0
    base_url: str = _UPSTOX_QUOTES_URL
    _provider_id: str = "upstox_market_quote"
    provider_name: str = "Upstox Market Quote"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def get_quote(self, instrument: Instrument) -> AuthenticatedMarketQuote | None:
        token = self.access_token.strip()
        if not token:
            raise ProviderRequestError("Upstox access token is required")

        instrument_key = resolve_upstox_instrument_key(instrument)
        if instrument_key is None:
            return None

        url = f"{self.base_url}?{urlencode({'instrument_key': instrument_key})}"
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Api-Version": "3.0",
                "User-Agent": "dsp-data-engine-upstox-quote/1.0",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                status = getattr(response, "status", 200)
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code in (404, 204):
                return None
            if exc.code in (401, 403):
                raise ProviderRequestError(
                    f"Upstox authentication/permission failure (HTTP {exc.code})"
                ) from None
            if exc.code == 429:
                raise ProviderRequestError(
                    "Upstox rate limit exceeded (HTTP 429)"
                ) from None
            raise ProviderRequestError(
                f"Upstox quote request failed (HTTP {exc.code})"
            ) from None
        except (TimeoutError, urllib.error.URLError) as exc:
            reason = getattr(exc, "reason", None)
            if isinstance(reason, TimeoutError) or isinstance(exc, TimeoutError):
                raise ProviderRequestError("Upstox quote request timed out") from None
            raise ProviderRequestError(
                "Upstox quote request could not be completed"
            ) from None
        except Exception:
            raise ProviderRequestError("Upstox quote request failed") from None

        if status == 204:
            return None
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ProviderRequestError("Upstox quote response is not valid JSON") from None
        if not isinstance(payload, Mapping):
            raise ProviderRequestError("Upstox quote response must be a JSON object")
        if str(payload.get("status", "")).lower() == "error":
            raise ProviderRequestError("Upstox reported a quote request error")

        quote_data = _extract_quote(payload)
        if quote_data is None:
            return None
        ohlc = quote_data.get("ohlc")
        ohlc = ohlc if isinstance(ohlc, Mapping) else {}
        from data_engine.market_quote.adapters import build_quote_from_mapping

        source_time = _parse_source_time(
            quote_data.get("timestamp")
            or quote_data.get("last_trade_time")
            or quote_data.get("last_trade_time_utc")
        )
        fields = {
            "current_price": quote_data.get("last_price"),
            "open": ohlc.get("open"),
            "high": ohlc.get("high"),
            "low": ohlc.get("low"),
            "previous_close": ohlc.get("close"),
            "volume": quote_data.get("volume"),
            # Upstox average_price is a traded price, not average volume.
            "average_volume": None,
            "exchange": instrument.exchange,
            "currency": instrument.currency,
        }
        provenance = MarketQuoteProvenance(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            source_type="licensed_vendor",
            retrieved_at=utc_now(),
            as_of=source_time,
            auth_mode="bearer_token",
            metadata={
                "endpoint": "/v3/market-quote/quotes",
                "instrument_key": instrument_key,
                "api_version": "3",
            },
        )
        return build_quote_from_mapping(
            symbol=instrument.symbol,
            payload=fields,
            provenance=provenance,
        )

    def health(self) -> QuoteProviderHealth:
        configured = bool(self.access_token.strip() and self.base_url.strip())
        return QuoteProviderHealth(
            provider_id=self.provider_id,
            healthy=configured,
            authenticated=bool(self.access_token.strip()),
            detail=(
                "configured; live connectivity not checked"
                if configured
                else "missing Upstox access token or endpoint"
            ),
        )
