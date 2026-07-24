"""Input validation for Reverse DCF Intelligence."""

from __future__ import annotations

import math

from valuation.exceptions import ValuationError
from valuation.reverse_dcf.reverse_dcf_models import (
    ReverseDcfInputs,
    ValidationSummary,
)

__all__ = ["validate_reverse_dcf_inputs"]


def _is_bad_number(value: float, name: str, errors: list[str]) -> None:
    if math.isnan(value):
        errors.append(f"{name} is NaN")
    if math.isinf(value):
        errors.append(f"{name} is infinite")


def validate_reverse_dcf_inputs(inputs: ReverseDcfInputs) -> ValidationSummary:
    """Validate reverse-DCF inputs; raise ValuationError on hard failures.

    Returns:
        ValidationSummary when all hard checks pass.

    Raises:
        ValuationError: On rejected / impossible assumptions.
    """
    errors: list[str] = []
    checks: list[str] = []

    numeric_fields = (
        ("current_share_price", inputs.current_share_price),
        ("shares_outstanding", inputs.shares_outstanding),
        ("cash", inputs.cash),
        ("debt", inputs.debt),
        ("minority_interest", inputs.minority_interest),
        ("investments", inputs.investments),
        ("current_revenue", inputs.current_revenue),
        ("current_ebit", inputs.current_ebit),
        ("current_fcff", inputs.current_fcff),
        ("current_operating_margin", inputs.current_operating_margin),
        ("tax_rate", inputs.tax_rate),
        ("reinvestment_rate", inputs.reinvestment_rate),
        ("terminal_growth", inputs.terminal_growth),
        ("wacc", inputs.wacc),
        ("expected_margin_expansion", inputs.expected_margin_expansion),
        ("growth_low", inputs.growth_low),
        ("growth_high", inputs.growth_high),
        ("precision", inputs.precision),
    )
    for name, value in numeric_fields:
        _is_bad_number(value, name, errors)
    if inputs.expected_roic is not None:
        _is_bad_number(inputs.expected_roic, "expected_roic", errors)

    if inputs.wacc <= 0:
        errors.append(f"WACC must be positive, got {inputs.wacc}")
    else:
        checks.append("wacc > 0")

    if inputs.terminal_growth >= inputs.wacc:
        errors.append(
            "terminal_growth must be strictly less than WACC "
            f"({inputs.terminal_growth} >= {inputs.wacc})"
        )
    else:
        checks.append("terminal_growth < wacc")

    if inputs.shares_outstanding <= 0:
        errors.append(
            f"shares_outstanding must be positive, got {inputs.shares_outstanding}"
        )
    else:
        checks.append("shares_outstanding > 0")

    if inputs.current_share_price < 0:
        errors.append("current_share_price must be non-negative")
    else:
        checks.append("share_price >= 0")

    if not (0.0 <= inputs.tax_rate < 1.0):
        errors.append(f"impossible tax_rate: {inputs.tax_rate}")
    else:
        checks.append("tax_rate in [0, 1)")

    for name, value in (
        ("cash", inputs.cash),
        ("debt", inputs.debt),
        ("minority_interest", inputs.minority_interest),
        ("investments", inputs.investments),
    ):
        if value < 0:
            errors.append(f"impossible capital structure field {name}={value}")
    if not any(
        e.startswith("impossible capital structure") for e in errors
    ):
        checks.append("capital structure non-negative")

    if inputs.current_revenue <= 0:
        errors.append("current_revenue must be positive")
    else:
        checks.append("current_revenue > 0")

    if inputs.forecast_years < 1 or inputs.forecast_years > 30:
        errors.append(f"forecast_years out of range: {inputs.forecast_years}")
    else:
        checks.append("forecast_years in [1, 30]")

    if inputs.growth_low >= inputs.growth_high:
        errors.append("growth_low must be < growth_high")
    else:
        checks.append("growth search bounds ordered")

    if inputs.precision <= 0 or inputs.precision > 0.01:
        errors.append(f"precision out of usable range: {inputs.precision}")
    else:
        checks.append("precision target set")

    if inputs.max_iterations < 1 or inputs.max_iterations > 10_000:
        errors.append(f"max_iterations out of range: {inputs.max_iterations}")
    else:
        checks.append("max_iterations sane")

    if inputs.reinvestment_rate < -0.5 or inputs.reinvestment_rate > 1.5:
        errors.append(f"reinvestment_rate out of range: {inputs.reinvestment_rate}")
    else:
        checks.append("reinvestment_rate in range")

    if errors:
        raise ValuationError(
            "Reverse DCF validation failed: " + "; ".join(errors)
        )

    return ValidationSummary(
        ok=True,
        checks=tuple(checks),
        errors=(),
    )
