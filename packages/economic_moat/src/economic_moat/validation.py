"""Input validation for the Economic Moat Intelligence framework."""

from __future__ import annotations

from typing import Any

from business_quality import BusinessQualityAnalysis
from financial import FinancialAnalysis

from economic_moat.metadata import EconomicMetadata
from economic_moat.models import EconomicValidationSummary

__all__ = ["validate_framework_inputs", "validate_metadata"]


def validate_metadata(metadata: object | None) -> EconomicValidationSummary:
    """Validate framework metadata without interpreting any domain inputs."""
    if not isinstance(metadata, EconomicMetadata):
        return EconomicValidationSummary(
            ok=False,
            invalid_inputs=("metadata",),
            errors=("Invalid metadata: EconomicMetadata is required",),
        )
    if not metadata.engine_version or not metadata.framework_version:
        return EconomicValidationSummary(
            ok=False,
            invalid_inputs=("metadata",),
            errors=("Invalid metadata: contract versions are required",),
        )
    return EconomicValidationSummary(ok=True, checks=("metadata_valid=True",))


def validate_framework_inputs(
    financial_analysis: object | None,
    business_quality_analysis: object | None,
    metadata: object | None,
) -> EconomicValidationSummary:
    """Validate the two permitted upstream inputs and framework metadata."""
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
    return EconomicValidationSummary(
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
    """Record one exact public-input contract check."""
    if value is None:
        missing.append(label)
        errors.append(f"Missing {label}")
    elif not isinstance(value, expected_type):
        invalid.append(label)
        errors.append(f"Accept ONLY {label}, got {type(value).__name__}")
    else:
        checks.append(f"{label}_present=True")
