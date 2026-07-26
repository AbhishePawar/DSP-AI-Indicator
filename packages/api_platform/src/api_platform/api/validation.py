"""Request validation for composition endpoints — no execution."""

from __future__ import annotations

import re

from api_platform.api.composition_schemas import AnalyseRequest

__all__ = ["validate_analyse_request"]

_TICKER_RE = re.compile(r"^[A-Za-z0-9.\-]{1,32}$")
_EXCHANGE_RE = re.compile(r"^[A-Za-z0-9_\-]{1,32}$")


def validate_analyse_request(body: AnalyseRequest) -> list[str]:
    """Return validation error strings (empty when valid). Does not execute."""
    errors: list[str] = []
    ticker = body.ticker.strip()
    if not ticker:
        errors.append("ticker is required")
    elif not _TICKER_RE.match(ticker):
        errors.append("ticker has unsupported format")

    if body.exchange is not None:
        exchange = body.exchange.strip()
        if not exchange:
            errors.append("exchange must be non-empty when provided")
        elif not _EXCHANGE_RE.match(exchange):
            errors.append("exchange has unsupported format")

    period = body.financial_statements.period
    if not period.period_type.strip():
        errors.append("financial_statements.period.period_type is required")
    if not period.period_end.strip():
        errors.append("financial_statements.period.period_end is required")

    has_signals = body.valuation_signals is not None and (
        body.valuation_signals.intrinsic_value_per_share is not None
        or body.valuation_signals.current_market_price is not None
    )
    has_price = body.current_market_price is not None
    if not has_signals and not has_price:
        errors.append(
            "missing valuation data: provide valuation_signals and/or "
            "current_market_price"
        )

    income = body.financial_statements.income_statement or {}
    if not income:
        errors.append("financial_statements.income_statement is required")

    return errors
