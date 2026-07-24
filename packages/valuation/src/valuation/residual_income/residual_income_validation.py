"""Input validation for Residual Income Valuation.

Rejects impossible assumptions with :class:`~valuation.exceptions.ValuationError`.
"""

from __future__ import annotations

import math

from valuation.exceptions import ValuationError
from valuation.residual_income.residual_income_models import (
    ResidualIncomeInputs,
    RiValidationSummary,
    RoeForecastModel,
)

__all__ = ["validate_residual_income_inputs"]


def _bad_number(value: float, name: str, errors: list[str]) -> None:
    if math.isnan(value):
        errors.append(f"{name} is NaN")
    if math.isinf(value):
        errors.append(f"{name} is infinite")


def validate_residual_income_inputs(
    inputs: ResidualIncomeInputs,
) -> RiValidationSummary:
    """Validate RIV inputs; raise ValuationError on hard failures.

    Returns:
        RiValidationSummary when hard checks pass (may include warnings).
    """
    errors: list[str] = []
    checks: list[str] = []
    warnings: list[str] = []

    fields: list[tuple[str, float]] = [
        ("current_book_value", inputs.current_book_value),
        ("roe_forecast", inputs.roe_forecast),
        ("cost_of_equity", inputs.cost_of_equity),
        ("dividend_payout_ratio", inputs.dividend_payout_ratio),
        ("terminal_growth", inputs.terminal_growth),
        ("shares_outstanding", inputs.shares_outstanding),
        ("bear_roe_delta", inputs.bear_roe_delta),
        ("bull_roe_delta", inputs.bull_roe_delta),
        ("mean_reversion_kappa", inputs.mean_reversion_kappa),
    ]
    if inputs.net_income_forecast is not None:
        fields.append(("net_income_forecast", inputs.net_income_forecast))
    if inputs.retention_ratio is not None:
        fields.append(("retention_ratio", inputs.retention_ratio))
    if inputs.terminal_roe is not None:
        fields.append(("terminal_roe", inputs.terminal_roe))
    if inputs.current_market_price is not None:
        fields.append(("current_market_price", inputs.current_market_price))
    if inputs.roe_long_run is not None:
        fields.append(("roe_long_run", inputs.roe_long_run))
    if inputs.accounting_quality_score is not None:
        fields.append(("accounting_quality_score", inputs.accounting_quality_score))
    for i, v in enumerate(inputs.historical_roe_series):
        fields.append((f"historical_roe[{i}]", v))
    if inputs.roe_manual_series is not None:
        for i, v in enumerate(inputs.roe_manual_series):
            fields.append((f"roe_manual_series[{i}]", v))

    for name, value in fields:
        _bad_number(value, name, errors)

    if inputs.current_book_value <= 0:
        errors.append(
            f"book value must be positive, got {inputs.current_book_value}"
        )
    else:
        checks.append("book_value > 0")

    if inputs.roe_forecast < -0.5 or inputs.roe_forecast > 1.0:
        errors.append(f"ROE outside reasonable bounds: {inputs.roe_forecast}")
    else:
        checks.append("roe in [-0.5, 1.0]")

    if inputs.cost_of_equity <= 0:
        errors.append(
            f"cost_of_equity must be > 0, got {inputs.cost_of_equity}"
        )
    else:
        checks.append("cost_of_equity > 0")

    if inputs.terminal_growth >= inputs.cost_of_equity:
        errors.append(
            "terminal_growth must be strictly less than cost_of_equity "
            f"({inputs.terminal_growth} >= {inputs.cost_of_equity})"
        )
    else:
        checks.append("terminal_growth < cost_of_equity")

    if inputs.shares_outstanding <= 0:
        errors.append(
            f"shares_outstanding must be positive, got {inputs.shares_outstanding}"
        )
    else:
        checks.append("shares_outstanding > 0")

    if not (0.0 <= inputs.dividend_payout_ratio <= 1.0):
        errors.append(
            f"dividend_payout_ratio out of range: {inputs.dividend_payout_ratio}"
        )
    else:
        checks.append("payout in [0, 1]")

    if inputs.retention_ratio is not None and not (
        0.0 <= inputs.retention_ratio <= 1.0
    ):
        errors.append(
            f"retention_ratio out of range: {inputs.retention_ratio}"
        )
    else:
        checks.append("retention valid or defaulted")

    if inputs.forecast_years < 1 or inputs.forecast_years > 30:
        errors.append(f"forecast_years out of range: {inputs.forecast_years}")
    else:
        checks.append("forecast_years in [1, 30]")

    if inputs.terminal_roe is not None and (
        inputs.terminal_roe < -0.5 or inputs.terminal_roe > 1.0
    ):
        errors.append(f"terminal_roe out of bounds: {inputs.terminal_roe}")
    else:
        checks.append("terminal_roe ok")

    if inputs.current_market_price is not None and inputs.current_market_price < 0:
        errors.append("current_market_price must be non-negative")
    else:
        checks.append("market_price ok")

    if not (0.0 < inputs.mean_reversion_kappa <= 1.0):
        errors.append(
            f"mean_reversion_kappa out of range: {inputs.mean_reversion_kappa}"
        )
    else:
        checks.append("mean_reversion_kappa in (0, 1]")

    if inputs.accounting_quality_score is not None and not (
        0.0 <= inputs.accounting_quality_score <= 100.0
    ):
        errors.append(
            "accounting_quality_score must be in [0, 100], "
            f"got {inputs.accounting_quality_score}"
        )
    else:
        checks.append("accounting_quality_score ok")

    if inputs.roe_model is RoeForecastModel.LINEAR_FADE and inputs.terminal_roe is None:
        errors.append("LINEAR_FADE requires terminal_roe")
    if inputs.roe_model is RoeForecastModel.MANUAL:
        if inputs.roe_manual_series is None:
            errors.append("MANUAL roe_model requires roe_manual_series")
        elif len(inputs.roe_manual_series) != inputs.forecast_years:
            errors.append(
                "roe_manual_series length must equal forecast_years "
                f"({len(inputs.roe_manual_series)} != {inputs.forecast_years})"
            )
        else:
            checks.append("manual ROE series length ok")
    else:
        checks.append(f"roe_model={inputs.roe_model.value}")

    if (
        inputs.net_income_forecast is not None
        and inputs.current_book_value > 0
        and abs(
            inputs.net_income_forecast / inputs.current_book_value
            - inputs.roe_forecast
        )
        > 0.05
    ):
        warnings.append(
            "Year-1 NI override implies ROE materially different from roe_forecast "
            "(accounting consistency warning)."
        )

    if errors:
        raise ValuationError(
            "Residual Income validation failed: " + "; ".join(errors)
        )

    return RiValidationSummary(
        ok=True,
        checks=tuple(checks),
        errors=(),
        warnings=tuple(warnings),
    )
