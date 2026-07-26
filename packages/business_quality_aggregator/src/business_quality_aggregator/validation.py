"""Input validation for Business Quality Aggregator."""

from __future__ import annotations

from typing import Any

from earnings_quality import EarningsQualityAnalysis
from economic_moat import EconomicAnalysis
from financial_strength import FinancialStrengthAnalysis
from growth_quality import GrowthQualityAnalysis
from management_quality import ManagementAnalysis

from business_quality_aggregator.metadata import BusinessQualityAggregatorMetadata
from business_quality_aggregator.models import BusinessQualityAggregatorValidationSummary

__all__ = ["validate_framework_inputs", "validate_metadata"]


def validate_metadata(
    metadata: object | None,
) -> BusinessQualityAggregatorValidationSummary:
    if not isinstance(metadata, BusinessQualityAggregatorMetadata):
        return BusinessQualityAggregatorValidationSummary(
            ok=False,
            invalid_inputs=("metadata",),
            errors=("Invalid metadata: BusinessQualityAggregatorMetadata is required",),
        )
    if not metadata.engine_version or not metadata.framework_version:
        return BusinessQualityAggregatorValidationSummary(
            ok=False,
            invalid_inputs=("metadata",),
            errors=("Invalid metadata: contract versions are required",),
        )
    return BusinessQualityAggregatorValidationSummary(
        ok=True, checks=("metadata_valid=True",)
    )


def validate_framework_inputs(
    *,
    economic_moat: object | None,
    management_quality: object | None,
    financial_strength: object | None,
    earnings_quality: object | None,
    growth_quality: object | None,
    metadata: object | None,
) -> BusinessQualityAggregatorValidationSummary:
    required = (
        "EconomicAnalysis",
        "ManagementAnalysis",
        "FinancialStrengthAnalysis",
        "EarningsQualityAnalysis",
        "GrowthQualityAnalysis",
    )
    missing: list[str] = []
    invalid: list[str] = []
    errors: list[str] = []
    checks: list[str] = []

    _validate_input(
        value=economic_moat,
        expected_type=EconomicAnalysis,
        label="EconomicAnalysis",
        missing=missing,
        invalid=invalid,
        errors=errors,
        checks=checks,
    )
    _validate_input(
        value=management_quality,
        expected_type=ManagementAnalysis,
        label="ManagementAnalysis",
        missing=missing,
        invalid=invalid,
        errors=errors,
        checks=checks,
    )
    _validate_input(
        value=financial_strength,
        expected_type=FinancialStrengthAnalysis,
        label="FinancialStrengthAnalysis",
        missing=missing,
        invalid=invalid,
        errors=errors,
        checks=checks,
    )
    _validate_input(
        value=earnings_quality,
        expected_type=EarningsQualityAnalysis,
        label="EarningsQualityAnalysis",
        missing=missing,
        invalid=invalid,
        errors=errors,
        checks=checks,
    )
    _validate_input(
        value=growth_quality,
        expected_type=GrowthQualityAnalysis,
        label="GrowthQualityAnalysis",
        missing=missing,
        invalid=invalid,
        errors=errors,
        checks=checks,
    )

    metadata_validation = validate_metadata(metadata)
    invalid.extend(metadata_validation.invalid_inputs)
    errors.extend(metadata_validation.errors)
    checks.extend(metadata_validation.checks)
    return BusinessQualityAggregatorValidationSummary(
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
