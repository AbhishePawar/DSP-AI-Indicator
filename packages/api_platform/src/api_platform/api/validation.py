"""Request validation for composition endpoints — no execution."""

from __future__ import annotations

import re
from typing import Any

from api_platform.api.composition_schemas import AnalyseRequest

__all__ = ["validate_analyse_request"]

_TICKER_RE = re.compile(r"^[A-Za-z0-9.\-]{1,32}$")
_EXCHANGE_RE = re.compile(r"^[A-Za-z0-9_\-]{1,32}$")

# P1-05 — client-controlled Buffett / investment-quality conclusions are never
# authoritative. Reject when smuggled into statement maps or metadata.
_FORBIDDEN_BUFFETT_CLIENT_KEYS = frozenset(
    {
        "buffett_score",
        "buffett_rating",
        "buffett_conclusion",
        "buffett_signals",
        "moat_score",
        "management_score",
        "quality_score",
        "capital_allocation_score",
        "governance_score",
        "investment_quality",
        "overall_buffett_rating",
        "buffett_action",
    }
)

# P1-06 — client-forged audit / provenance evidence is never authoritative.
_FORBIDDEN_PROVENANCE_CLIENT_KEYS = frozenset(
    {
        "analysis_id",
        "audit_reference",
        "audit_result",
        "provenance",
        "source_evidence",
        "authenticated_valuation_trace",
        "input_fingerprint",
        "result_fingerprint",
        "valuation_result",
        "buffett_result",
        "investment_conclusion",
    }
)


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

    # P0-02 — clients may supply market price only. Investment conclusions
    # (IV / MoS / premium-discount) are rejected at the HTTP boundary.
    if body.valuation_signals is not None:
        vs = body.valuation_signals
        if vs.intrinsic_value_per_share is not None:
            errors.append(
                "client-supplied valuation_signals.intrinsic_value_per_share "
                "is not accepted (P0-02)"
            )
        if vs.margin_of_safety is not None:
            errors.append(
                "client-supplied valuation_signals.margin_of_safety "
                "is not accepted (P0-02)"
            )
        if vs.premium_discount is not None:
            errors.append(
                "client-supplied valuation_signals.premium_discount "
                "is not accepted (P0-02)"
            )

    has_price = body.current_market_price is not None or (
        body.valuation_signals is not None
        and body.valuation_signals.current_market_price is not None
    )
    if not has_price:
        errors.append(
            "missing valuation data: provide current_market_price "
            "(client investment conclusions are not accepted)"
        )

    income = body.financial_statements.income_statement or {}
    if not income:
        errors.append("financial_statements.income_statement is required")

    # P1-05 / P1-06 — reject smuggled Buffett / provenance conclusion fields.
    fs = body.financial_statements
    for path, mapping in (
        ("financial_statements.income_statement", fs.income_statement),
        ("financial_statements.balance_sheet", fs.balance_sheet),
        ("financial_statements.cash_flow", fs.cash_flow),
        ("financial_statements.statement_metadata", fs.statement_metadata),
    ):
        errors.extend(_forbidden_client_keys(mapping, path))

    return errors


def _forbidden_client_keys(mapping: Any, path: str) -> list[str]:
    if not isinstance(mapping, dict):
        return []
    hits: list[str] = []
    for key in mapping:
        normalized = str(key).strip().lower()
        if normalized in _FORBIDDEN_BUFFETT_CLIENT_KEYS:
            hits.append(
                f"client-supplied {path}.{key} is not accepted (P1-05)"
            )
        elif normalized in _FORBIDDEN_PROVENANCE_CLIENT_KEYS:
            hits.append(
                f"client-supplied {path}.{key} is not accepted (P1-06)"
            )
    return hits
