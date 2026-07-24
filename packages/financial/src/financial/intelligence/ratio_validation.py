"""Validation for Financial Ratio Engine inputs."""

from __future__ import annotations

import math
from typing import Sequence

from financial.exceptions import FinancialRatioError, FinancialValidationError
from financial.models import FinancialSnapshot, FinancialStatements
from financial.validation import ValidationResult, validate_statements

__all__ = [
    "FinancialRatioError",
    "validate_ratio_inputs",
    "coerce_ratio_series",
]


def _reject(message: str) -> None:
    raise FinancialRatioError(message)


def _ensure_finite(name: str, value: float | None) -> None:
    if value is None:
        return
    if math.isnan(value):
        _reject(f"{name} is NaN")
    if math.isinf(value):
        _reject(f"{name} is infinite")


def validate_ratio_inputs(
    statements: FinancialStatements,
    *,
    require_revenue: bool = True,
    require_total_assets: bool = True,
) -> ValidationResult:
    """Validate one period triad for ratio analysis."""
    income = statements.income_statement
    balance = statements.balance_sheet
    cash = statements.cash_flow

    for prefix, values in (
        ("income", income.values()),
        ("balance", balance.values()),
        ("cash_flow", cash.values()),
    ):
        for key, val in values.items():
            _ensure_finite(f"{prefix}.{key}", val)

    if require_revenue and income.revenue is None:
        _reject("Missing required statements: revenue")
    if require_revenue and income.revenue == 0:
        _reject("Divide-by-zero: revenue is zero")
    if require_total_assets and balance.total_assets is None:
        _reject("Missing required statements: total_assets")
    if require_total_assets and balance.total_assets == 0:
        _reject("Divide-by-zero: total_assets is zero")

    # Impossible: |net margin| absurd when both present
    if income.revenue and income.net_income is not None:
        margin = income.net_income / income.revenue
        if abs(margin) > 5.0:
            _reject(f"Impossible ratios: net_margin={margin:.4f}")

    try:
        result = validate_statements(
            statements,
            require_revenue=require_revenue,
            require_total_assets=require_total_assets,
        )
    except FinancialValidationError as exc:
        raise FinancialRatioError(str(exc)) from exc

    return result


def coerce_ratio_series(
    source: FinancialStatements
    | FinancialSnapshot
    | dict
    | Sequence[FinancialStatements],
) -> tuple[list[FinancialStatements], dict]:
    """Normalize inputs into chronologically ordered statement series."""
    meta: dict = {}

    if isinstance(source, dict):
        if "statements" in source or "version" in source:
            source = FinancialSnapshot.from_dict(source)
        elif "period" in source or "income_statement" in source:
            source = FinancialStatements.from_dict(source)
        else:
            _reject(
                "Unsupported payload: expected FinancialStatements or "
                "FinancialSnapshot"
            )

    if isinstance(source, FinancialStatements):
        stmts = [source]
        meta["period_end"] = source.period.period_end.isoformat()
    elif isinstance(source, FinancialSnapshot):
        meta["company"] = source.company.company
        meta["ticker"] = source.company.ticker
        if not source.statements:
            _reject("Empty financial snapshot: no statements to analyze")
        ordered = sorted(source.statements, key=lambda s: s.period.period_end)
        seen: set[tuple] = set()
        for s in ordered:
            key = s.period.key()
            if key in seen:
                _reject(
                    f"Duplicate periods: {s.period.period_type.value} ending "
                    f"{s.period.period_end.isoformat()}"
                )
            seen.add(key)
        stmts = list(ordered)
        meta["period_end"] = ordered[-1].period.period_end.isoformat()
    elif isinstance(source, (list, tuple)):
        if not source:
            _reject("Empty history sequence")
        for item in source:
            if not isinstance(item, FinancialStatements):
                _reject("History items must be FinancialStatements")
        stmts = sorted(source, key=lambda s: s.period.period_end)
        seen_keys: set[tuple] = set()
        for s in stmts:
            key = s.period.key()
            if key in seen_keys:
                _reject(
                    f"Duplicate periods: {s.period.period_type.value} ending "
                    f"{s.period.period_end.isoformat()}"
                )
            seen_keys.add(key)
        meta["period_end"] = stmts[-1].period.period_end.isoformat()
    else:
        _reject(
            "Accept ONLY FinancialStatements or Normalized Financial Snapshot"
        )

    return stmts, meta
