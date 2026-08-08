"""Authenticated financial statement models (EPIC-D002) — RS-003 + provenance.

Retrieval and validation only — no ratios, valuation, or scoring are computed here.
Provider-supplied ratio fields are pass-through as-reported values when present.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

__all__ = [
    "AuthenticatedFinancialStatements",
    "AuthenticatedStatementPeriod",
    "CompanyIdentity",
    "FinancialStatementProvenance",
    "StatementField",
    "StatementPeriodKind",
    "utc_now",
]

# Canonical period kinds aligned with contracts.StatementPeriodType + restated flag.
StatementPeriodKind = str  # "annual" | "quarterly" | "ttm"


@dataclass(frozen=True, slots=True)
class StatementField:
    """Single numeric statement field — absent means unavailable, never invented."""

    value: Decimal | None
    available: bool

    @classmethod
    def of(cls, value: Decimal | float | int | str | None) -> StatementField:
        if value is None:
            return cls(value=None, available=False)
        if isinstance(value, str) and not value.strip():
            return cls(value=None, available=False)
        try:
            dec = value if isinstance(value, Decimal) else Decimal(str(value))
        except Exception:
            return cls(value=None, available=False)
        return cls(value=dec, available=True)

    @classmethod
    def missing(cls) -> StatementField:
        return cls(value=None, available=False)


@dataclass(frozen=True, slots=True)
class CompanyIdentity:
    """Resolved company identifier (read-only resolution metadata)."""

    symbol: str
    exchange: str | None = None
    company_name: str | None = None
    isin: str | None = None
    cik: str | None = None
    provider_company_id: str | None = None
    currency: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "company_name": self.company_name,
            "isin": self.isin,
            "cik": self.cik,
            "provider_company_id": self.provider_company_id,
            "currency": self.currency,
        }


@dataclass(frozen=True, slots=True)
class FinancialStatementProvenance:
    """Source metadata for CV-001 / RS-003 / RS-010."""

    provider_id: str
    provider_name: str
    source_type: str
    retrieved_at: datetime
    as_of: datetime | None = None
    request_id: str | None = None
    cache_hit: bool = False
    auth_mode: str = "api_key"
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "source_type": self.source_type,
            "retrieved_at": self.retrieved_at.isoformat(),
            "as_of": self.as_of.isoformat() if self.as_of else None,
            "request_id": self.request_id,
            "cache_hit": self.cache_hit,
            "auth_mode": self.auth_mode,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class AuthenticatedStatementPeriod:
    """One authenticated filing period — as-reported line items only."""

    period_type: StatementPeriodKind
    fiscal_year: int
    fiscal_quarter: int | None
    period_end: date
    filing_date: date | None
    reporting_currency: str
    restated: bool
    # Income statement
    revenue: StatementField
    cost_of_revenue: StatementField
    gross_profit: StatementField
    operating_income: StatementField
    ebit: StatementField
    ebitda: StatementField
    net_income: StatementField
    eps_basic: StatementField
    eps_diluted: StatementField
    # Balance sheet
    cash_and_equivalents: StatementField
    current_assets: StatementField
    total_assets: StatementField
    current_liabilities: StatementField
    total_liabilities: StatementField
    total_equity: StatementField
    total_debt: StatementField
    long_term_debt: StatementField
    # Cash flow
    operating_cash_flow: StatementField
    investing_cash_flow: StatementField
    financing_cash_flow: StatementField
    capital_expenditures: StatementField
    free_cash_flow: StatementField
    dividends_paid: StatementField
    share_buybacks: StatementField
    # Provider-supplied ratios / metrics (pass-through only — never calculated here)
    roe: StatementField
    roce: StatementField
    debt_to_equity: StatementField
    working_capital: StatementField
    gross_margin: StatementField
    operating_margin: StatementField
    net_margin: StatementField
    revenue_growth: StatementField
    eps_growth: StatementField
    # P1-02 integrity metadata — required for authoritative valuation path.
    # statement_basis: "consolidated" | "standalone"
    # unit_scale: actual|thousands|millions|billions|lakh|crore|...
    statement_basis: str | None = None
    unit_scale: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        def _f(q: StatementField) -> float | None:
            if not q.available or q.value is None:
                return None
            return float(q.value)

        return {
            "period_type": self.period_type,
            "fiscal_year": self.fiscal_year,
            "fiscal_quarter": self.fiscal_quarter,
            "period_end": self.period_end.isoformat(),
            "filing_date": self.filing_date.isoformat() if self.filing_date else None,
            "reporting_currency": self.reporting_currency,
            "restated": self.restated,
            "statement_basis": self.statement_basis,
            "unit_scale": self.unit_scale,
            "income_statement": {
                "revenue": _f(self.revenue),
                "cost_of_revenue": _f(self.cost_of_revenue),
                "gross_profit": _f(self.gross_profit),
                "operating_income": _f(self.operating_income),
                "ebit": _f(self.ebit),
                "ebitda": _f(self.ebitda),
                "net_income": _f(self.net_income),
                "eps_basic": _f(self.eps_basic),
                "eps_diluted": _f(self.eps_diluted),
            },
            "balance_sheet": {
                "cash_and_equivalents": _f(self.cash_and_equivalents),
                "current_assets": _f(self.current_assets),
                "total_assets": _f(self.total_assets),
                "current_liabilities": _f(self.current_liabilities),
                "total_liabilities": _f(self.total_liabilities),
                "total_equity": _f(self.total_equity),
                "total_debt": _f(self.total_debt),
                "long_term_debt": _f(self.long_term_debt),
            },
            "cash_flow": {
                "operating_cash_flow": _f(self.operating_cash_flow),
                "investing_cash_flow": _f(self.investing_cash_flow),
                "financing_cash_flow": _f(self.financing_cash_flow),
                "capital_expenditures": _f(self.capital_expenditures),
                "free_cash_flow": _f(self.free_cash_flow),
                "dividends_paid": _f(self.dividends_paid),
                "share_buybacks": _f(self.share_buybacks),
            },
            "ratios": {
                "roe": _f(self.roe),
                "roce": _f(self.roce),
                "debt_to_equity": _f(self.debt_to_equity),
                "working_capital": _f(self.working_capital),
                "gross_margin": _f(self.gross_margin),
                "operating_margin": _f(self.operating_margin),
                "net_margin": _f(self.net_margin),
                "revenue_growth": _f(self.revenue_growth),
                "eps_growth": _f(self.eps_growth),
            },
        }


@dataclass(frozen=True, slots=True)
class AuthenticatedFinancialStatements:
    """Authenticated multi-period statement bundle for one company."""

    identity: CompanyIdentity
    periods: tuple[AuthenticatedStatementPeriod, ...]
    provenance: FinancialStatementProvenance
    reporting_currency: str | None = None

    def has_any_period(self) -> bool:
        return len(self.periods) > 0

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "authenticated": True,
            "identity": self.identity.to_dict(),
            "reporting_currency": self.reporting_currency
            or self.identity.currency,
            "periods": [p.to_public_dict() for p in self.periods],
            "provenance": self.provenance.to_dict(),
        }


def utc_now() -> datetime:
    return datetime.now(tz=UTC)
