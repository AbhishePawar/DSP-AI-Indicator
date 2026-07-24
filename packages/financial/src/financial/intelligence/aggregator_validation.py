"""Validation for Financial Statement Aggregator inputs."""

from __future__ import annotations

from typing import Sequence

from financial.exceptions import FinancialAggregationError
from financial.intelligence.trend_models import FinancialStatementsHistory
from financial.models import FinancialStatements
from financial.validation import ValidationResult, validate_statements

__all__ = [
    "FinancialAggregationError",
    "validate_aggregation_inputs",
    "coerce_aggregation_source",
]


def _reject(message: str) -> None:
    raise FinancialAggregationError(message)


def coerce_aggregation_source(
    source: FinancialStatements | FinancialStatementsHistory | Sequence[FinancialStatements],
) -> tuple[list[FinancialStatements], dict]:
    """Normalize aggregator inputs into ordered FinancialStatements list.

    Accepts ONLY ``FinancialStatements``, ``FinancialStatementsHistory``,
    or an ordered sequence of ``FinancialStatements``.
    """
    meta: dict = {"company": "", "ticker": ""}

    if isinstance(source, FinancialStatementsHistory):
        stmts = list(source.statements)
    elif isinstance(source, FinancialStatements):
        stmts = [source]
    elif isinstance(source, (list, tuple)):
        if not source:
            _reject("Missing required statement sets: empty history")
        for item in source:
            if not isinstance(item, FinancialStatements):
                _reject(
                    "Invalid aggregation inputs: history items must be "
                    "FinancialStatements"
                )
        stmts = list(source)
        # Treat bare sequences as history wrappers (ordered snapshots)
        if len(stmts) >= 1:
            # Spec primary types are FinancialStatements | History;
            # sequences of statements are accepted as ordered history.
            pass
    else:
        _reject(
            "Accept ONLY FinancialStatements or FinancialStatementsHistory"
        )

    if not stmts:
        _reject("Missing required statement sets: empty history")

    # Chronological order for multi-period composition
    stmts = sorted(stmts, key=lambda s: s.period.period_end)
    ends = [s.period.period_end for s in stmts]
    if len(set(ends)) != len(ends):
        _reject("Partial incompatible analyses: duplicate reporting period ends")
    meta["period_ends"] = tuple(e.isoformat() for e in ends)
    return stmts, meta


def validate_aggregation_inputs(
    statements: Sequence[FinancialStatements],
) -> ValidationResult:
    """Validate statement triad completeness for aggregation."""
    if not statements:
        _reject("Missing required statement sets: empty history")

    checks: list[str] = [f"period_count={len(statements)}"]
    warnings: list[str] = []

    for i, stmt in enumerate(statements):
        inc = stmt.income_statement
        bal = stmt.balance_sheet
        cf = stmt.cash_flow
        # Required: all three statement objects present (always on model),
        # but key fields must exist for a meaningful aggregate.
        if inc.revenue is None and inc.net_income is None:
            _reject(
                f"Missing required statement sets: [{i}] income lacks "
                "revenue and net_income"
            )
        if bal.total_assets is None and bal.total_equity is None:
            _reject(
                f"Missing required statement sets: [{i}] balance sheet lacks "
                "total_assets and total_equity"
            )
        if (
            cf.operating_cash_flow is None
            and cf.free_cash_flow is None
            and cf.capex is None
        ):
            _reject(
                f"Missing required statement sets: [{i}] cash flow lacks "
                "operating_cash_flow, free_cash_flow, and capex"
            )
        try:
            result = validate_statements(stmt)
        except Exception as exc:  # domain validation hard-fail
            raise FinancialAggregationError(
                f"Partial incompatible analyses: {exc}"
            ) from exc
        checks.extend(result.checks)
        warnings.extend(result.warnings)

    if len(statements) < 2:
        warnings.append(
            "Trend analysis omitted: fewer than 2 reporting periods"
        )

    return ValidationResult(
        ok=True,
        checks=tuple(dict.fromkeys(checks)),
        errors=(),
        warnings=tuple(dict.fromkeys(warnings)),
    )
