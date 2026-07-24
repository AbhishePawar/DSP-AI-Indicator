"""Input validation for Graham Intrinsic Value heuristics."""

from __future__ import annotations

import math

from valuation.core.result_models import ValidationSummary
from valuation.core.validation_engine import ValidationEngine
from valuation.exceptions import ValuationError
from valuation.graham.graham_models import GrahamInputs

__all__ = ["validate_graham_inputs"]


def _finite(value: float, name: str, errors: list[str]) -> None:
    if math.isnan(value):
        errors.append(f"{name} is NaN")
    if math.isinf(value):
        errors.append(f"{name} is infinite")


def validate_graham_inputs(inputs: GrahamInputs) -> ValidationSummary:
    """Validate Graham inputs; raise ValuationError on hard failures."""
    errors: list[str] = []
    checks: list[str] = []
    warnings: list[str] = []

    fields: list[tuple[str, float]] = [
        ("eps_trailing", inputs.eps_trailing),
        ("growth_rate", inputs.growth_rate),
        ("aaa_bond_yield", inputs.aaa_bond_yield),
        ("shares_outstanding", inputs.shares_outstanding),
        ("reference_aaa_yield", inputs.reference_aaa_yield),
        ("cash", inputs.cash),
        ("debt", inputs.debt),
        ("bear_growth_delta", inputs.bear_growth_delta),
        ("bull_growth_delta", inputs.bull_growth_delta),
        ("bear_yield_delta", inputs.bear_yield_delta),
        ("bull_yield_delta", inputs.bull_yield_delta),
    ]
    optionals: list[tuple[str, float | None]] = [
        ("normalized_eps", inputs.normalized_eps),
        ("book_value_per_share", inputs.book_value_per_share),
        ("required_return", inputs.required_return),
        ("current_market_price", inputs.current_market_price),
        ("average_eps_3y", inputs.average_eps_3y),
        ("average_eps_5y", inputs.average_eps_5y),
        ("average_eps_10y", inputs.average_eps_10y),
        ("normalized_roe", inputs.normalized_roe),
        ("accounting_quality_score", inputs.accounting_quality_score),
    ]
    for name, value in fields:
        _finite(value, name, errors)
    for name, value in optionals:
        if value is not None:
            _finite(value, name, errors)

    shared = ValidationEngine().summarize(
        {
            "shares_outstanding": inputs.shares_outstanding,
            "debt": inputs.debt,
            "cash": inputs.cash,
            "discount_rate": (
                inputs.required_return
                if inputs.required_return is not None and inputs.required_return > 0
                else None
            ),
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

    eps = (
        inputs.normalized_eps
        if inputs.normalized_eps is not None
        else inputs.eps_trailing
    )
    if eps < 0 and not inputs.allow_negative_eps:
        errors.append(
            f"negative EPS unsupported (got {eps}); set allow_negative_eps=True "
            "for research edge cases"
        )
    elif eps == 0:
        warnings.append("EPS is zero — intrinsic value will be zero")
    else:
        checks.append("EPS accepted")

    # Growth bounds: percent form typically 0–20 in Graham; decimal 0–0.20
    g = inputs.growth_rate
    if inputs.growth_as_decimal:
        if g < -0.5 or g > 0.5:
            errors.append(f"impossible growth_rate (decimal): {g}")
        else:
            checks.append("growth_rate decimal in [-0.5, 0.5]")
        if g > 0.15:
            warnings.append(f"high growth assumption (decimal): {g}")
    else:
        if g < -50 or g > 50:
            errors.append(f"impossible growth_rate (percent form): {g}")
        else:
            checks.append("growth_rate percent in [-50, 50]")
        if g > 15:
            warnings.append(f"high growth assumption (percent): {g}")

    if inputs.aaa_bond_yield <= 0:
        errors.append(
            f"aaa_bond_yield must be > 0, got {inputs.aaa_bond_yield}"
        )
    else:
        checks.append("aaa_bond_yield > 0")

    if inputs.reference_aaa_yield <= 0:
        errors.append(
            f"reference_aaa_yield must be > 0, got {inputs.reference_aaa_yield}"
        )
    else:
        checks.append("reference_aaa_yield > 0")

    if inputs.required_return is not None:
        if inputs.required_return <= 0:
            errors.append(
                f"required_return must be > 0 when set, got {inputs.required_return}"
            )
        else:
            checks.append("required_return > 0")

    if inputs.cash < 0 or inputs.debt < 0:
        errors.append("cash and debt must be non-negative")

    if inputs.current_market_price is not None and inputs.current_market_price < 0:
        errors.append(
            f"current_market_price must be non-negative, "
            f"got {inputs.current_market_price}"
        )

    if inputs.book_value_per_share is not None and inputs.book_value_per_share < 0:
        warnings.append(
            f"negative book_value_per_share: {inputs.book_value_per_share}"
        )

    errors = list(dict.fromkeys(errors))
    checks = list(dict.fromkeys(checks))
    warnings = list(dict.fromkeys(warnings))

    if errors:
        raise ValuationError("Graham validation failed: " + "; ".join(errors))

    return ValidationSummary(
        ok=True,
        checks=tuple(checks),
        errors=(),
        warnings=tuple(warnings),
    )
