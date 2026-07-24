"""Input validation for Earnings Power Value.

Uses shared :class:`~valuation.core.validation_engine.ValidationEngine`
plus EPV-specific rules. Hard failures raise package :class:`ValuationError`.
"""

from __future__ import annotations

import math

from valuation.core.result_models import ValidationSummary
from valuation.core.validation_engine import ValidationEngine
from valuation.epv.epv_models import EpvInputs, NormalizationMethod
from valuation.exceptions import ValuationError

__all__ = ["validate_epv_inputs"]


def _finite(value: float, name: str, errors: list[str]) -> None:
    if math.isnan(value):
        errors.append(f"{name} is NaN")
    if math.isinf(value):
        errors.append(f"{name} is infinite")


def validate_epv_inputs(inputs: EpvInputs) -> ValidationSummary:
    """Validate EPV inputs; raise ValuationError on hard failures."""
    errors: list[str] = []
    checks: list[str] = []
    warnings: list[str] = []

    numeric_fields: list[tuple[str, float]] = [
        ("revenue", inputs.revenue),
        ("ebit", inputs.ebit),
        ("tax_rate", inputs.tax_rate),
        ("maintenance_capex", inputs.maintenance_capex),
        ("depreciation", inputs.depreciation),
        ("working_capital_adjustment", inputs.working_capital_adjustment),
        ("cost_of_capital", inputs.cost_of_capital),
        ("cash", inputs.cash),
        ("debt", inputs.debt),
        ("minority_interest", inputs.minority_interest),
        ("investments", inputs.investments),
        ("shares_outstanding", inputs.shares_outstanding),
        ("cycle_adjustment_factor", inputs.cycle_adjustment_factor),
        ("one_time_gains", inputs.one_time_gains),
        ("one_time_losses", inputs.one_time_losses),
        ("asset_sales", inputs.asset_sales),
        ("exceptional_items", inputs.exceptional_items),
        ("accounting_distortions", inputs.accounting_distortions),
        ("bear_earnings_delta", inputs.bear_earnings_delta),
        ("bull_earnings_delta", inputs.bull_earnings_delta),
        ("bear_wacc_delta", inputs.bear_wacc_delta),
        ("bull_wacc_delta", inputs.bull_wacc_delta),
    ]
    if inputs.ebit_margin is not None:
        numeric_fields.append(("ebit_margin", inputs.ebit_margin))
    if inputs.normalized_earnings is not None:
        numeric_fields.append(("normalized_earnings", inputs.normalized_earnings))
    if inputs.current_market_price is not None:
        numeric_fields.append(("current_market_price", inputs.current_market_price))
    if inputs.normalized_operating_margin is not None:
        numeric_fields.append(
            ("normalized_operating_margin", inputs.normalized_operating_margin)
        )
    if inputs.average_ebit is not None:
        numeric_fields.append(("average_ebit", inputs.average_ebit))
    if inputs.average_ebit_margin is not None:
        numeric_fields.append(("average_ebit_margin", inputs.average_ebit_margin))
    if inputs.accounting_quality_score is not None:
        numeric_fields.append(
            ("accounting_quality_score", inputs.accounting_quality_score)
        )
    for i, v in enumerate(inputs.historical_ebit):
        numeric_fields.append((f"historical_ebit[{i}]", v))
    for i, v in enumerate(inputs.historical_ebit_margin):
        numeric_fields.append((f"historical_ebit_margin[{i}]", v))

    for name, value in numeric_fields:
        _finite(value, name, errors)

    # Shared engine checks (shares, tax, debt/cash, discount > 0).
    shared = ValidationEngine().summarize(
        {
            "shares_outstanding": inputs.shares_outstanding,
            "tax_rate": inputs.tax_rate,
            "debt": inputs.debt,
            "cash": inputs.cash,
            "wacc": inputs.cost_of_capital,
            "revenue": inputs.revenue if inputs.revenue > 0 else None,
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

    if inputs.cost_of_capital <= 0:
        errors.append(
            f"cost_of_capital must be > 0, got {inputs.cost_of_capital}"
        )
    else:
        checks.append("cost_of_capital > 0")

    if not (0.0 <= inputs.tax_rate < 1.0):
        errors.append(f"impossible tax_rate: {inputs.tax_rate}")
    else:
        checks.append("tax_rate in [0, 1)")

    if inputs.maintenance_capex < 0:
        errors.append(
            f"maintenance_capex must be non-negative, got {inputs.maintenance_capex}"
        )
    else:
        checks.append("maintenance_capex >= 0")

    if inputs.depreciation < 0:
        errors.append(f"depreciation must be non-negative, got {inputs.depreciation}")
    else:
        checks.append("depreciation >= 0")

    if inputs.debt < 0 or inputs.cash < 0 or inputs.investments < 0:
        errors.append("cash, debt, and investments must be non-negative")
    if inputs.minority_interest < 0:
        errors.append(
            f"minority_interest must be non-negative, got {inputs.minority_interest}"
        )

    if inputs.cycle_adjustment_factor <= 0:
        errors.append(
            f"cycle_adjustment_factor must be > 0, got {inputs.cycle_adjustment_factor}"
        )

    method = inputs.normalization_method
    if method in {
        NormalizationMethod.HISTORICAL_AVERAGE,
        NormalizationMethod.MEDIAN,
        NormalizationMethod.BUSINESS_CYCLE_ADJUSTMENT,
    }:
        if not inputs.historical_ebit and inputs.average_ebit is None:
            if inputs.normalized_operating_margin is None:
                errors.append(
                    f"{method.value} requires historical_ebit, average_ebit, "
                    "or normalized_operating_margin"
                )
            elif inputs.revenue <= 0:
                errors.append(
                    "normalized_operating_margin requires positive revenue"
                )
        else:
            checks.append(f"normalization={method.value} inputs present")

    if inputs.current_market_price is not None and inputs.current_market_price < 0:
        errors.append(
            f"current_market_price must be non-negative, "
            f"got {inputs.current_market_price}"
        )

    # Deduplicate while preserving order
    errors = list(dict.fromkeys(errors))
    checks = list(dict.fromkeys(checks))
    warnings = list(dict.fromkeys(warnings))

    if errors:
        raise ValuationError("EPV validation failed: " + "; ".join(errors))

    return ValidationSummary(
        ok=True,
        checks=tuple(checks),
        errors=(),
        warnings=tuple(warnings),
    )
