"""Authenticated market quote adapters (EPIC-D001)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Mapping
from urllib.parse import urlencode

from contracts.domain.instrument import Instrument
from data_engine.exceptions import ProviderRequestError
from data_engine.market_quote.models import (
    AuthenticatedMarketQuote,
    MarketQuoteProvenance,
    QuoteField,
    utc_now,
)
from data_engine.market_quote.service import MarketQuotePort, QuoteProviderHealth
from data_engine.market_quote.validation import validate_authenticated_quote

__all__ = [
    "ConfiguredHttpQuoteAdapter",
    "InMemoryAuthenticatedQuoteAdapter",
    "NullAuthenticatedQuoteAdapter",
    "build_quote_from_mapping",
]


def build_quote_from_mapping(
    *,
    symbol: str,
    payload: Mapping[str, Any],
    provenance: MarketQuoteProvenance,
) -> AuthenticatedMarketQuote:
    """Map a vendor-neutral field dict → AuthenticatedMarketQuote."""

    def q(key: str) -> QuoteField:
        return QuoteField.of(payload.get(key))

    quote = AuthenticatedMarketQuote(
        symbol=symbol.strip().upper(),
        exchange=(str(payload["exchange"]) if payload.get("exchange") else None),
        currency=(str(payload["currency"]) if payload.get("currency") else None),
        current_price=q("current_price"),
        open=q("open"),
        high=q("high"),
        low=q("low"),
        previous_close=q("previous_close"),
        week_52_high=q("week_52_high"),
        week_52_low=q("week_52_low"),
        volume=q("volume"),
        average_volume=q("average_volume"),
        market_cap=q("market_cap"),
        enterprise_value=q("enterprise_value"),
        shares_outstanding=q("shares_outstanding"),
        dividend_yield=q("dividend_yield"),
        beta=q("beta"),
        provenance=provenance,
    )
    validate_authenticated_quote(quote)
    return quote


@dataclass
class NullAuthenticatedQuoteAdapter(MarketQuotePort):
    """Always unavailable — safe default when no feed is configured."""

    _provider_id: str = "null_market_quote"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def get_quote(self, instrument: Instrument) -> AuthenticatedMarketQuote | None:
        return None

    def health(self) -> QuoteProviderHealth:
        return QuoteProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=False,
            detail="null provider — no market feed configured",
        )


@dataclass
class InMemoryAuthenticatedQuoteAdapter(MarketQuotePort):
    """Explicitly seeded authenticated quotes only — never invents symbols."""

    api_key: str | None = None
    _provider_id: str = "memory_authenticated_quote"
    _quotes: dict[str, AuthenticatedMarketQuote] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def put(self, quote: AuthenticatedMarketQuote) -> None:
        validate_authenticated_quote(quote)
        with self._lock:
            self._quotes[quote.symbol.upper()] = quote

    def get_quote(self, instrument: Instrument) -> AuthenticatedMarketQuote | None:
        if not self.api_key:
            raise ProviderRequestError(
                "memory quote adapter requires api_key (authentication)"
            )
        with self._lock:
            return self._quotes.get(instrument.symbol.strip().upper())

    def health(self) -> QuoteProviderHealth:
        return QuoteProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=bool(self.api_key),
            detail=(
                "seeded in-memory authenticated quotes"
                if self.api_key
                else "missing api_key"
            ),
        )


@dataclass
class ConfiguredHttpQuoteAdapter(MarketQuotePort):
    """Authenticated HTTP JSON quote adapter.

    Expects the remote to return JSON with RS-002 field names (or nested under
    ``fields``). Requires ``api_key``. Rejects invalid payloads.
    """

    base_url: str
    api_key: str
    timeout_seconds: float = 10.0
    _provider_id: str = "configured_http_quote"
    provider_name: str = "Configured HTTP Market Quote"
    header_name: str = "Authorization"
    header_template: str = "Bearer {api_key}"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def get_quote(self, instrument: Instrument) -> AuthenticatedMarketQuote | None:
        if not self.api_key.strip():
            raise ProviderRequestError("market quote api_key required")
        symbol = instrument.symbol.strip().upper()
        url = f"{self.base_url.rstrip('/')}?{urlencode({'symbol': symbol})}"
        req = urllib.request.Request(
            url,
            headers={
                self.header_name: self.header_template.format(api_key=self.api_key),
                "Accept": "application/json",
                "User-Agent": "dsp-data-engine-market-quote/1.0",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                raw = resp.read().decode("utf-8")
                status = getattr(resp, "status", 200)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            raise ProviderRequestError(
                f"market quote HTTP {exc.code}: {exc.reason}"
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise ProviderRequestError(f"market quote request failed: {exc}") from exc

        if status == 204:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderRequestError("market quote response is not JSON") from exc

        if not isinstance(payload, dict):
            raise ProviderRequestError("market quote JSON must be an object")
        if payload.get("unavailable") is True:
            return None
        fields = payload.get("fields")
        data = fields if isinstance(fields, dict) else payload
        provenance = MarketQuoteProvenance(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            source_type="licensed_vendor",
            retrieved_at=utc_now(),
            as_of=None,
            auth_mode="api_key",
            metadata={"base_url": self.base_url},
        )
        return build_quote_from_mapping(
            symbol=symbol, payload=data, provenance=provenance
        )

    def health(self) -> QuoteProviderHealth:
        ok = bool(self.api_key.strip() and self.base_url.strip())
        return QuoteProviderHealth(
            provider_id=self.provider_id,
            healthy=ok,
            authenticated=bool(self.api_key.strip()),
            detail="configured" if ok else "missing base_url or api_key",
        )


def build_default_quote_adapter_from_env() -> MarketQuotePort:
    """Select quote adapter from environment (no fabricated data).

    P1-03: production requires authenticated HTTP credentials; Null/memory
    cannot silently become the production provider.

    Routes:
    - ``DSP_INVESTMENT_DATA_PROVIDER=upstox`` → Upstox U2 only (no FMP fallback)
    - ``DSP_INVESTMENT_DATA_PROVIDER=fmp`` → FMP only
    - unset / ``auto`` (first match wins):
      1. ConfiguredHttp — ``DSP_MARKET_QUOTE_API_KEY`` + ``DSP_MARKET_QUOTE_BASE_URL``
      2. FMP — ``DSP_FMP_API_KEY`` or ``DSP_INVESTMENT_FMP_API_KEY``
      3. Memory — non-production flag only
    """
    from data_engine.connector_framework.production_profile import (
        memory_adapter_allowed,
        require_authenticated_http_adapter,
    )
    from data_engine.fmp_investment import (
        FinancialModelingPrepQuoteAdapter,
        resolve_fmp_api_key,
    )
    from data_engine.investment_data_provider import (
        require_upstox_analytics_token,
        resolve_investment_data_provider,
    )

    provider = resolve_investment_data_provider()

    if provider == "upstox":
        from data_engine.upstox_investment import UpstoxQuoteAdapter

        token = require_upstox_analytics_token(connector="market_quote")
        if token:
            return UpstoxQuoteAdapter(access_token=token)
        return NullAuthenticatedQuoteAdapter()

    if provider == "fmp":
        fmp_key = resolve_fmp_api_key()
        if fmp_key:
            return FinancialModelingPrepQuoteAdapter(api_key=fmp_key)
        require_authenticated_http_adapter(
            connector="market_quote",
            api_key="",
            base_url="",
            api_key_env="DSP_FMP_API_KEY",
            base_url_env="DSP_FMP_API_KEY",
        )
        return NullAuthenticatedQuoteAdapter()

    # auto — existing FMP / ConfiguredHttp route (unchanged precedence)
    api_key = os.environ.get("DSP_MARKET_QUOTE_API_KEY", "").strip()
    base_url = os.environ.get("DSP_MARKET_QUOTE_BASE_URL", "").strip()
    if api_key and base_url:
        return ConfiguredHttpQuoteAdapter(base_url=base_url, api_key=api_key)
    fmp_key = resolve_fmp_api_key()
    if fmp_key:
        return FinancialModelingPrepQuoteAdapter(api_key=fmp_key)
    if memory_adapter_allowed(
        "DSP_MARKET_QUOTE_MEMORY", connector="market_quote"
    ):
        return InMemoryAuthenticatedQuoteAdapter(api_key=api_key or "dev-memory-key")
    require_authenticated_http_adapter(
        connector="market_quote",
        api_key=api_key,
        base_url=base_url,
        api_key_env="DSP_MARKET_QUOTE_API_KEY",
        base_url_env="DSP_MARKET_QUOTE_BASE_URL",
    )
    return NullAuthenticatedQuoteAdapter()
