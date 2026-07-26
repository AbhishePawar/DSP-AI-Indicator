"""Input validation for Investment Recommendation."""

from __future__ import annotations

from typing import Any

from business_quality_aggregator import BusinessQualityAggregation
from earnings_quality import EarningsQualityAnalysis
from economic_moat import EconomicAnalysis
from financial_strength import FinancialStrengthAnalysis
from growth_quality import GrowthQualityAnalysis
from management_quality import ManagementAnalysis
from valuation import OverallValuationResult

from investment_recommendation.metadata import InvestmentRecommendationMetadata
from investment_recommendation.models import InvestmentRecommendationValidationSummary
from investment_recommendation.valuation_signals import ValuationSignals

__all__ = ["validate_framework_inputs", "validate_metadata"]


def validate_metadata(
    metadata: object | None,
) -> InvestmentRecommendationValidationSummary:
    if not isinstance(metadata, InvestmentRecommendationMetadata):
        return InvestmentRecommendationValidationSummary(
            ok=False,
            invalid_inputs=("metadata",),
            errors=(
                "Invalid metadata: InvestmentRecommendationMetadata is required",
            ),
        )
    if not metadata.engine_version or not metadata.framework_version:
        return InvestmentRecommendationValidationSummary(
            ok=False,
            invalid_inputs=("metadata",),
            errors=("Invalid metadata: contract versions are required",),
        )
    return InvestmentRecommendationValidationSummary(
        ok=True, checks=("metadata_valid=True",)
    )


def validate_framework_inputs(
    *,
    valuation: object | None,
    business_quality: object | None,
    economic_moat: object | None,
    management_quality: object | None,
    financial_strength: object | None,
    earnings_quality: object | None,
    growth_quality: object | None,
    metadata: object | None,
) -> InvestmentRecommendationValidationSummary:
    required = (
        "OverallValuationResult|ValuationSignals",
        "BusinessQualityAggregation",
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

    if valuation is None:
        missing.append("OverallValuationResult|ValuationSignals")
        errors.append("Missing OverallValuationResult or ValuationSignals")
    elif isinstance(valuation, (OverallValuationResult, ValuationSignals)):
        checks.append("valuation_present=True")
    else:
        invalid.append("OverallValuationResult|ValuationSignals")
        errors.append(
            "Accept ONLY OverallValuationResult or ValuationSignals, "
            f"got {type(valuation).__name__}"
        )

    pairs = (
        (business_quality, BusinessQualityAggregation, "BusinessQualityAggregation"),
        (economic_moat, EconomicAnalysis, "EconomicAnalysis"),
        (management_quality, ManagementAnalysis, "ManagementAnalysis"),
        (financial_strength, FinancialStrengthAnalysis, "FinancialStrengthAnalysis"),
        (earnings_quality, EarningsQualityAnalysis, "EarningsQualityAnalysis"),
        (growth_quality, GrowthQualityAnalysis, "GrowthQualityAnalysis"),
    )
    for value, expected, label in pairs:
        _validate_input(
            value=value,
            expected_type=expected,
            label=label,
            missing=missing,
            invalid=invalid,
            errors=errors,
            checks=checks,
        )

    metadata_validation = validate_metadata(metadata)
    invalid.extend(metadata_validation.invalid_inputs)
    errors.extend(metadata_validation.errors)
    checks.extend(metadata_validation.checks)
    return InvestmentRecommendationValidationSummary(
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
