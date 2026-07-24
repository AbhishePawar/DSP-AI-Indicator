"""Validation for Balance Sheet Intelligence inputs."""

from __future__ import annotations

import math
from typing import Sequence

from financial.balance_sheet import BalanceSheet
from financial.exceptions import BalanceAnalysisError, FinancialValidationError
from financial.models import FinancialSnapshot, FinancialStatements
from financial.validation import ValidationResult, validate_statements

__all__ = [
    "BalanceAnalysisError",
    "validate_balance_for_analysis",
    "coerce_balance_series",
]


def _reject(message: str) -> None:
    raise BalanceAnalysisError(message)


def _ensure_finite(name: str, value: float | None) -> None:
    if value is None:
        return
    if math.isnan(value):
        _reject(f"{name} is NaN")
    if math.isinf(value):
        _reject(f"{name} is infinite")


def _equity_value(bs: BalanceSheet) -> float | None:
    if bs.total_equity is not None:
        return bs.total_equity
    return bs.equity


def _check_balance_hard(
    bs: BalanceSheet,
    *,
    allow_negative_equity: bool = False,
    accounting_tolerance: float = 1e-6,
) -> list[str]:
    """Return soft warnings; raise BalanceAnalysisError on hard failures."""
    warnings: list[str] = []

    for key, val in bs.values().items():
        _ensure_finite(key, val)

    if bs.total_assets is None:
        _reject("Missing total_assets")
    if bs.total_assets < 0:
        _reject("Negative Total Assets")
    if bs.total_assets == 0:
        _reject("Impossible ratios: total_assets is zero")

    equity = _equity_value(bs)
    if equity is not None and equity < 0 and not allow_negative_equity:
        _reject("Negative Equity")

    liabilities = bs.total_liabilities
    if (
        bs.total_assets is not None
        and liabilities is not None
        and equity is not None
    ):
        rhs = liabilities + equity
        if abs(bs.total_assets - rhs) > accounting_tolerance * max(
            1.0, abs(bs.total_assets)
        ):
            _reject(
                f"Assets ≠ Liabilities + Equity: assets={bs.total_assets} "
                f"vs liabilities+equity={rhs}"
            )

    if bs.current_liabilities is not None and bs.current_liabilities < 0:
        warnings.append("negative current_liabilities")
    if bs.cash is not None and bs.cash < 0:
        warnings.append("negative cash")

    return warnings


def validate_balance_for_analysis(
    balance: BalanceSheet,
    *,
    statements: FinancialStatements | None = None,
    allow_negative_equity: bool = False,
    accounting_tolerance: float = 1e-6,
) -> ValidationResult:
    """Validate balance-sheet inputs; raise :class:`BalanceAnalysisError`."""
    checks: list[str] = []
    warnings: list[str] = list(
        _check_balance_hard(
            balance,
            allow_negative_equity=allow_negative_equity,
            accounting_tolerance=accounting_tolerance,
        )
    )

    if balance.total_assets is not None:
        checks.append("total_assets present")

    if statements is not None:
        try:
            result = validate_statements(
                statements,
                accounting_tolerance=accounting_tolerance,
                require_total_assets=True,
            )
            checks.extend(result.checks)
            warnings.extend(result.warnings)
        except FinancialValidationError as exc:
            raise BalanceAnalysisError(str(exc)) from exc

    return ValidationResult(
        ok=True,
        checks=tuple(dict.fromkeys(checks)),
        errors=(),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def coerce_balance_series(
    source: BalanceSheet
    | FinancialStatements
    | FinancialSnapshot
    | dict
    | Sequence[BalanceSheet | FinancialStatements],
) -> tuple[list[BalanceSheet], list[FinancialStatements | None], dict]:
    """Normalize engine inputs into chronologically ordered balance series."""
    meta: dict = {}

    if isinstance(source, dict):
        if "statements" in source or "version" in source:
            source = FinancialSnapshot.from_dict(source)
        elif "balance_sheet" in source or "period" in source:
            source = FinancialStatements.from_dict(source)
        elif any(
            k in source for k in ("total_assets", "cash", "total_equity", "equity")
        ):
            source = BalanceSheet.from_dict(source)
        else:
            _reject(
                "Unsupported payload: expected BalanceSheet fields, "
                "FinancialStatements, or FinancialSnapshot"
            )

    balances: list[BalanceSheet] = []
    stmts: list[FinancialStatements | None] = []

    if isinstance(source, BalanceSheet):
        balances = [source]
        stmts = [None]
    elif isinstance(source, FinancialStatements):
        balances = [source.balance_sheet]
        stmts = [source]
        meta["period_end"] = source.period.period_end.isoformat()
    elif isinstance(source, FinancialSnapshot):
        meta["company"] = source.company.company
        meta["ticker"] = source.company.ticker
        ordered = sorted(source.statements, key=lambda s: s.period.period_end)
        if not ordered:
            _reject("Empty financial snapshot: no statements to analyze")
        seen: set[tuple] = set()
        for s in ordered:
            key = s.period.key()
            if key in seen:
                _reject(
                    f"Duplicate periods: {s.period.period_type.value} ending "
                    f"{s.period.period_end.isoformat()}"
                )
            seen.add(key)
        balances = [s.balance_sheet for s in ordered]
        stmts = list(ordered)
        meta["period_end"] = ordered[-1].period.period_end.isoformat()
    elif isinstance(source, (list, tuple)):
        if not source:
            _reject("Empty history sequence")
        for item in source:
            if isinstance(item, BalanceSheet):
                balances.append(item)
                stmts.append(None)
            elif isinstance(item, FinancialStatements):
                balances.append(item.balance_sheet)
                stmts.append(item)
            else:
                _reject(
                    "History items must be BalanceSheet or FinancialStatements"
                )
        if all(s is not None for s in stmts):
            paired = sorted(
                zip(balances, stmts, strict=True),
                key=lambda p: p[1].period.period_end,  # type: ignore[union-attr]
            )
            balances = [p[0] for p in paired]
            stmts = [p[1] for p in paired]
            seen_keys: set[tuple] = set()
            for s in stmts:
                assert s is not None
                key = s.period.key()
                if key in seen_keys:
                    _reject(
                        f"Duplicate periods: {s.period.period_type.value} ending "
                        f"{s.period.period_end.isoformat()}"
                    )
                seen_keys.add(key)
            meta["period_end"] = stmts[-1].period.period_end.isoformat()  # type: ignore[union-attr]
    else:
        _reject("Accept ONLY BalanceSheet or Normalized Financial Payload")

    return balances, stmts, meta
