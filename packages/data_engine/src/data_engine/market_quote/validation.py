"""Validate authenticated market quotes — reject invalid / fabricated envelopes."""

from __future__ import annotations

from data_engine.exceptions import InvalidProviderDataError
from data_engine.market_quote.models import AuthenticatedMarketQuote, QuoteField

__all__ = ["validate_authenticated_quote"]


def _check_field(name: str, field: QuoteField) -> None:
    if field.available and field.value is None:
        raise InvalidProviderDataError(
            f"quote field '{name}' marked available with null value"
        )
    if not field.available and field.value is not None:
        raise InvalidProviderDataError(
            f"quote field '{name}' has value but marked unavailable"
        )


def validate_authenticated_quote(quote: AuthenticatedMarketQuote) -> None:
    """Reject structurally invalid quotes. Never invent replacements."""
    if not quote.symbol or not str(quote.symbol).strip():
        raise InvalidProviderDataError("quote missing symbol")
    if not quote.provenance.provider_id.strip():
        raise InvalidProviderDataError("quote missing provider_id provenance")
    if not quote.provenance.provider_name.strip():
        raise InvalidProviderDataError("quote missing provider_name provenance")
    if quote.provenance.source_type.strip().lower() in {
        "",
        "example",
        "dummy",
        "placeholder",
        "fabricated",
        "estimated",
    }:
        raise InvalidProviderDataError(
            f"disallowed provenance source_type={quote.provenance.source_type!r}"
        )

    for name in (
        "current_price",
        "open",
        "high",
        "low",
        "previous_close",
        "week_52_high",
        "week_52_low",
        "volume",
        "average_volume",
        "market_cap",
        "enterprise_value",
        "shares_outstanding",
        "dividend_yield",
        "beta",
    ):
        _check_field(name, getattr(quote, name))
