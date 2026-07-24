"""Input validation for Overall Valuation Aggregator."""

from __future__ import annotations

import math
from typing import Any, Mapping

from valuation.consensus.consensus_models import ConsensusResult
from valuation.core.result_models import ValidationSummary, ValuationResult
from valuation.overall.overall_models import OverallInputs, OverallValuationError

__all__ = ["validate_overall_inputs"]


def _finite(value: float, name: str, errors: list[str]) -> None:
    if math.isnan(value):
        errors.append(f"{name} is NaN")
    if math.isinf(value):
        errors.append(f"{name} is infinite")


def validate_overall_inputs(inputs: OverallInputs) -> ValidationSummary:
    """Validate overall inputs; raise OverallValuationError on hard failures."""
    errors: list[str] = []
    checks: list[str] = []
    warnings: list[str] = []

    _finite(inputs.current_market_price, "current_market_price", errors)
    if inputs.current_market_price < 0:
        errors.append(
            f"current_market_price must be non-negative, got {inputs.current_market_price}"
        )
    elif inputs.current_market_price == 0:
        warnings.append("current_market_price is zero — MoS interpretation limited")
    else:
        checks.append("price >= 0")

    if inputs.shares_outstanding is not None:
        _finite(inputs.shares_outstanding, "shares_outstanding", errors)
        if inputs.shares_outstanding <= 0:
            errors.append("shares_outstanding must be positive when provided")

    for name, val in (
        ("wide_range_pct", inputs.wide_range_pct),
        ("narrow_range_pct", inputs.narrow_range_pct),
    ):
        _finite(val, name, errors)
        if val < 0:
            errors.append(f"{name} must be non-negative")

    thr = inputs.mos_thresholds
    for name, val in (
        ("deep_value", thr.deep_value),
        ("undervalued", thr.undervalued),
        ("fairly_band", thr.fairly_band),
        ("overvalued", thr.overvalued),
        ("extremely_overvalued", thr.extremely_overvalued),
    ):
        _finite(val, f"mos_thresholds.{name}", errors)

    consensus = inputs.consensus
    if consensus is None:
        errors.append("missing consensus")
    elif isinstance(consensus, ConsensusResult):
        checks.append("consensus=ConsensusResult")
        if consensus.consensus_intrinsic_value.value is None and (
            consensus.consensus_per_share.value is None
        ):
            errors.append("consensus missing intrinsic values")
    elif isinstance(consensus, ValuationResult):
        if consensus.model_name != "consensus":
            warnings.append(
                f"consensus ValuationResult model_name={consensus.model_name!r} "
                "(expected 'consensus')"
            )
        if (
            consensus.intrinsic_value is None
            and consensus.intrinsic_value_per_share is None
        ):
            errors.append("consensus ValuationResult missing intrinsic values")
        checks.append("consensus=ValuationResult")
    elif isinstance(consensus, Mapping):
        method = str(consensus.get("method") or consensus.get("model_name") or "")
        if method and method != "consensus":
            warnings.append(f"consensus payload method={method!r}")
        iv = consensus.get("intrinsic_value")
        ivps = consensus.get("intrinsic_value_per_share")
        if iv is None and ivps is None:
            errors.append("consensus payload missing intrinsic values")
        for label, val in (("intrinsic_value", iv), ("intrinsic_value_per_share", ivps)):
            if val is None:
                continue
            try:
                _finite(float(val), f"consensus.{label}", errors)
            except (TypeError, ValueError):
                errors.append(f"consensus.{label} is not numeric")
        checks.append("consensus=v2_payload")
    else:
        errors.append(f"unsupported consensus type: {type(consensus)!r}")

    seen: set[str] = set()
    for i, raw in enumerate(inputs.methods):
        if isinstance(raw, ValuationResult):
            name = raw.model_name
            if raw.intrinsic_value_per_share is not None:
                _finite(
                    raw.intrinsic_value_per_share,
                    f"methods[{i}].intrinsic_value_per_share",
                    errors,
                )
            if raw.intrinsic_value is not None:
                _finite(raw.intrinsic_value, f"methods[{i}].intrinsic_value", errors)
        elif isinstance(raw, Mapping):
            name = str(raw.get("method") or raw.get("model_name") or "").strip()
            if not name:
                errors.append(f"methods[{i}] missing method")
                continue
            for label in ("intrinsic_value", "intrinsic_value_per_share"):
                val = raw.get(label)
                if val is None:
                    continue
                try:
                    _finite(float(val), f"methods[{i}].{label}", errors)
                except (TypeError, ValueError):
                    errors.append(f"methods[{i}].{label} is not numeric")
        else:
            errors.append(f"methods[{i}] unsupported type: {type(raw)!r}")
            continue
        if name in seen:
            errors.append(f"duplicate method: {name}")
        seen.add(name)

    if inputs.required_method_count > 0 and len(seen) < inputs.required_method_count:
        errors.append(
            f"missing required results: need {inputs.required_method_count}, "
            f"got {len(seen)}"
        )

    if not isinstance(consensus, ConsensusResult) and not inputs.methods:
        warnings.append(
            "no method results supplied — method summary will be sparse "
            "(prefer ConsensusResult or explicit methods)"
        )

    if errors:
        raise OverallValuationError(
            "Overall valuation validation failed: " + "; ".join(dict.fromkeys(errors))
        )

    return ValidationSummary(
        ok=True,
        checks=tuple(dict.fromkeys(checks)),
        errors=(),
        warnings=tuple(dict.fromkeys(warnings)),
    )
