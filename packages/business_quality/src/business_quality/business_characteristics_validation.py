"""Validation for Business Characteristics Intelligence inputs."""

from __future__ import annotations

from typing import Any

from business_quality.exceptions import BusinessQualityValidationError
from business_quality.validation import (
    BusinessQualityValidation,
    validate_required_inputs,
)

__all__ = [
    "validate_business_characteristics_input",
    "BusinessCharacteristicsValidationError",
]

BusinessCharacteristicsValidationError = BusinessQualityValidationError


def validate_business_characteristics_input(source: Any) -> BusinessQualityValidation:
    """Validate that input is a usable ``FinancialAnalysis``.

    Accepts ONLY FinancialAnalysis. Rejects missing characteristic evidence.
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
        "balance_sheet",
        "cash_flow",
        "ratios",
        "validation",
        "metadata",
        "overall_summary",
    )
    missing_attrs = [a for a in required_attrs if not hasattr(source, a)]
    if missing_attrs:
        raise BusinessQualityValidationError(
            "Missing FinancialAnalysis: object lacks " + ", ".join(missing_attrs)
        )

    income = source.income
    balance = source.balance_sheet
    cash = source.cash_flow
    evidence_payload = {
        "revenue": getattr(getattr(income, "revenue", None), "revenue", None),
        "margin_stability": getattr(
            getattr(income, "profitability", None), "margin_stability", None
        ),
        "balance_sheet_strength": getattr(
            getattr(balance, "working_capital", None),
            "balance_sheet_strength",
            None,
        ),
        "cash_sustainability": getattr(
            getattr(cash, "quality", None), "cash_sustainability", None
        ),
        "operating_cash_flow": getattr(
            getattr(cash, "operating", None), "operating_cash_flow", None
        ),
    }
    result = validate_required_inputs(
        evidence_payload,
        ("revenue", "operating_cash_flow"),
        raise_on_missing=False,
    )
    if not result.ok:
        raise BusinessQualityValidationError(
            "Missing required business characteristic evidence: "
            + (", ".join(result.missing_inputs) or "unknown")
        )

    warnings: list[str] = []
    if evidence_payload["margin_stability"] is None:
        warnings.append("margin_stability unavailable")
    if evidence_payload["balance_sheet_strength"] is None:
        warnings.append("balance_sheet_strength unavailable")
    if evidence_payload["cash_sustainability"] is None:
        warnings.append("cash_sustainability unavailable")

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
