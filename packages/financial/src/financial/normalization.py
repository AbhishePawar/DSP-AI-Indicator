"""Normalization helpers for canonical financial statements.

Provider-agnostic: alias maps and unit/currency scaling only.
No market APIs. No NSE/BSE-specific logic.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from financial.balance_sheet import BALANCE_SHEET_FIELDS, BalanceSheet
from financial.cash_flow import CASH_FLOW_FIELDS, CashFlowStatement
from financial.currency import CurrencyCode, CurrencyRef
from financial.income_statement import INCOME_STATEMENT_FIELDS, IncomeStatement
from financial.metadata import StatementMetadata, UnitScale
from financial.models import FinancialSnapshot, FinancialStatements
from financial.period import FinancialPeriod

__all__ = [
    "FIELD_ALIASES",
    "UNIT_SCALE_FACTORS",
    "canonicalize_field_name",
    "map_raw_fields",
    "scale_values",
    "normalize_statements",
    "normalize_snapshot",
]

# Common provider / spreadsheet aliases → canonical field names.
FIELD_ALIASES: Mapping[str, str] = {
    "sales": "revenue",
    "total_revenue": "revenue",
    "total_sales": "revenue",
    "net_sales": "revenue",
    "cost_of_goods_sold": "cogs",
    "cost_of_revenue": "cogs",
    "cost_of_sales": "cogs",
    "research_and_development": "rd",
    "research_development": "rd",
    "selling_general_administrative": "sga",
    "selling_general_and_administrative": "sga",
    "operating_income": "ebit",
    "income_before_tax": "pretax_income",
    "income_before_taxes": "pretax_income",
    "earnings_before_tax": "pretax_income",
    "tax_expense": "tax",
    "income_tax": "tax",
    "income_tax_expense": "tax",
    "net_earnings": "net_income",
    "profit": "net_income",
    "basic_eps": "eps",
    "eps_basic": "eps",
    "eps_diluted": "diluted_eps",
    "shares_outstanding": "weighted_shares",
    "weighted_average_shares": "weighted_shares",
    "cash_and_equivalents": "cash",
    "cash_and_cash_equivalents": "cash",
    "receivables": "accounts_receivable",
    "trade_receivables": "accounts_receivable",
    "property_plant_equipment": "ppe",
    "property_plant_and_equipment": "ppe",
    "net_ppe": "ppe",
    "intangible_assets": "intangibles",
    "total_liab": "total_liabilities",
    "stockholders_equity": "total_equity",
    "shareholders_equity": "total_equity",
    "total_stockholders_equity": "total_equity",
    "common_stock": "share_capital",
    "cash_from_operations": "operating_cash_flow",
    "cfo": "operating_cash_flow",
    "capital_expenditures": "capex",
    "capital_expenditure": "capex",
    "purchase_of_ppe": "capex",
    "cash_from_investing": "investing_cash_flow",
    "cash_from_financing": "financing_cash_flow",
    "fcf": "free_cash_flow",
    "dividend_paid": "dividends_paid",
    "repurchase_of_stock": "share_buybacks",
    "issuance_of_stock": "share_issuance",
}

UNIT_SCALE_FACTORS: Mapping[UnitScale, float] = {
    UnitScale.ACTUAL: 1.0,
    UnitScale.THOUSANDS: 1_000.0,
    UnitScale.MILLIONS: 1_000_000.0,
    UnitScale.BILLIONS: 1_000_000_000.0,
}


def canonicalize_field_name(name: str) -> str:
    """Map an alias or noisy name onto a canonical snake_case field."""
    key = (
        str(name)
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
        .replace("/", "_")
    )
    while "__" in key:
        key = key.replace("__", "_")
    return FIELD_ALIASES.get(key, key)


def map_raw_fields(
    raw: Mapping[str, Any],
    *,
    allowed: tuple[str, ...] | None = None,
) -> dict[str, float | None]:
    """Map a raw dict of aliases onto canonical numeric fields.

    Unknown keys are dropped. Empty / missing values become ``None``.
    """
    allowed_set = set(allowed) if allowed is not None else None
    out: dict[str, float | None] = {}
    for key, value in raw.items():
        canon = canonicalize_field_name(str(key))
        if allowed_set is not None and canon not in allowed_set:
            continue
        if value is None or value == "":
            out[canon] = None
            continue
        try:
            out[canon] = float(value)
        except (TypeError, ValueError):
            # Non-numeric retained as missing for domain purity
            out[canon] = None
    return out


def scale_values(
    values: Mapping[str, float | None],
    *,
    from_scale: UnitScale,
    to_scale: UnitScale = UnitScale.ACTUAL,
) -> dict[str, float | None]:
    """Convert numeric values between unit scales (no FX)."""
    if from_scale is to_scale:
        return dict(values)
    factor = UNIT_SCALE_FACTORS[from_scale] / UNIT_SCALE_FACTORS[to_scale]
    return {
        k: (None if v is None else v * factor) for k, v in values.items()
    }


def _build_income(raw: Mapping[str, Any]) -> IncomeStatement:
    mapped = map_raw_fields(raw, allowed=INCOME_STATEMENT_FIELDS)
    return IncomeStatement.from_dict(mapped)


def _build_balance(raw: Mapping[str, Any]) -> BalanceSheet:
    mapped = map_raw_fields(raw, allowed=BALANCE_SHEET_FIELDS)
    return BalanceSheet.from_dict(mapped)


def _build_cash(raw: Mapping[str, Any]) -> CashFlowStatement:
    mapped = map_raw_fields(raw, allowed=CASH_FLOW_FIELDS)
    return CashFlowStatement.from_dict(mapped)


def normalize_statements(
    statements: FinancialStatements,
    *,
    target_scale: UnitScale = UnitScale.ACTUAL,
    target_currency: CurrencyRef | CurrencyCode | str | None = None,
) -> FinancialStatements:
    """Normalize one period's statements to a target unit scale.

    Currency retargeting updates metadata only in F2.1 (no FX conversion).
    """
    meta = statements.statement_metadata
    from_scale = meta.unit_scale
    income_vals = scale_values(
        statements.income_statement.values(),
        from_scale=from_scale,
        to_scale=target_scale,
    )
    balance_vals = scale_values(
        statements.balance_sheet.values(),
        from_scale=from_scale,
        to_scale=target_scale,
    )
    cash_vals = scale_values(
        statements.cash_flow.values(),
        from_scale=from_scale,
        to_scale=target_scale,
    )

    currency = meta.currency
    period = statements.period
    if target_currency is not None:
        currency = CurrencyRef.parse(target_currency)
        period = replace(period, currency=currency)

    new_meta = StatementMetadata(
        unit_scale=target_scale,
        currency=currency,
        source=meta.source,
        notes=meta.notes,
    )
    return FinancialStatements(
        period=period,
        income_statement=IncomeStatement.from_dict(income_vals),
        balance_sheet=BalanceSheet.from_dict(balance_vals),
        cash_flow=CashFlowStatement.from_dict(cash_vals),
        statement_metadata=new_meta,
    )


def normalize_snapshot(
    snapshot: FinancialSnapshot,
    *,
    target_scale: UnitScale = UnitScale.ACTUAL,
    target_currency: CurrencyRef | CurrencyCode | str | None = None,
) -> FinancialSnapshot:
    """Normalize every period in a snapshot."""
    normalized = tuple(
        normalize_statements(
            s, target_scale=target_scale, target_currency=target_currency
        )
        for s in snapshot.statements
    )
    company = snapshot.company
    if target_currency is not None:
        company = replace(
            company, reporting_currency=CurrencyRef.parse(target_currency)
        )
    return FinancialSnapshot(
        company=company,
        statements=normalized,
        version=snapshot.version,
    )


def statements_from_raw(
    *,
    period: FinancialPeriod,
    income: Mapping[str, Any] | None = None,
    balance: Mapping[str, Any] | None = None,
    cash_flow: Mapping[str, Any] | None = None,
    statement_metadata: StatementMetadata | None = None,
) -> FinancialStatements:
    """Build canonical statements from aliased raw provider dicts."""
    return FinancialStatements(
        period=period,
        income_statement=_build_income(income or {}),
        balance_sheet=_build_balance(balance or {}),
        cash_flow=_build_cash(cash_flow or {}),
        statement_metadata=statement_metadata or StatementMetadata(),
    )
