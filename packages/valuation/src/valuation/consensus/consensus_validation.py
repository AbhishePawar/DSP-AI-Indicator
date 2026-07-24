"""Input validation for Cross-Method Consensus."""

from __future__ import annotations

import math

from valuation.consensus.consensus_models import (
    ConsensusInputs,
    ConsensusValidationError,
    WeightingMode,
    normalize_method_input,
)
from valuation.core.result_models import ValidationSummary

__all__ = ["validate_consensus_inputs"]


def _finite(value: float, name: str, errors: list[str]) -> None:
    if math.isnan(value):
        errors.append(f"{name} is NaN")
    if math.isinf(value):
        errors.append(f"{name} is infinite")


def validate_consensus_inputs(inputs: ConsensusInputs) -> ValidationSummary:
    """Validate consensus inputs; raise ConsensusValidationError on hard failures."""
    errors: list[str] = []
    checks: list[str] = []
    warnings: list[str] = []

    if not inputs.methods:
        errors.append("empty method list")
    else:
        checks.append(f"method count={len(inputs.methods)}")

    _finite(inputs.trim_fraction, "trim_fraction", errors)
    if inputs.trim_fraction < 0 or inputs.trim_fraction >= 0.5:
        errors.append(
            f"trim_fraction must be in [0, 0.5), got {inputs.trim_fraction}"
        )

    thr = inputs.outlier_thresholds
    for name, val in (
        ("z_score", thr.z_score),
        ("iqr_multiplier", thr.iqr_multiplier),
        ("median_deviation_pct", thr.median_deviation_pct),
        ("extreme_ratio", thr.extreme_ratio),
    ):
        _finite(val, f"outlier_thresholds.{name}", errors)
        if val < 0:
            errors.append(f"outlier_thresholds.{name} must be non-negative")

    if inputs.current_market_price is not None:
        _finite(inputs.current_market_price, "current_market_price", errors)
    if inputs.shares_outstanding is not None:
        _finite(inputs.shares_outstanding, "shares_outstanding", errors)
        if inputs.shares_outstanding <= 0:
            errors.append("shares_outstanding must be positive when provided")

    # Normalize early to catch duplicates / bad confidence / NaN values
    seen: set[str] = set()
    for i, raw in enumerate(inputs.methods):
        try:
            std = normalize_method_input(
                raw, category_overrides=inputs.category_overrides
            )
        except ConsensusValidationError as exc:
            errors.append(str(exc))
            continue
        if std.method in seen:
            errors.append(f"duplicate method: {std.method}")
        seen.add(std.method)

        for label, val in (
            ("intrinsic_value", std.intrinsic_value),
            ("intrinsic_value_per_share", std.intrinsic_value_per_share),
            ("confidence_score", std.confidence_score),
        ):
            if val is None:
                continue
            if math.isnan(val):
                errors.append(f"{std.method}.{label} is NaN")
            if math.isinf(val):
                errors.append(f"{std.method}.{label} is infinite")

    if inputs.weighting_mode is WeightingMode.MANUAL:
        if not inputs.manual_weights:
            errors.append("manual weighting requires manual_weights")
        else:
            for method, w in inputs.manual_weights.items():
                _finite(w, f"manual_weights[{method}]", errors)
                if w < 0:
                    errors.append(f"negative weight for {method}: {w}")
            wsum = sum(float(w) for w in inputs.manual_weights.values())
            if wsum <= 0:
                errors.append("manual weights must sum to a positive total")
            elif abs(wsum - 1.0) > 1e-6 and abs(wsum - 100.0) > 1e-6:
                warnings.append(
                    f"manual weights sum to {wsum}; will be normalized to 100%"
                )
            else:
                checks.append("manual weights present")

    if errors:
        raise ConsensusValidationError(
            "Consensus validation failed: " + "; ".join(dict.fromkeys(errors))
        )

    return ValidationSummary(
        ok=True,
        checks=tuple(dict.fromkeys(checks)),
        errors=(),
        warnings=tuple(dict.fromkeys(warnings)),
    )
