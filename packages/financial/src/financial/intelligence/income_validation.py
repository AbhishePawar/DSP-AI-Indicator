"""Validation for Income Statement Intelligence inputs."""

from __future__ import annotations

import math
from typing import Sequence

from financial.exceptions import FinancialValidationError, IncomeAnalysisError
from financial.income_statement import IncomeStatement
from financial.models import FinancialSnapshot, FinancialStatements
from financial.validation import ValidationResult, validate_statements

__all__ = ["IncomeAnalysisError", "validate_income_for_analysis", "coerce_income_series"]


def _reject(message: str) -> None:
    raise IncomeAnalysisError(message)


def _ensure_finite(name: str, value: float | None) -> None:
    if value is None:
        return
    if math.isnan(value):
        _reject(f"{name} is NaN")
    if math.isinf(value):
        _reject(f"{name} is infinite")


def _check_income_hard(income: IncomeStatement, *, require_revenue: bool) -> list[str]:
    """Return soft warnings; raise IncomeAnalysisError on hard failures."""
    warnings: list[str] = []

    for key, val in income.values().items():
        _ensure_finite(key, val)

    if require_revenue:
        if income.revenue is None:
            _reject("Missing Revenue")
        if income.revenue == 0:
            _reject("Divide-by-zero: revenue is zero")

    if income.weighted_shares is not None and income.weighted_shares < 0:
        _reject("Negative Shares")

    if income.eps is not None and income.weighted_shares is not None:
        if income.weighted_shares == 0 and income.eps != 0:
            _reject("Invalid EPS: non-zero EPS with zero weighted shares")

    if income.diluted_eps is not None and income.eps is not None:
        # Diluted EPS should not exceed basic EPS for positive earnings
        if income.eps > 0 and income.diluted_eps > income.eps * 1.0001:
            _reject("Invalid EPS: diluted EPS exceeds basic EPS")

    # Impossible margins when both numerator and revenue present
    revenue = income.revenue
    if revenue is not None and revenue != 0:
        pairs = (
            ("gross_margin", income.gross_profit),
            ("ebit_margin", income.ebit),
            ("ebitda_margin", income.ebitda),
            ("net_margin", income.net_income),
            ("pretax_margin", income.pretax_income),
        )
        for label, num in pairs:
            if num is None:
                continue
            margin = num / revenue
            if math.isnan(margin) or math.isinf(margin):
                _reject(f"Impossible Margins: {label} is non-finite")
            if abs(margin) > 5.0:
                _reject(
                    f"Impossible Margins: {label}={margin:.4f} exceeds ±500%"
                )

    if income.revenue is not None and income.revenue < 0:
        warnings.append("negative revenue")

    return warnings


def validate_income_for_analysis(
    income: IncomeStatement,
    *,
    statements: FinancialStatements | None = None,
    require_revenue: bool = True,
) -> ValidationResult:
    """Validate income inputs for analysis; raise :class:`IncomeAnalysisError`.

    Reuses Financial Domain statement validation when a full period triad is
    provided.
    """
    checks: list[str] = []
    warnings: list[str] = []

    try:
        warnings.extend(_check_income_hard(income, require_revenue=require_revenue))
    except IncomeAnalysisError:
        raise

    if income.revenue is not None:
        checks.append("revenue present")

    if statements is not None:
        try:
            result = validate_statements(
                statements,
                require_revenue=require_revenue,
            )
            checks.extend(result.checks)
            warnings.extend(result.warnings)
        except FinancialValidationError as exc:
            raise IncomeAnalysisError(str(exc)) from exc

    return ValidationResult(
        ok=True,
        checks=tuple(dict.fromkeys(checks)),
        errors=(),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def coerce_income_series(
    source: IncomeStatement
    | FinancialStatements
    | FinancialSnapshot
    | dict
    | Sequence[IncomeStatement | FinancialStatements],
) -> tuple[list[IncomeStatement], list[FinancialStatements | None], dict]:
    """Normalize engine inputs into chronologically ordered income series.

    Returns ``(incomes, statements_or_none, meta)`` where ``meta`` may include
    company / ticker from a snapshot.
    """
    meta: dict = {}

    if isinstance(source, dict):
        if "statements" in source or "version" in source:
            source = FinancialSnapshot.from_dict(source)
        elif "income_statement" in source or "period" in source:
            source = FinancialStatements.from_dict(source)
        elif any(k in source for k in ("revenue", "net_income", "ebit")):
            source = IncomeStatement.from_dict(source)
        else:
            _reject(
                "Unsupported payload: expected IncomeStatement fields, "
                "FinancialStatements, or FinancialSnapshot"
            )

    incomes: list[IncomeStatement] = []
    stmts: list[FinancialStatements | None] = []

    if isinstance(source, IncomeStatement):
        incomes = [source]
        stmts = [None]
    elif isinstance(source, FinancialStatements):
        incomes = [source.income_statement]
        stmts = [source]
        meta["period_end"] = source.period.period_end.isoformat()
    elif isinstance(source, FinancialSnapshot):
        meta["company"] = source.company.company
        meta["ticker"] = source.company.ticker
        ordered = sorted(
            source.statements, key=lambda s: s.period.period_end
        )
        if not ordered:
            _reject("Empty financial snapshot: no statements to analyze")
        incomes = [s.income_statement for s in ordered]
        stmts = list(ordered)
        meta["period_end"] = ordered[-1].period.period_end.isoformat()
    elif isinstance(source, (list, tuple)):
        if not source:
            _reject("Empty history sequence")
        for item in source:
            if isinstance(item, IncomeStatement):
                incomes.append(item)
                stmts.append(None)
            elif isinstance(item, FinancialStatements):
                incomes.append(item.income_statement)
                stmts.append(item)
            else:
                _reject(
                    "History items must be IncomeStatement or FinancialStatements"
                )
        # Sort when period metadata available
        if all(s is not None for s in stmts):
            paired = sorted(
                zip(incomes, stmts, strict=True),
                key=lambda p: p[1].period.period_end,  # type: ignore[union-attr]
            )
            incomes = [p[0] for p in paired]
            stmts = [p[1] for p in paired]
            meta["period_end"] = stmts[-1].period.period_end.isoformat()  # type: ignore[union-attr]
    else:
        _reject(
            "Accept ONLY IncomeStatement or Normalized Financial Payload"
        )

    return incomes, stmts, meta
