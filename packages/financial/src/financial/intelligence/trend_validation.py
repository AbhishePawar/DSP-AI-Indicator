"""Validation for Trend & Time-Series Intelligence inputs."""

from __future__ import annotations

import math
from typing import Sequence

from financial.exceptions import FinancialValidationError, TrendAnalysisError
from financial.intelligence.trend_models import FinancialStatementsHistory
from financial.models import FinancialSnapshot, FinancialStatements
from financial.validation import ValidationResult, validate_statements

__all__ = [
    "TrendAnalysisError",
    "validate_trend_history",
    "coerce_trend_history",
]

_MAX_PERIODS = 20
_MIN_PERIODS = 2


def _reject(message: str) -> None:
    raise TrendAnalysisError(message)


def _ensure_finite(name: str, value: float | None) -> None:
    if value is None:
        return
    if math.isnan(value):
        _reject(f"{name} is NaN")
    if math.isinf(value):
        _reject(f"{name} is infinite")


def validate_trend_history(
    statements: Sequence[FinancialStatements],
) -> ValidationResult:
    """Validate ordered multi-period history for trend analysis."""
    if len(statements) < _MIN_PERIODS:
        _reject(f"Missing reporting periods: need at least {_MIN_PERIODS}")
    if len(statements) > _MAX_PERIODS:
        _reject(f"History exceeds maximum supported periods ({_MAX_PERIODS})")

    checks: list[str] = [f"period_count={len(statements)}"]
    warnings: list[str] = []

    ends = [s.period.period_end for s in statements]
    if ends != sorted(ends):
        _reject("Unordered periods: period_end must be ascending")

    seen: set[tuple] = set()
    for i, stmt in enumerate(statements):
        key = stmt.period.key()
        if key in seen:
            _reject(
                f"Duplicate reporting dates: {stmt.period.period_type.value} "
                f"ending {stmt.period.period_end.isoformat()}"
            )
        seen.add(key)
        for prefix, values in (
            ("income", stmt.income_statement.values()),
            ("balance", stmt.balance_sheet.values()),
            ("cash_flow", stmt.cash_flow.values()),
        ):
            for field, val in values.items():
                _ensure_finite(f"[{i}].{prefix}.{field}", val)
        try:
            result = validate_statements(stmt)
            checks.extend(result.checks)
            warnings.extend(result.warnings)
        except FinancialValidationError as exc:
            raise TrendAnalysisError(str(exc)) from exc

    # CAGR validity soft check when revenue series present
    revenues = [s.income_statement.revenue for s in statements]
    if all(r is not None for r in revenues):
        if revenues[0] is not None and revenues[0] <= 0 and revenues[-1] and revenues[-1] > 0:
            warnings.append("Invalid CAGR inputs: non-positive start revenue")

    return ValidationResult(
        ok=True,
        checks=tuple(dict.fromkeys(checks)),
        errors=(),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def coerce_trend_history(
    source: FinancialStatementsHistory
    | FinancialSnapshot
    | dict
    | Sequence[FinancialStatements],
) -> tuple[list[FinancialStatements], dict]:
    """Normalize trend inputs into chronologically ordered statements."""
    meta: dict = {}

    if isinstance(source, dict):
        if "company" in source or "version" in source:
            source = FinancialSnapshot.from_dict(source)
        elif "statements" in source and isinstance(source.get("statements"), list):
            source = FinancialStatementsHistory(
                statements=tuple(
                    FinancialStatements.from_dict(s) for s in source["statements"]
                )
            )
        else:
            _reject(
                "Unsupported payload: expected FinancialStatementsHistory or "
                "FinancialSnapshot"
            )

    if isinstance(source, FinancialStatementsHistory):
        stmts = list(source.statements)
    elif isinstance(source, FinancialSnapshot):
        meta["company"] = source.company.company
        meta["ticker"] = source.company.ticker
        stmts = list(source.statements)
    elif isinstance(source, (list, tuple)):
        for item in source:
            if not isinstance(item, FinancialStatements):
                _reject("History items must be FinancialStatements")
        stmts = list(source)
    else:
        _reject(
            "Accept ONLY FinancialStatementsHistory or ordered historical "
            "normalized financial snapshots"
        )

    if not stmts:
        _reject("Missing reporting periods: empty history")

    # Sort then validate order / duplicates
    stmts = sorted(stmts, key=lambda s: s.period.period_end)
    meta["period_ends"] = tuple(s.period.period_end.isoformat() for s in stmts)
    return stmts, meta
