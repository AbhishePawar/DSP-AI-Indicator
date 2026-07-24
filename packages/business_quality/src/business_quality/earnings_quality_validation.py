"""Validation for Earnings Quality Intelligence inputs."""

from __future__ import annotations

from typing import Any

from business_quality.exceptions import BusinessQualityValidationError
from business_quality.validation import (
    BusinessQualityValidation,
    validate_required_inputs,
)

__all__ = [
    "validate_earnings_quality_input",
    "EarningsQualityValidationError",
]

# Alias for sprint naming; same hierarchy as framework validation errors.
EarningsQualityValidationError = BusinessQualityValidationError


def validate_earnings_quality_input(source: Any) -> BusinessQualityValidation:
    """Validate that input is a usable ``FinancialAnalysis``.

    Accepts ONLY FinancialAnalysis. Rejects missing / incomplete evidence.
    Does not recompute financial metrics.
    """
    if source is None:
        raise BusinessQualityValidationError("Missing FinancialAnalysis")

    type_name = type(source).__name__
    if type_name != "FinancialAnalysis":
        raise BusinessQualityValidationError(
            f"Accept ONLY FinancialAnalysis, got {type_name}"
        )

    required_attrs = (
        "income",
        "cash_flow",
        "ratios",
        "validation",
        "metadata",
    )
    missing_attrs = [a for a in required_attrs if not hasattr(source, a)]
    if missing_attrs:
        raise BusinessQualityValidationError(
            "Missing FinancialAnalysis: object lacks "
            + ", ".join(missing_attrs)
        )

    income = source.income
    cash = source.cash_flow
    # Evidence completeness from already-computed intelligence fields
    evidence_payload = {
        "revenue": getattr(getattr(income, "revenue", None), "revenue", None),
        "net_income_quality": getattr(
            getattr(income, "profitability", None), "net_income_quality", None
        ),
        "operating_cash_flow": getattr(
            getattr(cash, "operating", None), "operating_cash_flow", None
        ),
        "cash_conversion": getattr(
            getattr(cash, "operating", None), "cash_conversion", None
        ),
    }
    # Soft structural check first
    result = validate_required_inputs(
        evidence_payload,
        ("revenue", "operating_cash_flow"),
        raise_on_missing=False,
    )
    if not result.ok:
        raise BusinessQualityValidationError(
            "Incomplete required financial evidence: "
            + (", ".join(result.missing_inputs) or "unknown")
        )

    warnings: list[str] = []
    if evidence_payload["net_income_quality"] is None:
        warnings.append("net_income_quality unavailable")
    if evidence_payload["cash_conversion"] is None:
        warnings.append("cash_conversion unavailable")

    fa_validation = getattr(source, "validation", None)
    checks = list(result.checks)
    if fa_validation is not None and hasattr(fa_validation, "ok"):
        checks.append(f"financial_analysis_ok={bool(fa_validation.ok)}")
        if not fa_validation.ok:
            warnings.append("underlying FinancialAnalysis validation not ok")

    return BusinessQualityValidation(
        ok=True,
        required_inputs=result.required_inputs,
        missing_inputs=(),
        invalid_inputs=(),
        checks=tuple(checks),
        warnings=tuple(dict.fromkeys(warnings)),
        errors=(),
    )
