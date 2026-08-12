"""Valuation firewall — educational layer must not mutate quantitative outputs."""

from __future__ import annotations

import copy
from typing import Any, Mapping

# Fields the educational synthesizer must never write or alter on inputs.
PROTECTED_INPUT_KEYS: frozenset[str] = frozenset(
    {
        "valuation_signals",
        "valuationSignals",
        "intrinsic_value",
        "intrinsicValue",
        "market_price",
        "marketPrice",
        "margin_of_safety",
        "marginOfSafety",
        "buffett_score",
        "buffettScore",
        "valuation_score",
        "valuationScore",
        "buy_zone",
        "buyZone",
        "valuation_consensus",
        "valuationConsensus",
        "recommendation",
    }
)

# Keys that must never appear as invented outputs from educational synthesis.
FORBIDDEN_OUTPUT_KEYS: frozenset[str] = frozenset(
    {
        "intrinsic_value",
        "intrinsicValue",
        "market_price",
        "marketPrice",
        "margin_of_safety",
        "marginOfSafety",
        "buffett_score",
        "buffettScore",
        "valuation_score",
        "valuationScore",
        "buy_zone",
        "buyZone",
        "price_target",
        "priceTarget",
        "expected_return",
        "expectedReturn",
        "recommendation_action",
        "recommendationAction",
    }
)


class ValuationFirewallError(RuntimeError):
    """Raised when educational analysis attempts to breach the valuation boundary."""


def snapshot_protected(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Deep-copy protected keys from an analysis payload for later comparison."""
    if not payload:
        return {}
    out: dict[str, Any] = {}
    for key in PROTECTED_INPUT_KEYS:
        if key in payload:
            out[key] = copy.deepcopy(payload[key])
    # Nested recommendation / valuation under stages
    stages = payload.get("stages")
    if isinstance(stages, Mapping):
        for stage_key in ("valuation", "recommendation", "buffett"):
            if stage_key in stages:
                out[f"stages.{stage_key}"] = copy.deepcopy(stages[stage_key])
    return out


def assert_inputs_unchanged(
    original_snapshot: Mapping[str, Any],
    payload_after: Mapping[str, Any] | None,
) -> None:
    """Ensure caller did not mutate protected quantitative fields in-place."""
    after = snapshot_protected(payload_after)
    for key, before_val in original_snapshot.items():
        if after.get(key) != before_val:
            raise ValuationFirewallError(
                f"Educational analysis must not modify protected field: {key}"
            )


def assert_report_has_no_forbidden_outputs(report: Mapping[str, Any]) -> None:
    """Educational report must not invent quantitative investment outputs."""
    stack: list[Any] = [report]
    while stack:
        node = stack.pop()
        if isinstance(node, Mapping):
            for k, v in node.items():
                if k in FORBIDDEN_OUTPUT_KEYS:
                    raise ValuationFirewallError(
                        f"Educational report must not include forbidden key: {k}"
                    )
                stack.append(v)
        elif isinstance(node, (list, tuple)):
            stack.extend(node)


def isolate_read_only_inputs(
    analysis_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return a deep copy so synthesis cannot mutate the caller's payload."""
    return copy.deepcopy(dict(analysis_payload or {}))
