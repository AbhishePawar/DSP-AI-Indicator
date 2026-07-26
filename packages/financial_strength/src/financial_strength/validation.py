"""Input validation for Financial Strength Intelligence."""

from __future__ import annotations

from typing import Any

from business_quality import BusinessQualityAnalysis
from financial import FinancialAnalysis

from financial_strength.metadata import FinancialStrengthMetadata
from financial_strength.models import FinancialStrengthValidationSummary

__all__ = ["validate_framework_inputs", "validate_metadata"]


def validate_metadata(metadata: object | None) -> FinancialStrengthValidationSummary:
    if not isinstance(metadata, FinancialStrengthMetadata):
        return FinancialStrengthValidationSummary(
            ok=False,
            invalid_inputs=("metadata",),
            errors=("Invalid metadata: FinancialStrengthMetadata is required",),
        )
    if not metadata.engine_version or not metadata.framework_version:
        return FinancialStrengthValidationSummary(
            ok=False,
            invalid_inputs=("metadata",),
            errors=("Invalid metadata: contract versions are required",),
        )
    return FinancialStrengthValidationSummary(ok=True, checks=("metadata_valid=True",))


def validate_framework_inputs(
    financial_analysis: object | None,
    business_quality_analysis: object | None,
    metadata: object | None,
) -> FinancialStrengthValidationSummary:
    required = ("FinancialAnalysis", "BusinessQualityAnalysis")
    missing: list[str] = []
    invalid: list[str] = []
    errors: list[str] = []
    checks: list[str] = []

    _validate_input(
        value=financial_analysis,
        expected_type=FinancialAnalysis,
        label="FinancialAnalysis",
        missing=missing,
        invalid=invalid,
        errors=errors,
        checks=checks,
    )
    _validate_input(
        value=business_quality_analysis,
        expected_type=BusinessQualityAnalysis,
        label="BusinessQualityAnalysis",
        missing=missing,
        invalid=invalid,
        errors=errors,
        checks=checks,
    )

    metadata_validation = validate_metadata(metadata)
    invalid.extend(metadata_validation.invalid_inputs)
    errors.extend(metadata_validation.errors)
    checks.extend(metadata_validation.checks)
    return FinancialStrengthValidationSummary(
        ok=not missing and not invalid,
        required_inputs=required,
        missing_inputs=tuple(missing),
        invalid_inputs=tuple(invalid),
        checks=tuple(checks),
        errors=tuple(errors),
    )


def _validate_input(
    *,
    value: object | None,
    expected_type: type[Any],
    label: str,
    missing: list[str],
    invalid: list[str],
    errors: list[str],
    checks: list[str],
) -> None:
    if value is None:
        missing.append(label)
        errors.append(f"Missing {label}")
    elif not isinstance(value, expected_type):
        invalid.append(label)
        errors.append(f"Accept ONLY {label}, got {type(value).__name__}")
    else:
        checks.append(f"{label}_present=True")
