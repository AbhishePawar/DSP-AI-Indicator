"""Authenticated market quote façade for DSPPlatform (EPIC-D001).

Thin wrapper over ``data_engine.market_quote``. No scoring or valuation.
"""

from __future__ import annotations

from threading import Lock
from typing import Any

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine import (
    MarketQuoteService,
    build_default_quote_adapter_from_env,
)

__all__ = [
    "get_authenticated_market_quote",
    "market_quote_health",
    "market_quote_metrics",
    "reset_market_quote_service_for_tests",
]

_LOCK = Lock()
_SERVICE: MarketQuoteService | None = None


def _service() -> MarketQuoteService:
    global _SERVICE
    with _LOCK:
        if _SERVICE is None:
            adapter = build_default_quote_adapter_from_env()
            # P1-09 CI fixture only — never production / never live vendor evidence.
            try:
                from data_engine import InMemoryAuthenticatedQuoteAdapter
                from dsp_platform.p109_e2e_fixture import (
                    build_p109_quote,
                    p109_fixture_enabled,
                )

                if p109_fixture_enabled() and isinstance(
                    adapter, InMemoryAuthenticatedQuoteAdapter
                ):
                    adapter.put(build_p109_quote())
            except Exception:  # noqa: BLE001
                pass
            _SERVICE = MarketQuoteService(adapter)
        return _SERVICE


def reset_market_quote_service_for_tests(
    service: MarketQuoteService | None = None,
) -> None:
    """Replace or clear the process-local quote service (tests only)."""
    global _SERVICE
    with _LOCK:
        _SERVICE = service


def get_authenticated_market_quote(
    symbol: str,
    *,
    exchange: str | None = None,
    currency: str | None = None,
) -> dict[str, Any] | None:
    """Fetch authenticated quote as a public dict, or ``None`` if unavailable."""
    eff_currency = currency
    if not eff_currency:
        eff_currency = "INR" if exchange and str(exchange).strip().upper() in ("NSE", "BSE") else "USD"
    instrument = Instrument(
        symbol=symbol.strip().upper(),
        asset_class=AssetClass.EQUITY,
        currency=eff_currency,
        exchange=exchange,
    )
    quote = _service().get_quote(instrument)
    if quote is None:
        return None
    return quote.to_public_dict()


def market_quote_health() -> dict[str, Any]:
    return _service().health().to_dict()


def market_quote_metrics() -> dict[str, int]:
    return _service().metrics.snapshot()
