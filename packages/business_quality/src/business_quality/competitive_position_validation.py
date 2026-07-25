"""Validation for Competitive Position Indicators inputs."""

from __future__ import annotations

from typing import Any

from business_quality.exceptions import BusinessQualityValidationError
from business_quality.validation import (
    BusinessQualityValidation,
    validate_required_inputs,
)

__all__ = [
    "validate_competitive_position_input",
    "CompetitivePositionValidationError",
]

CompetitivePositionValidationError = BusinessQualityValidationError


def validate_competitive_position_input(source: Any) -> BusinessQualityValidation:
    """Validate that input is a usable ``FinancialAnalysis``.

    Accepts ONLY FinancialAnalysis. Rejects missing competitive evidence.
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
    cash = source.cash_flow
    ratios = source.ratios
    evidence_payload = {
        "revenue": getattr(getattr(income, "revenue", None), "revenue", None),
        "gross_margin": getattr(getattr(income, "margins", None), "gross_margin", None),
        "margin_stability": getattr(
            getattr(income, "profitability", None), "margin_stability", None
        ),
        "operating_cash_flow": getattr(
            getattr(cash, "operating", None), "operating_cash_flow", None
        ),
        "roa": _ratio_value(getattr(ratios, "profitability", None), "roa"),
        "roe": _ratio_value(getattr(ratios, "profitability", None), "roe"),
    }
    result = validate_required_inputs(
        evidence_payload,
        ("revenue", "operating_cash_flow"),
        raise_on_missing=False,
    )
    if not result.ok:
        raise BusinessQualityValidationError(
            "Missing required competitive evidence: "
            + (", ".join(result.missing_inputs) or "unknown")
        )

    warnings: list[str] = []
    if evidence_payload["gross_margin"] is None:
        warnings.append("gross_margin unavailable")
    if evidence_payload["margin_stability"] is None:
        warnings.append("margin_stability unavailable")
    if evidence_payload["roa"] is None and evidence_payload["roe"] is None:
        warnings.append("return-on-capital ratios unavailable")

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


def _ratio_value(metrics: Any, name: str) -> float | None:
    if metrics is None:
        return None
    for m in metrics:
        if getattr(m, "name", None) == name:
            return getattr(m, "value", None)
    return None
