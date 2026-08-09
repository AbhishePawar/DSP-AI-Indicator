"""P1-02 — financial statement integrity for the authenticated valuation path.

Fail closed with ``Data unavailable.`` when identity, basis, period, unit,
currency, shares/EPS, cash-flow, or balance-sheet integrity cannot be proven.
Does not invent FX, corporate-action engines, or valuation methodologies.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from data_engine.financial_statement.models import (
    AuthenticatedStatementPeriod,
    StatementField,
)

__all__ = [
    "ALLOWED_STATEMENT_BASIS",
    "FinancialIntegrityError",
    "assert_balance_sheet_integrity",
    "assert_cash_flow_integrity",
    "assert_duplicate_periods",
    "assert_eps_share_integrity",
    "assert_profitability_sanity",
    "assert_share_count_integrity",
    "assert_statement_basis",
    "assert_unit_homogeneous",
    "normalize_periods_to_actual",
    "unit_scale_factor",
]

DATA_UNAVAILABLE = "Data unavailable."


class FinancialIntegrityError(ValueError):
    """Financial integrity gate failure (P1-02)."""

    def __init__(self, message: str = DATA_UNAVAILABLE) -> None:
        super().__init__(message if message else DATA_UNAVAILABLE)

ALLOWED_STATEMENT_BASIS = frozenset({"consolidated", "standalone"})

# Explicit scale factors to ACTUAL currency units (no FX).
_UNIT_FACTORS: dict[str, float] = {
    "actual": 1.0,
    "absolute": 1.0,
    "units": 1.0,
    "unit": 1.0,
    "thousand": 1_000.0,
    "thousands": 1_000.0,
    "million": 1_000_000.0,
    "millions": 1_000_000.0,
    "billion": 1_000_000_000.0,
    "billions": 1_000_000_000.0,
    "lakh": 100_000.0,
    "lakhs": 100_000.0,
    "crore": 10_000_000.0,
    "crores": 10_000_000.0,
}

_MONETARY_FIELDS = (
    "revenue",
    "cost_of_revenue",
    "gross_profit",
    "operating_income",
    "ebit",
    "ebitda",
    "net_income",
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
    "working_capital",
)

# EPS / ratio fields are never unit-scaled.


def unit_scale_factor(unit_scale: str | None) -> float:
    """Return multiply-to-ACTUAL factor, or raise if unknown/missing."""
    if unit_scale is None or not str(unit_scale).strip():
        raise FinancialIntegrityError(
            f"{DATA_UNAVAILABLE} (statement unit_scale unavailable)"
        )
    key = str(unit_scale).strip().lower()
    if key not in _UNIT_FACTORS:
        raise FinancialIntegrityError(
            f"{DATA_UNAVAILABLE} (unsupported unit_scale={unit_scale!r})"
        )
    return _UNIT_FACTORS[key]


def assert_statement_basis(
    periods: Iterable[AuthenticatedStatementPeriod],
) -> str:
    """Require a single explicit consolidated|standalone basis."""
    bases = {
        str(p.statement_basis or "").strip().lower()
        for p in periods
    }
    bases.discard("")
    if not bases:
        raise FinancialIntegrityError(
            f"{DATA_UNAVAILABLE} (statement_basis unavailable)"
        )
    if len(bases) > 1:
        raise FinancialIntegrityError(
            f"{DATA_UNAVAILABLE} (mixed consolidated/standalone statements)"
        )
    basis = next(iter(bases))
    if basis not in ALLOWED_STATEMENT_BASIS:
        raise FinancialIntegrityError(
            f"{DATA_UNAVAILABLE} (invalid statement_basis={basis!r})"
        )
    # Also reject periods that omit basis while others declare it.
    for period in periods:
        raw = str(period.statement_basis or "").strip().lower()
        if raw != basis:
            raise FinancialIntegrityError(
                f"{DATA_UNAVAILABLE} (inconsistent statement_basis)"
            )
    return basis


def assert_unit_homogeneous(
    periods: Iterable[AuthenticatedStatementPeriod],
) -> str:
    """Require a single explicit unit_scale across selected periods."""
    units = {
        str(p.unit_scale or "").strip().lower()
        for p in periods
    }
    units.discard("")
    if not units:
        raise FinancialIntegrityError(
            f"{DATA_UNAVAILABLE} (statement unit_scale unavailable)"
        )
    if len(units) > 1:
        raise FinancialIntegrityError(
            f"{DATA_UNAVAILABLE} (mixed statement unit scales)"
        )
    unit = next(iter(units))
    unit_scale_factor(unit)  # validate known
    for period in periods:
        raw = str(period.unit_scale or "").strip().lower()
        if raw != unit:
            raise FinancialIntegrityError(
                f"{DATA_UNAVAILABLE} (inconsistent unit_scale)"
            )
    return unit


def assert_duplicate_periods(
    periods: tuple[AuthenticatedStatementPeriod, ...],
) -> None:
    """Reject duplicate fiscal periods / identical period ends in one set."""
    ends = [p.period_end for p in periods]
    if len(ends) != len(set(ends)):
        raise FinancialIntegrityError(
            f"{DATA_UNAVAILABLE} (duplicate statement periods)"
        )
    if not periods:
        return
    kind = periods[0].period_type
    if kind == "quarterly":
        keys = []
        for p in periods:
            if p.fiscal_quarter is None:
                raise FinancialIntegrityError(
                    f"{DATA_UNAVAILABLE} (quarterly period missing fiscal_quarter)"
                )
            keys.append((p.fiscal_year, p.fiscal_quarter))
        if len(keys) != len(set(keys)):
            raise FinancialIntegrityError(
                f"{DATA_UNAVAILABLE} (duplicate fiscal quarter)"
            )
    elif kind in {"annual", "ttm"}:
        keys = [(p.period_type, p.fiscal_year) for p in periods]
        if len(keys) != len(set(keys)):
            raise FinancialIntegrityError(
                f"{DATA_UNAVAILABLE} (duplicate fiscal period)"
            )


def _scale_field(field: StatementField, factor: float) -> StatementField:
    if not field.available or field.value is None:
        return field
    if factor == 1.0:
        return field
    return StatementField.of(float(field.value) * factor)


def normalize_periods_to_actual(
    periods: tuple[AuthenticatedStatementPeriod, ...],
    *,
    source_unit: str,
) -> tuple[AuthenticatedStatementPeriod, ...]:
    """Scale monetary fields to ACTUAL units; leave EPS/ratios untouched."""
    factor = unit_scale_factor(source_unit)
    if factor == 1.0:
        return tuple(
            replace(p, unit_scale="actual") for p in periods
        )
    out: list[AuthenticatedStatementPeriod] = []
    for period in periods:
        updates = {
            name: _scale_field(getattr(period, name), factor)
            for name in _MONETARY_FIELDS
        }
        out.append(replace(period, unit_scale="actual", **updates))
    return tuple(out)


def assert_profitability_sanity(period: AuthenticatedStatementPeriod) -> None:
    """Reject impossible revenue; allow legitimate losses."""
    revenue = _num(period.revenue)
    if revenue is not None and revenue < 0:
        raise FinancialIntegrityError(
            f"{DATA_UNAVAILABLE} (negative revenue)"
        )
    op = _num(period.operating_income)
    if op is None:
        op = _num(period.ebit)
    pat = _num(period.net_income)
    if revenue is not None and revenue > 0 and op is not None:
        # Operating profit cannot exceed revenue by a material absurd margin.
        if op > revenue * 1.5 + max(1.0, abs(revenue) * 0.01):
            raise FinancialIntegrityError(
                f"{DATA_UNAVAILABLE} (operating profit inconsistent with revenue)"
            )
    if revenue is not None and revenue > 0 and pat is not None:
        if pat > revenue * 1.5 + max(1.0, abs(revenue) * 0.01):
            raise FinancialIntegrityError(
                f"{DATA_UNAVAILABLE} (PAT inconsistent with revenue)"
            )


def assert_cash_flow_integrity(period: AuthenticatedStatementPeriod) -> None:
    """Validate FCF ≈ CFO − |capex| using repository convention."""
    ocf = _num(period.operating_cash_flow)
    capex = _num(period.capital_expenditures)
    fcf = _num(period.free_cash_flow)
    if ocf is None or capex is None or fcf is None:
        return  # incomplete — methods that need FCF will degrade honestly
    expected = ocf - abs(capex)
    tol = max(1.0, abs(expected) * 0.15, abs(ocf) * 0.02)
    if abs(fcf - expected) > tol:
        raise FinancialIntegrityError(
            f"{DATA_UNAVAILABLE} (FCF inconsistent with CFO - |capex|)"
        )


def assert_balance_sheet_integrity(
    period: AuthenticatedStatementPeriod,
    *,
    tolerance: float = 0.02,
) -> None:
    """When Assets, Liabilities, Equity are all present: Assets ≈ L + E."""
    assets = _num(period.total_assets)
    liabilities = _num(period.total_liabilities)
    equity = _num(period.total_equity)
    if assets is None or liabilities is None or equity is None:
        return
    rhs = liabilities + equity
    if abs(assets - rhs) > tolerance * max(1.0, abs(assets)):
        raise FinancialIntegrityError(
            f"{DATA_UNAVAILABLE} (balance sheet accounting equation failed)"
        )


def assert_eps_share_integrity(
    period: AuthenticatedStatementPeriod,
    shares: float,
    *,
    tolerance: float = 0.20,
) -> None:
    """When PAT + EPS + shares present: EPS ≈ PAT / shares (material check)."""
    if shares <= 0:
        raise FinancialIntegrityError(
            f"{DATA_UNAVAILABLE} (shares outstanding unavailable)"
        )
    pat = _num(period.net_income)
    eps = _num(period.eps_basic)
    if eps is None:
        eps = _num(period.eps_diluted)
    if pat is None or eps is None:
        return
    if abs(eps) < 1e-12:
        return
    implied = pat / shares
    denom = max(abs(eps), abs(implied), 1e-9)
    if abs(implied - eps) / denom > tolerance:
        raise FinancialIntegrityError(
            f"{DATA_UNAVAILABLE} (EPS inconsistent with PAT/shares)"
        )


def assert_share_count_integrity(
    *,
    quote_shares: float | None,
    derived_shares: float | None,
    tolerance: float = 0.25,
) -> None:
    """Detect material quote vs NI/EPS share-count mismatch (CA / split proxy)."""
    if quote_shares is None or derived_shares is None:
        return
    if quote_shares <= 0 or derived_shares <= 0:
        raise FinancialIntegrityError(
            f"{DATA_UNAVAILABLE} (invalid share count)"
        )
    denom = max(quote_shares, derived_shares)
    if abs(quote_shares - derived_shares) / denom > tolerance:
        raise FinancialIntegrityError(
            f"{DATA_UNAVAILABLE} (share-count mismatch; corporate-action "
            "adjustment unavailable)"
        )


def _num(field: StatementField) -> float | None:
    if not field.available or field.value is None:
        return None
    return float(field.value)
