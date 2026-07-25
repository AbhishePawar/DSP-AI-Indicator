"""Validation for the canonical Business Quality Engine (F3.6)."""

from __future__ import annotations

import math
from typing import Any

from business_quality.business_quality_models import BusinessQualityWeights
from business_quality.exceptions import BusinessQualityValidationError
from business_quality.validation import (
    BusinessQualityValidation,
    validate_required_inputs,
)

__all__ = [
    "BusinessQualityEngineValidationError",
    "validate_business_quality_input",
    "validate_module_outputs",
    "validate_weights",
]

BusinessQualityEngineValidationError = BusinessQualityValidationError


def validate_business_quality_input(source: Any) -> BusinessQualityValidation:
    """Validate that input is a usable ``FinancialAnalysis``."""
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

    evidence_payload = {
        "revenue": getattr(
            getattr(getattr(source, "income", None), "revenue", None), "revenue", None
        ),
        "operating_cash_flow": getattr(
            getattr(getattr(source, "cash_flow", None), "operating", None),
            "operating_cash_flow",
            None,
        ),
    }
    result = validate_required_inputs(
        evidence_payload,
        ("revenue", "operating_cash_flow"),
        raise_on_missing=False,
    )
    if not result.ok:
        raise BusinessQualityValidationError(
            "Missing required Business Quality evidence: "
            + (", ".join(result.missing_inputs) or "unknown")
        )

    warnings: list[str] = []
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


def validate_weights(weights: BusinessQualityWeights | None) -> BusinessQualityWeights:
    """Validate and return usable weights; reject invalid configurations."""
    if weights is None:
        return BusinessQualityWeights()

    values = weights.as_dict()
    for name, value in values.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise BusinessQualityValidationError(
                f"Invalid weighting configuration: {name} must be numeric"
            )
        if not math.isfinite(float(value)):
            raise BusinessQualityValidationError(
                f"Invalid weighting configuration: {name} must be finite"
            )
        if float(value) < 0:
            raise BusinessQualityValidationError(
                f"Invalid weighting configuration: {name} must be >= 0"
            )

    total = sum(float(v) for v in values.values())
    if total <= 0:
        raise BusinessQualityValidationError(
            "Invalid weighting configuration: weights must sum to a positive total"
        )
    return weights


def validate_module_outputs(
    *,
    earnings_quality: Any,
    capital_allocation: Any,
    business_characteristics: Any,
    competitive_position: Any,
) -> BusinessQualityValidation:
    """Reject missing module outputs after orchestration."""
    modules = {
        "earnings_quality": earnings_quality,
        "capital_allocation": capital_allocation,
        "business_characteristics": business_characteristics,
        "competitive_position": competitive_position,
    }
    missing = [name for name, value in modules.items() if value is None]
    if missing:
        raise BusinessQualityValidationError(
            "Missing module outputs: " + ", ".join(missing)
        )

    for name, value in modules.items():
        if not hasattr(value, "overall_score") or not hasattr(value, "validation"):
            raise BusinessQualityValidationError(
                f"Missing module outputs: {name} is incomplete"
            )

    return BusinessQualityValidation(
        ok=True,
        required_inputs=tuple(modules.keys()),
        missing_inputs=(),
        invalid_inputs=(),
        checks=tuple(f"{name}_present=True" for name in modules),
        warnings=(),
        errors=(),
    )
