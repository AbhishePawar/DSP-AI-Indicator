"""Input validation for Asset-Based Valuation."""

from __future__ import annotations

import math

from valuation.asset_based.asset_models import AssetBasedInputs, HaircutSchedule
from valuation.core.result_models import ValidationSummary
from valuation.core.validation_engine import ValidationEngine
from valuation.exceptions import ValuationError

__all__ = ["validate_asset_based_inputs"]


def _finite(value: float, name: str, errors: list[str]) -> None:
    if math.isnan(value):
        errors.append(f"{name} is NaN")
    if math.isinf(value):
        errors.append(f"{name} is infinite")


def _check_haircuts(schedule: HaircutSchedule, errors: list[str], checks: list[str]) -> None:
    for name, rate in schedule.as_mapping().items():
        _finite(rate, f"haircut.{name}", errors)
        if rate < 0.0 or rate > 1.0:
            errors.append(f"invalid haircut {name}={rate} (must be in [0, 1])")
    if not errors:
        checks.append("haircuts in [0, 1]")


def validate_asset_based_inputs(inputs: AssetBasedInputs) -> ValidationSummary:
    """Validate asset-based inputs; raise ValuationError on hard failures."""
    errors: list[str] = []
    checks: list[str] = []
    warnings: list[str] = []

    asset_fields = (
        ("cash", inputs.cash),
        ("cash_equivalents", inputs.cash_equivalents),
        ("investments", inputs.investments),
        ("receivables", inputs.receivables),
        ("inventory", inputs.inventory),
        ("biological_assets", inputs.biological_assets),
        ("ppe", inputs.ppe),
        ("investment_property", inputs.investment_property),
        ("intangible_assets", inputs.intangible_assets),
        ("goodwill", inputs.goodwill),
        ("deferred_tax_assets", inputs.deferred_tax_assets),
        ("other_assets", inputs.other_assets),
    )
    liability_fields = (
        ("accounts_payable", inputs.accounts_payable),
        ("short_term_debt", inputs.short_term_debt),
        ("long_term_debt", inputs.long_term_debt),
        ("lease_liabilities", inputs.lease_liabilities),
        ("deferred_tax_liabilities", inputs.deferred_tax_liabilities),
        ("other_liabilities", inputs.other_liabilities),
        ("minority_interest", inputs.minority_interest),
        ("preferred_equity", inputs.preferred_equity),
    )
    optional_fields: list[tuple[str, float | None]] = [
        ("total_assets", inputs.total_assets),
        ("current_market_price", inputs.current_market_price),
        ("fv_investments", inputs.fv_investments),
        ("fv_ppe", inputs.fv_ppe),
        ("fv_investment_property", inputs.fv_investment_property),
        ("fv_biological_assets", inputs.fv_biological_assets),
        ("fv_inventory", inputs.fv_inventory),
        ("fv_receivables", inputs.fv_receivables),
        ("independent_appraisal", inputs.independent_appraisal),
        ("replacement_cost", inputs.replacement_cost),
        ("accounting_quality_score", inputs.accounting_quality_score),
    ]
    other = (
        ("shares_outstanding", inputs.shares_outstanding),
        ("hidden_assets", inputs.hidden_assets),
        ("off_balance_sheet_assets", inputs.off_balance_sheet_assets),
        ("off_balance_sheet_liabilities", inputs.off_balance_sheet_liabilities),
        ("private_holdings_adjustment", inputs.private_holdings_adjustment),
        ("real_estate_appreciation", inputs.real_estate_appreciation),
        ("bear_haircut_delta", inputs.bear_haircut_delta),
        ("bull_haircut_delta", inputs.bull_haircut_delta),
        ("bear_property_delta", inputs.bear_property_delta),
        ("bull_property_delta", inputs.bull_property_delta),
    )

    for name, value in (*asset_fields, *liability_fields, *other):
        _finite(value, name, errors)
    for name, value in optional_fields:
        if value is not None:
            _finite(value, name, errors)

    shared = ValidationEngine().summarize(
        {
            "shares_outstanding": inputs.shares_outstanding,
            "cash": inputs.cash,
            "debt": inputs.short_term_debt + inputs.long_term_debt,
        }
    )
    errors.extend(shared.errors)
    checks.extend(shared.checks)
    warnings.extend(shared.warnings)

    if inputs.shares_outstanding <= 0:
        errors.append(
            f"shares_outstanding must be positive, got {inputs.shares_outstanding}"
        )
    else:
        checks.append("shares > 0")

    for name, value in asset_fields:
        if value < 0:
            errors.append(f"negative asset {name}={value}")
    for name, value in liability_fields:
        if value < 0:
            errors.append(f"negative liability {name}={value}")

    if inputs.hidden_assets < 0 or inputs.off_balance_sheet_assets < 0:
        errors.append("hidden / off-balance-sheet assets must be non-negative")
    if inputs.off_balance_sheet_liabilities < 0:
        errors.append("off_balance_sheet_liabilities must be non-negative")

    summed_assets = sum(v for _, v in asset_fields)
    if inputs.total_assets is not None:
        if inputs.total_assets < 0:
            errors.append(f"total_assets must be non-negative, got {inputs.total_assets}")
        elif abs(inputs.total_assets - summed_assets) > 1e-6 * max(1.0, summed_assets):
            warnings.append(
                f"total_assets ({inputs.total_assets}) differs from sum of "
                f"components ({summed_assets})"
            )
        else:
            checks.append("total_assets matches components")
    else:
        checks.append("total_assets derived from components")

    total_liab = sum(v for _, v in liability_fields)
    book_equity = summed_assets - (
        inputs.accounts_payable
        + inputs.short_term_debt
        + inputs.long_term_debt
        + inputs.lease_liabilities
        + inputs.deferred_tax_liabilities
        + inputs.other_liabilities
    )
    # Book equity before MI/preferred for solvency check of common claim
    if book_equity < 0 and not inputs.allow_negative_equity:
        errors.append(
            f"negative equity unsupported ({book_equity}); "
            "set allow_negative_equity=True for research edge cases"
        )
    elif book_equity < 0:
        warnings.append(f"negative book equity: {book_equity}")
    else:
        checks.append("book equity >= 0")

    if total_liab > summed_assets * 2 and summed_assets > 0:
        warnings.append("liabilities unusually large vs assets")

    if inputs.current_market_price is not None and inputs.current_market_price < 0:
        errors.append(
            f"current_market_price must be non-negative, "
            f"got {inputs.current_market_price}"
        )

    _check_haircuts(inputs.haircut_schedule, errors, checks)

    if inputs.replacement_cost is not None and inputs.replacement_cost < 0:
        errors.append(
            f"replacement_cost must be non-negative, got {inputs.replacement_cost}"
        )

    errors = list(dict.fromkeys(errors))
    checks = list(dict.fromkeys(checks))
    warnings = list(dict.fromkeys(warnings))

    if errors:
        raise ValuationError(
            "Asset-based validation failed: " + "; ".join(errors)
        )

    return ValidationSummary(
        ok=True,
        checks=tuple(checks),
        errors=(),
        warnings=tuple(warnings),
    )
