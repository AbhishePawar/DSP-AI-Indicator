"""Upstox adapters for Indian investment-critical quote + statements (G2).

Uses the long-lived, read-only Upstox Analytics Token. The provider resolves
an Indian equity to its NSE/BSE instrument key through Instrument Search, then
uses the market-quote and fundamentals APIs. No fabricated values and no
memory/Null fallback are introduced here.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from contracts.domain.instrument import Instrument
from data_engine.connector_framework.http import JsonHttpClient, UrllibJsonHttpClient
from data_engine.exceptions import ProviderRequestError
from data_engine.financial_statement.models import (
    AuthenticatedFinancialStatements,
    CompanyIdentity,
)
from data_engine.financial_statement.service import (
    FinancialStatementPort,
    StatementProviderHealth,
    StatementQuery,
)
from data_engine.market_quote.models import AuthenticatedMarketQuote
from data_engine.market_quote.service import MarketQuotePort, QuoteProviderHealth

__all__ = [
    "UPSTOX_BASE_URL",
    "UPSTOX_ANALYTICS_TOKEN_ENVS",
    "UpstoxQuoteAdapter",
    "UpstoxStatementAdapter",
    "resolve_upstox_analytics_token",
]

UPSTOX_BASE_URL = "https://api.upstox.com/v2"
UPSTOX_ANALYTICS_TOKEN_ENVS = (
    "DSP_UPSTOX_ANALYTICS_TOKEN",
    "DSP_UPSTOX_ACCESS_TOKEN",
)


def resolve_upstox_analytics_token(environ: Mapping[str, str] | None = None) -> str:
    """Return the first configured read-only Upstox token; never log its value."""
    env = environ if environ is not None else os.environ
    for name in UPSTOX_ANALYTICS_TOKEN_ENVS:
        value = str(env.get(name) or "").strip()
        if value:
            return value
    return ""


@dataclass
class _UpstoxBase:
    access_token: str
    base_url: str = UPSTOX_BASE_URL
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    provider_name: str = "Upstox"

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(timeout_seconds=self.timeout_seconds)

    def _get(self, path: str, params: Mapping[str, Any] | None = None) -> Any:
        if not self.access_token.strip():
            raise ProviderRequestError("Upstox adapter requires analytics token")
        try:
            return self._client().get_json(
                f"{self.base_url.rstrip('/')}/{path.lstrip('/')}",
                params=dict(params or {}),
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.access_token}",
                },
            )
        except TypeError:
            # Compatibility with the existing JsonHttpClient contract if it does
            # not accept headers directly: fall back to a provider-specific URL
            # client only when the injected client exposes no header parameter.
            raise

    def _resolve_identity(self, instrument: Instrument):
        """Resolve via U1 — never silently prefer NSE on ambiguity."""
        from data_engine.upstox_instrument_resolver import (
            UpstoxInstrumentResolver,
            UpstoxResolveRequest,
        )

        resolver = UpstoxInstrumentResolver(
            access_token=self.access_token,
            base_url=self.base_url,
            timeout_seconds=self.timeout_seconds,
            http_client=self.http_client,
        )
        result = resolver.resolve(
            UpstoxResolveRequest(
                symbol=instrument.symbol,
                preferred_exchange=instrument.exchange,
            )
        )
        if result.status != "RESOLVED" or result.identity is None:
            return None
        return result.identity

    def _instrument(self, instrument: Instrument) -> dict[str, Any] | None:
        """Compatibility shim — U1 only (no silent NSE selection)."""
        identity = self._resolve_identity(instrument)
        if identity is None:
            return None
        return {
            "name": identity.company_name,
            "segment": identity.segment,
            "exchange": identity.exchange,
            "isin": identity.isin,
            "instrument_type": identity.instrument_type,
            "instrument_key": identity.provider_instrument_id,
            "trading_symbol": identity.trading_symbol,
        }


@dataclass
class UpstoxQuoteAdapter(_UpstoxBase, MarketQuotePort):
    """Authenticated Upstox full-market quote → AuthenticatedMarketQuote.

    Uses U1 resolver + U2 market-quote path. Does not silently select NSE.
    """

    _provider_id: str = "upstox_market_quote"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def get_quote(self, instrument: Instrument) -> AuthenticatedMarketQuote | None:
        from data_engine.upstox_market_quote import (
            UpstoxMarketQuoteClient,
            UpstoxMarketQuoteRequest,
        )

        client = UpstoxMarketQuoteClient(
            access_token=self.access_token,
            base_url=self.base_url,
            timeout_seconds=self.timeout_seconds,
            http_client=self.http_client,
        )
        result = client.get_quote(
            UpstoxMarketQuoteRequest(
                symbol=instrument.symbol,
                preferred_exchange=instrument.exchange,
            )
        )
        return result.quote if result.status == "OK" else None

    def health(self) -> QuoteProviderHealth:
        ok = bool(self.access_token.strip())
        return QuoteProviderHealth(
            provider_id=self.provider_id,
            healthy=ok,
            authenticated=ok,
            detail="configured analytics token" if ok else "missing analytics token",
        )


@dataclass
class UpstoxStatementAdapter(_UpstoxBase, FinancialStatementPort):
    """Authenticated Upstox company fundamentals → statement bundle.

    Delegates to U4 (U1 identity, no silent NSE, no client ISIN/key authority).
    Not registered as the default production statement provider.
    """

    _provider_id: str = "upstox_financial_statements"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _u4(self):
        from data_engine.upstox_fundamentals import UpstoxFundamentalsClient

        return UpstoxFundamentalsClient(
            access_token=self.access_token,
            base_url=self.base_url,
            timeout_seconds=self.timeout_seconds,
            http_client=self.http_client,
            provider_id=self.provider_id,
            provider_name=self.provider_name,
        )

    def resolve_company(self, instrument: Instrument) -> CompanyIdentity | None:
        from data_engine.upstox_fundamentals import UpstoxFundamentalsRequest

        result = self._u4().get_fundamentals(
            UpstoxFundamentalsRequest(
                symbol=instrument.symbol,
                preferred_exchange=instrument.exchange,
                limit=1,
            )
        )
        if result.status != "OK" or result.statements is None:
            return None
        return result.statements.identity

    def get_statements(self, query: StatementQuery) -> AuthenticatedFinancialStatements | None:
        from data_engine.upstox_fundamentals import UpstoxFundamentalsRequest

        period = str(query.period_type or "annual").strip().lower()
        result = self._u4().get_fundamentals(
            UpstoxFundamentalsRequest(
                symbol=query.instrument.symbol,
                preferred_exchange=query.instrument.exchange,
                period_type=period,
                limit=int(query.limit or 4),
            )
        )
        return result.statements if result.status == "OK" else None

    def health(self) -> StatementProviderHealth:
        ok = bool(self.access_token.strip())
        return StatementProviderHealth(
            provider_id=self.provider_id,
            healthy=ok,
            authenticated=ok,
            detail="configured analytics token" if ok else "missing analytics token",
        )
