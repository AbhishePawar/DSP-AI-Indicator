"""Validate authenticated financial statements — reject invalid / fabricated envelopes.

No calculations — structural and provenance checks only.
"""

from __future__ import annotations

from data_engine.exceptions import InvalidProviderDataError
from data_engine.financial_statement.models import (
    AuthenticatedFinancialStatements,
    AuthenticatedStatementPeriod,
    StatementField,
)

__all__ = ["validate_authenticated_statements"]

_ALLOWED_PERIOD_TYPES = frozenset({"annual", "quarterly", "ttm"})
_DISALLOWED_SOURCE = frozenset(
    {"", "example", "dummy", "placeholder", "fabricated", "estimated"}
)

_PERIOD_FIELDS = (
    "revenue",
    "cost_of_revenue",
    "gross_profit",
    "operating_income",
    "ebit",
    "ebitda",
    "net_income",
    "eps_basic",
    "eps_diluted",
    "cash_and_equivalents",
    "current_assets",
    "total_assets",
    "current_liabilities",
    "total_liabilities",
    "total_equity",
    "total_debt",
    "long_term_debt",
    "operating_cash_flow",
    "investing_cash_flow",
    "financing_cash_flow",
    "capital_expenditures",
    "free_cash_flow",
    "dividends_paid",
    "share_buybacks",
    "roe",
    "roce",
    "debt_to_equity",
    "working_capital",
    "gross_margin",
    "operating_margin",
    "net_margin",
    "revenue_growth",
    "eps_growth",
)


def _check_field(name: str, field: StatementField) -> None:
    if field.available and field.value is None:
        raise InvalidProviderDataError(
            f"statement field '{name}' marked available with null value"
        )
    if not field.available and field.value is not None:
        raise InvalidProviderDataError(
            f"statement field '{name}' has value but marked unavailable"
        )


def _validate_period(period: AuthenticatedStatementPeriod, index: int) -> None:
    prefix = f"periods[{index}]"
    if period.period_type not in _ALLOWED_PERIOD_TYPES:
        raise InvalidProviderDataError(
            f"{prefix}.period_type must be annual|quarterly|ttm, "
            f"got {period.period_type!r}"
        )
    currency = (period.reporting_currency or "").strip().upper()
    if len(currency) != 3:
        raise InvalidProviderDataError(
            f"{prefix}.reporting_currency must be ISO 4217, got {currency!r}"
        )
    if not 1900 <= period.fiscal_year <= 2200:
        raise InvalidProviderDataError(
            f"{prefix}.fiscal_year out of range: {period.fiscal_year}"
        )
    if period.fiscal_quarter is not None and not 1 <= period.fiscal_quarter <= 4:
        raise InvalidProviderDataError(
            f"{prefix}.fiscal_quarter must be 1..4 or null"
        )
    for name in _PERIOD_FIELDS:
        _check_field(f"{prefix}.{name}", getattr(period, name))


def validate_authenticated_statements(
    bundle: AuthenticatedFinancialStatements,
) -> None:
    """Reject structurally invalid statement bundles. Never invent replacements."""
    if not bundle.identity.symbol or not str(bundle.identity.symbol).strip():
        raise InvalidProviderDataError("statements missing identity.symbol")
    if not bundle.provenance.provider_id.strip():
        raise InvalidProviderDataError("statements missing provider_id provenance")
    if not bundle.provenance.provider_name.strip():
        raise InvalidProviderDataError("statements missing provider_name provenance")
    if bundle.provenance.source_type.strip().lower() in _DISALLOWED_SOURCE:
        raise InvalidProviderDataError(
            f"disallowed provenance source_type={bundle.provenance.source_type!r}"
        )
    if not bundle.periods:
        raise InvalidProviderDataError(
            "authenticated statements must include at least one period "
            "(use None from adapter when unavailable)"
        )
    for i, period in enumerate(bundle.periods):
        _validate_period(period, i)
