"""Validation for canonical financial statements."""

from __future__ import annotations

import math
from dataclasses import dataclass
from financial.exceptions import FinancialValidationError
from financial.models import FinancialSnapshot, FinancialStatements
from financial.period import PeriodType

__all__ = ["ValidationResult", "validate_statements", "validate_snapshot"]


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Soft validation summary (hard failures raise instead)."""

    ok: bool
    checks: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "checks": list(self.checks),
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


def _finite(name: str, value: float | None, errors: list[str]) -> None:
    if value is None:
        return
    if math.isnan(value):
        errors.append(f"{name} is NaN")
    if math.isinf(value):
        errors.append(f"{name} is infinite")


def _check_statement_numbers(
    prefix: str, values: dict[str, float | None], errors: list[str]
) -> None:
    for key, val in values.items():
        _finite(f"{prefix}.{key}", val, errors)


def validate_statements(
    statements: FinancialStatements,
    *,
    accounting_tolerance: float = 1e-6,
    require_revenue: bool = False,
    require_total_assets: bool = False,
) -> ValidationResult:
    """Validate one period's statements; raise on hard failures."""
    errors: list[str] = []
    checks: list[str] = []
    warnings: list[str] = []

    period = statements.period
    checks.append("period_end present")

    if period.fiscal_quarter is not None:
        if period.fiscal_quarter < 1 or period.fiscal_quarter > 4:
            errors.append(
                f"fiscal_quarter must be 1–4, got {period.fiscal_quarter}"
            )
        elif period.period_type is PeriodType.QUARTERLY:
            checks.append("fiscal_quarter in range")

    if period.period_length_days is not None and period.period_length_days <= 0:
        errors.append("period_length_days must be positive")

    _check_statement_numbers(
        "income_statement", statements.income_statement.values(), errors
    )
    _check_statement_numbers(
        "balance_sheet", statements.balance_sheet.values(), errors
    )
    _check_statement_numbers("cash_flow", statements.cash_flow.values(), errors)

    income = statements.income_statement
    if require_revenue and income.revenue is None:
        errors.append("revenue is required")
    elif income.revenue is not None:
        checks.append("revenue present")
        if income.revenue < 0:
            warnings.append("negative revenue")

    if income.weighted_shares is not None and income.weighted_shares < 0:
        errors.append("weighted_shares must be non-negative")

    bs = statements.balance_sheet
    if require_total_assets and bs.total_assets is None:
        errors.append("total_assets is required")
    elif bs.total_assets is not None:
        checks.append("total_assets present")

    # Accounting equation: Assets ≈ Liabilities + Equity
    assets = bs.total_assets
    liabilities = bs.total_liabilities
    equity = bs.total_equity if bs.total_equity is not None else bs.equity
    if assets is not None and liabilities is not None and equity is not None:
        lhs = assets
        rhs = liabilities + equity
        if abs(lhs - rhs) > accounting_tolerance * max(1.0, abs(lhs)):
            errors.append(
                f"accounting equation failed: assets={assets} vs "
                f"liabilities+equity={rhs}"
            )
        else:
            checks.append("accounting equation holds")
    elif assets is not None and (liabilities is None or equity is None):
        warnings.append(
            "incomplete balance sheet for accounting-equation check"
        )

    # Soft negative checks on typically non-negative stock items
    for label, val in (
        ("cash", bs.cash),
        ("inventory", bs.inventory),
        ("goodwill", bs.goodwill),
        ("total_assets", bs.total_assets),
    ):
        if val is not None and val < 0:
            warnings.append(f"negative {label}")

    if errors:
        raise FinancialValidationError(
            "Financial validation failed: " + "; ".join(dict.fromkeys(errors))
        )

    return ValidationResult(
        ok=True,
        checks=tuple(dict.fromkeys(checks)),
        errors=(),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def validate_snapshot(
    snapshot: FinancialSnapshot,
    *,
    accounting_tolerance: float = 1e-6,
    require_revenue: bool = False,
    require_total_assets: bool = False,
) -> ValidationResult:
    """Validate a multi-period snapshot; reject duplicate periods."""
    errors: list[str] = []
    checks: list[str] = []
    warnings: list[str] = []

    if not snapshot.statements:
        warnings.append("empty statements list")
    else:
        checks.append(f"statement_count={len(snapshot.statements)}")

    seen: set[tuple] = set()
    for i, stmt in enumerate(snapshot.statements):
        key = stmt.period.key()
        if key in seen:
            errors.append(
                f"duplicate period at index {i}: {stmt.period.period_type.value} "
                f"ending {stmt.period.period_end.isoformat()}"
            )
        seen.add(key)
        try:
            result = validate_statements(
                stmt,
                accounting_tolerance=accounting_tolerance,
                require_revenue=require_revenue,
                require_total_assets=require_total_assets,
            )
            checks.extend(result.checks)
            warnings.extend(result.warnings)
        except FinancialValidationError as exc:
            errors.append(str(exc))

    currency_codes = {
        s.period.currency.code for s in snapshot.statements
    }
    if len(currency_codes) > 1:
        warnings.append(
            "mixed period currencies: "
            + ", ".join(sorted(c.value for c in currency_codes))
        )

    if errors:
        raise FinancialValidationError(
            "Financial validation failed: " + "; ".join(dict.fromkeys(errors))
        )

    return ValidationResult(
        ok=True,
        checks=tuple(dict.fromkeys(checks)),
        errors=(),
        warnings=tuple(dict.fromkeys(warnings)),
    )
