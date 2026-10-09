"""Upstox V2 Authenticated Market Quote and Instrument Adapter.

Provides optional server-side integration with Upstox API v2 for:
- NSE/BSE Equity market quotes
- MCX Commodity instruments (e.g. Gold, Silver, Crude Oil)
- Instrument key resolution

Credentials and configuration remain strictly server-side:
- UPSTOX_ACCESS_TOKEN
- UPSTOX_API_KEY
- UPSTOX_BASE_URL (defaults to https://api.upstox.com/v2)

Never exposes secrets or credentials to client bundles.
Fails gracefully when unconfigured or when upstream is unreachable.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine.exceptions import ProviderRequestError
from data_engine.market_quote.adapters import build_quote_from_mapping
from data_engine.market_quote.models import (
    AuthenticatedMarketQuote,
    MarketQuoteProvenance,
    QuoteField,
    utc_now,
)
from data_engine.market_quote.service import MarketQuotePort, QuoteProviderHealth

DEFAULT_UPSTOX_BASE_URL = "https://api.upstox.com/v2"


def _parse_timestamp(ts: Any) -> datetime | None:
    if isinstance(ts, (int, float)):
        # Milliseconds or seconds epoch
        if ts > 1e11:
            return datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


@dataclass
class UpstoxQuoteAdapter(MarketQuotePort):
    """Authenticated Upstox V2 API quote adapter."""

    base_url: str = field(
        default_factory=lambda: os.environ.get("UPSTOX_BASE_URL", DEFAULT_UPSTOX_BASE_URL)
    )
    access_token: str | None = field(
        default_factory=lambda: os.environ.get("UPSTOX_ACCESS_TOKEN")
    )
    api_key: str | None = field(
        default_factory=lambda: os.environ.get("UPSTOX_API_KEY")
    )
    timeout_seconds: float = 8.0
    max_retries: int = 2
    _provider_id: str = "upstox"
    provider_name: str = "Upstox V2 Market Quote"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def is_configured(self) -> bool:
        """True when authoritative credentials exist in the server environment."""
        token = (self.access_token or "").strip()
        return bool(token)

    def health(self) -> QuoteProviderHealth:
        if not self.is_configured():
            return QuoteProviderHealth(
                provider_id=self.provider_id,
                healthy=False,
                authenticated=False,
                detail="Upstox credentials not configured (UPSTOX_ACCESS_TOKEN not set)",
            )
        return QuoteProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=True,
            detail="Upstox configured and active",
        )

    def format_instrument_key(self, instrument: Instrument) -> str:
        """Translate Instrument into canonical Upstox instrument key.

        Format:
        - NSE Equity: NSE_EQ|INE155A01022 or NSE_EQ|TATAMOTORS
        - BSE Equity: BSE_EQ|500570 or BSE_EQ|TATAMOTORS
        - MCX Commodity: MCX_COMM|GOLD or MCX_COMM|CRUDEOIL
        """
        sym = instrument.symbol.strip().upper()
        ex = (instrument.exchange or "").strip().upper()

        if instrument.asset_class is AssetClass.COMMODITY or ex in ("MCX", "NCDEX"):
            return f"MCX_COMM|{sym}"
        if ex == "BSE":
            return f"BSE_EQ|{sym}"
        return f"NSE_EQ|{sym}"

    def get_quote(self, instrument: Instrument) -> AuthenticatedMarketQuote | None:
        """Fetch real-time quote from Upstox API v2 with bounded retries."""
        if not self.is_configured():
            return None

        instrument_key = self.format_instrument_key(instrument)
        encoded_key = urllib.parse.quote(instrument_key)
        url = f"{self.base_url.rstrip('/')}/market-quote/quotes?instrument_key={encoded_key}"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "User-Agent": "dsp-ai-indicator/1.0",
        }

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            req = urllib.request.Request(url, headers=headers, method="GET")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    raw = resp.read().decode("utf-8")
                    status = getattr(resp, "status", 200)
                break
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    return None
                if exc.code == 429 and attempt < self.max_retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                last_error = exc
                break
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(0.3 * (attempt + 1))
                    continue
                break
        else:
            if last_error:
                raise ProviderRequestError(f"Upstox quote request failed: {last_error}")
            return None

        if last_error is not None:
            if isinstance(last_error, urllib.error.HTTPError) and last_error.code in (401, 403):
                raise ProviderRequestError(f"Upstox authentication failed: HTTP {last_error.code}")
            raise ProviderRequestError(f"Upstox quote request failed: {last_error}")

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderRequestError("Upstox response is not valid JSON") from exc

        if not isinstance(payload, dict) or payload.get("status") != "success":
            return None

        data_map = payload.get("data")
        if not isinstance(data_map, dict):
            return None

        # Look up quote by normalized key
        quote_data = None
        for k, v in data_map.items():
            if k.upper() == instrument_key.upper() or instrument.symbol.upper() in k.upper():
                quote_data = v
                break

        if not isinstance(quote_data, dict):
            return None

        ohlc = quote_data.get("ohlc", {}) if isinstance(quote_data.get("ohlc"), dict) else {}
        current_price = quote_data.get("last_price")
        volume = quote_data.get("volume")
        change = quote_data.get("net_change")
        as_of = _parse_timestamp(quote_data.get("timestamp")) or utc_now()

        provenance = MarketQuoteProvenance(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            source_type="licensed_vendor",
            retrieved_at=utc_now(),
            as_of=as_of,
            auth_mode="oauth_bearer",
            metadata={"instrument_key": instrument_key, "base_url": self.base_url},
        )

        fields = {
            "exchange": instrument.exchange,
            "currency": instrument.currency or "INR",
            "current_price": current_price,
            "open": ohlc.get("open"),
            "high": ohlc.get("high"),
            "low": ohlc.get("low"),
            "previous_close": ohlc.get("close"),
            "volume": volume,
        }
        return build_quote_from_mapping(
            symbol=instrument.symbol.strip().upper(),
            payload=fields,
            provenance=provenance,
        )
