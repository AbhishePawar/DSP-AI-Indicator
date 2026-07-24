"""Validation for Capital Allocation Intelligence inputs."""

from __future__ import annotations

from typing import Any

from business_quality.exceptions import BusinessQualityValidationError
from business_quality.validation import (
    BusinessQualityValidation,
    validate_required_inputs,
)

__all__ = [
    "validate_capital_allocation_input",
    "CapitalAllocationValidationError",
]

CapitalAllocationValidationError = BusinessQualityValidationError


def validate_capital_allocation_input(source: Any) -> BusinessQualityValidation:
    """Validate that input is a usable ``FinancialAnalysis``.

    Accepts ONLY FinancialAnalysis. Rejects missing capital-allocation evidence.
    """
    if source is None:
        raise BusinessQualityValidationError("Missing FinancialAnalysis")

    type_name = type(source).__name__
    if type_name != "FinancialAnalysis":
        raise BusinessQualityValidationError(
            f"Accept ONLY FinancialAnalysis, got {type_name}"
        )

    required_attrs = (
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

    cash = source.cash_flow
    ratios = source.ratios
    evidence_payload = {
        "operating_cash_flow": getattr(
            getattr(cash, "operating", None), "operating_cash_flow", None
        ),
        "capital_allocation_score": getattr(
            getattr(ratios, "capital_allocation", None),
            "capital_allocation_score",
            None,
        ),
        "capex_discipline": getattr(
            getattr(ratios, "capital_allocation", None), "capex_discipline", None
        ),
        "investment_discipline": getattr(
            getattr(cash, "investing", None), "investment_discipline", None
        ),
    }
    result = validate_required_inputs(
        evidence_payload,
        ("operating_cash_flow",),
        raise_on_missing=False,
    )
    if not result.ok:
        raise BusinessQualityValidationError(
            "Missing required capital allocation evidence: "
            + (", ".join(result.missing_inputs) or "unknown")
        )

    warnings: list[str] = []
    if evidence_payload["capital_allocation_score"] is None:
        warnings.append("capital_allocation_score unavailable")
    if evidence_payload["capex_discipline"] is None:
        warnings.append("capex_discipline unavailable")
    if evidence_payload["investment_discipline"] is None:
        warnings.append("investment_discipline unavailable")

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
