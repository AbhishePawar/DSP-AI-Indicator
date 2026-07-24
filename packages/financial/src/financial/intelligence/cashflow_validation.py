"""Validation for Cash Flow Intelligence inputs."""

from __future__ import annotations

import math
from typing import Sequence

from financial.cash_flow import CashFlowStatement
from financial.exceptions import CashFlowAnalysisError, FinancialValidationError
from financial.models import FinancialSnapshot, FinancialStatements
from financial.validation import ValidationResult, validate_statements

__all__ = [
    "CashFlowAnalysisError",
    "validate_cashflow_for_analysis",
    "coerce_cashflow_series",
]


def _reject(message: str) -> None:
    raise CashFlowAnalysisError(message)


def _ensure_finite(name: str, value: float | None) -> None:
    if value is None:
        return
    if math.isnan(value):
        _reject(f"{name} is NaN")
    if math.isinf(value):
        _reject(f"{name} is infinite")


def _computed_fcf(cf: CashFlowStatement) -> float | None:
    """FCF = OCF - |capex| when both present (capex may be signed negative)."""
    if cf.operating_cash_flow is None or cf.capex is None:
        return None
    return cf.operating_cash_flow - abs(cf.capex)


def _check_cashflow_hard(cf: CashFlowStatement) -> list[str]:
    warnings: list[str] = []

    for key, val in cf.values().items():
        _ensure_finite(key, val)

    if cf.operating_cash_flow is None:
        _reject("Missing operating_cash_flow")

    # Impossible: extreme mismatch between reported FCF and OCF - |capex|
    computed = _computed_fcf(cf)
    if (
        cf.free_cash_flow is not None
        and computed is not None
        and abs(cf.free_cash_flow - computed) > max(1.0, abs(computed) * 0.5 + abs(cf.operating_cash_flow) * 0.01)
        and abs(cf.free_cash_flow - computed) > abs(cf.operating_cash_flow)
    ):
        _reject(
            "Invalid FCF calculations: reported free_cash_flow inconsistent "
            f"with OCF - |capex| (reported={cf.free_cash_flow}, computed={computed})"
        )

    # Soft: all-zero statement
    nums = [v for v in cf.values().values() if v is not None]
    if nums and all(v == 0 for v in nums):
        warnings.append("all cash-flow line items are zero")

    return warnings


def validate_cashflow_for_analysis(
    cash_flow: CashFlowStatement,
    *,
    statements: FinancialStatements | None = None,
) -> ValidationResult:
    """Validate cash-flow inputs; raise :class:`CashFlowAnalysisError`."""
    checks: list[str] = []
    warnings: list[str] = list(_check_cashflow_hard(cash_flow))

    if cash_flow.operating_cash_flow is not None:
        checks.append("operating_cash_flow present")

    if statements is not None:
        try:
            result = validate_statements(statements)
            checks.extend(result.checks)
            warnings.extend(result.warnings)
        except FinancialValidationError as exc:
            raise CashFlowAnalysisError(str(exc)) from exc

    return ValidationResult(
        ok=True,
        checks=tuple(dict.fromkeys(checks)),
        errors=(),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def coerce_cashflow_series(
    source: CashFlowStatement
    | FinancialStatements
    | FinancialSnapshot
    | dict
    | Sequence[CashFlowStatement | FinancialStatements],
) -> tuple[
    list[CashFlowStatement],
    list[FinancialStatements | None],
    dict,
]:
    """Normalize engine inputs into chronologically ordered cash-flow series."""
    meta: dict = {}

    if isinstance(source, dict):
        if "statements" in source or "version" in source:
            source = FinancialSnapshot.from_dict(source)
        elif "cash_flow" in source or "period" in source:
            source = FinancialStatements.from_dict(source)
        elif any(
            k in source
            for k in ("operating_cash_flow", "free_cash_flow", "capex")
        ):
            source = CashFlowStatement.from_dict(source)
        else:
            _reject(
                "Unsupported payload: expected CashFlowStatement fields, "
                "FinancialStatements, or FinancialSnapshot"
            )

    flows: list[CashFlowStatement] = []
    stmts: list[FinancialStatements | None] = []

    if isinstance(source, CashFlowStatement):
        flows = [source]
        stmts = [None]
    elif isinstance(source, FinancialStatements):
        flows = [source.cash_flow]
        stmts = [source]
        meta["period_end"] = source.period.period_end.isoformat()
        if source.income_statement.revenue is not None:
            meta["revenue"] = source.income_statement.revenue
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
        flows = [s.cash_flow for s in ordered]
        stmts = list(ordered)
        meta["period_end"] = ordered[-1].period.period_end.isoformat()
        rev = ordered[-1].income_statement.revenue
        if rev is not None:
            meta["revenue"] = rev
    elif isinstance(source, (list, tuple)):
        if not source:
            _reject("Empty history sequence")
        for item in source:
            if isinstance(item, CashFlowStatement):
                flows.append(item)
                stmts.append(None)
            elif isinstance(item, FinancialStatements):
                flows.append(item.cash_flow)
                stmts.append(item)
            else:
                _reject(
                    "History items must be CashFlowStatement or FinancialStatements"
                )
        if all(s is not None for s in stmts):
            paired = sorted(
                zip(flows, stmts, strict=True),
                key=lambda p: p[1].period.period_end,  # type: ignore[union-attr]
            )
            flows = [p[0] for p in paired]
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
            rev = stmts[-1].income_statement.revenue  # type: ignore[union-attr]
            if rev is not None:
                meta["revenue"] = rev
    else:
        _reject("Accept ONLY CashFlowStatement or Normalized Financial Payload")

    return flows, stmts, meta
