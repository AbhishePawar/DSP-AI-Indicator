"""Input validation for Dividend Discount Model."""

from __future__ import annotations

import math

from valuation.core.result_models import ValidationSummary
from valuation.core.validation_engine import ValidationEngine
from valuation.ddm.ddm_models import DdmInputs, DdmMethod
from valuation.exceptions import ValuationError

__all__ = ["validate_ddm_inputs"]


def _finite(value: float, name: str, errors: list[str]) -> None:
    if math.isnan(value):
        errors.append(f"{name} is NaN")
    if math.isinf(value):
        errors.append(f"{name} is infinite")


def validate_ddm_inputs(inputs: DdmInputs) -> ValidationSummary:
    """Validate DDM inputs; raise ValuationError on hard failures."""
    errors: list[str] = []
    checks: list[str] = []
    warnings: list[str] = []

    fields: list[tuple[str, float]] = [
        ("current_dps", inputs.current_dps),
        ("cost_of_equity", inputs.cost_of_equity),
        ("expected_dividend_growth", inputs.expected_dividend_growth),
        ("terminal_growth", inputs.terminal_growth),
        ("shares_outstanding", inputs.shares_outstanding),
        ("bear_growth_delta", inputs.bear_growth_delta),
        ("bull_growth_delta", inputs.bull_growth_delta),
        ("bear_coe_delta", inputs.bear_coe_delta),
        ("bull_coe_delta", inputs.bull_coe_delta),
    ]
    optionals: list[tuple[str, float | None]] = [
        ("current_market_price", inputs.current_market_price),
        ("dividend_payout_ratio", inputs.dividend_payout_ratio),
        ("retention_ratio", inputs.retention_ratio),
        ("roe", inputs.roe),
        ("eps", inputs.eps),
        ("book_value", inputs.book_value),
        ("historical_dividend_cagr", inputs.historical_dividend_cagr),
        ("dividend_stability_score", inputs.dividend_stability_score),
        ("dividend_coverage_ratio", inputs.dividend_coverage_ratio),
        ("free_cash_flow_payout_ratio", inputs.free_cash_flow_payout_ratio),
        ("accounting_quality_score", inputs.accounting_quality_score),
    ]
    for name, value in fields:
        _finite(value, name, errors)
    for name, value in optionals:
        if value is not None:
            _finite(value, name, errors)
    for i, g in enumerate(inputs.dividend_growth_schedule):
        _finite(g, f"dividend_growth_schedule[{i}]", errors)

    shared = ValidationEngine().summarize(
        {
            "shares_outstanding": inputs.shares_outstanding,
            "cost_of_equity": inputs.cost_of_equity,
            "growth": inputs.expected_dividend_growth,
            "terminal_growth": (
                inputs.terminal_growth
                if inputs.method
                in {DdmMethod.TWO_STAGE, DdmMethod.MULTI_STAGE, DdmMethod.GORDON}
                else None
            ),
        }
    )
    errors.extend(shared.errors)
    checks.extend(shared.checks)
    warnings.extend(shared.warnings)

    if inputs.current_dps < 0:
        errors.append(f"current_dps must be non-negative, got {inputs.current_dps}")
    elif inputs.current_dps == 0:
        warnings.append("current_dps is zero — intrinsic value will be zero")
    else:
        checks.append("current_dps >= 0")

    if inputs.shares_outstanding <= 0:
        errors.append(
            f"shares_outstanding must be positive, got {inputs.shares_outstanding}"
        )
    else:
        checks.append("shares > 0")

    if inputs.cost_of_equity <= 0:
        errors.append(
            f"cost_of_equity must be > 0, got {inputs.cost_of_equity}"
        )
    else:
        checks.append("cost_of_equity > 0")

    r = inputs.cost_of_equity
    method = inputs.method

    if method is DdmMethod.ZERO_GROWTH:
        checks.append("zero_growth: g=0 assumed")
    elif method is DdmMethod.GORDON:
        g = inputs.expected_dividend_growth
        if g >= r:
            errors.append(
                f"growth must be < cost_of_equity ({g} >= {r})"
            )
        else:
            checks.append("gordon: g < r")
    elif method in {DdmMethod.TWO_STAGE, DdmMethod.MULTI_STAGE}:
        if inputs.forecast_years < 1 or inputs.forecast_years > 50:
            errors.append(
                f"forecast_years out of range: {inputs.forecast_years}"
            )
        else:
            checks.append("forecast_years in [1, 50]")
        tg = inputs.terminal_growth
        if tg >= r:
            errors.append(
                f"terminal_growth must be < cost_of_equity ({tg} >= {r})"
            )
        else:
            checks.append("terminal_growth < r")
        if method is DdmMethod.MULTI_STAGE and inputs.dividend_growth_schedule:
            if len(inputs.dividend_growth_schedule) != inputs.forecast_years:
                errors.append(
                    "dividend_growth_schedule length must equal forecast_years "
                    f"({len(inputs.dividend_growth_schedule)} != "
                    f"{inputs.forecast_years})"
                )
            else:
                checks.append("growth schedule length matches forecast_years")

    if inputs.dividend_payout_ratio is not None:
        p = inputs.dividend_payout_ratio
        if p < 0 or p > 1.5:
            errors.append(f"impossible payout ratio: {p}")
        elif p > 1.0:
            warnings.append(f"payout ratio > 100%: {p}")
        else:
            checks.append("payout in [0, 1]")

    if inputs.retention_ratio is not None:
        ret = inputs.retention_ratio
        if ret < 0 or ret > 1.0:
            errors.append(f"impossible retention_ratio: {ret}")
        else:
            checks.append("retention in [0, 1]")

    if inputs.roe is not None:
        if inputs.roe < -1.0 or inputs.roe > 2.0:
            errors.append(f"invalid ROE: {inputs.roe}")
        else:
            checks.append("roe in [-1, 2]")

    if inputs.current_market_price is not None and inputs.current_market_price < 0:
        errors.append(
            f"current_market_price must be non-negative, "
            f"got {inputs.current_market_price}"
        )

    if inputs.expected_dividend_growth > 0.20:
        warnings.append(
            f"high growth assumption: {inputs.expected_dividend_growth}"
        )
    if inputs.expected_dividend_growth < 0:
        warnings.append(
            f"negative growth assumption: {inputs.expected_dividend_growth}"
        )

    errors = list(dict.fromkeys(errors))
    checks = list(dict.fromkeys(checks))
    warnings = list(dict.fromkeys(warnings))

    if errors:
        raise ValuationError("DDM validation failed: " + "; ".join(errors))

    return ValidationSummary(
        ok=True,
        checks=tuple(checks),
        errors=(),
        warnings=tuple(warnings),
    )
