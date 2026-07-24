"""Terminal value — Gordon Growth and optional Exit Multiple."""

from __future__ import annotations

from dataclasses import dataclass

from valuation.dcf_intelligence.assumptions import DcfTerminalAssumptions
from valuation.dcf_intelligence.explain import ExplainedValue
from valuation.exceptions import ValuationError

__all__ = ["TerminalValueResult", "compute_terminal_value"]


@dataclass(frozen=True, slots=True)
class TerminalValueResult:
    """Terminal value components at the end of the explicit forecast."""

    gordon_value: ExplainedValue | None
    exit_multiple_value: ExplainedValue | None
    blended_value: ExplainedValue
    method: str


def compute_terminal_value(
    *,
    last_fcff: float,
    last_ebitda: float,
    wacc: float,
    assumptions: DcfTerminalAssumptions,
) -> TerminalValueResult:
    """Compute terminal value with explainability.

    Raises:
        ValuationError: If Gordon spread is non-positive when required.
    """
    gordon: ExplainedValue | None = None
    exit_v: ExplainedValue | None = None

    if assumptions.method in {"gordon", "both"}:
        if wacc <= assumptions.perpetual_growth:
            raise ValuationError(
                "WACC must exceed perpetual growth for Gordon model "
                f"(wacc={wacc}, g={assumptions.perpetual_growth})"
            )
        tv = last_fcff * (1.0 + assumptions.perpetual_growth) / (
            wacc - assumptions.perpetual_growth
        )
        gordon = ExplainedValue(
            name="terminal_value_gordon",
            value=tv,
            formula="TV = FCFFₙ(1+g) / (WACC − g)",
            inputs={
                "last_fcff": last_fcff,
                "perpetual_growth": assumptions.perpetual_growth,
                "wacc": wacc,
            },
            intermediates={
                "numerator": last_fcff * (1.0 + assumptions.perpetual_growth),
                "denominator": wacc - assumptions.perpetual_growth,
            },
            confidence="high",
        )

    if assumptions.method in {"exit_multiple", "both"}:
        multiple = float(assumptions.exit_ebitda_multiple)  # type: ignore[arg-type]
        tv_exit = last_ebitda * multiple
        exit_v = ExplainedValue(
            name="terminal_value_exit_multiple",
            value=tv_exit,
            formula="TV_exit = EBITDAₙ × exit_multiple",
            inputs={
                "last_ebitda": last_ebitda,
                "exit_ebitda_multiple": multiple,
            },
            intermediates={},
            confidence="medium",
            notes="Exit multiple is an optional extension; use with caution.",
        )

    if assumptions.method == "gordon":
        assert gordon is not None and gordon.value is not None
        blended = ExplainedValue(
            name="terminal_value",
            value=gordon.value,
            formula="TV = Gordon Growth Model",
            inputs={"method": "gordon"},
            intermediates={"gordon": gordon.value},
            confidence="high",
        )
    elif assumptions.method == "exit_multiple":
        assert exit_v is not None and exit_v.value is not None
        blended = ExplainedValue(
            name="terminal_value",
            value=exit_v.value,
            formula="TV = Exit Multiple Model",
            inputs={"method": "exit_multiple"},
            intermediates={"exit_multiple": exit_v.value},
            confidence="medium",
        )
    else:
        assert gordon is not None and exit_v is not None
        assert gordon.value is not None and exit_v.value is not None
        w_g = assumptions.exit_weight_gordon
        blended_val = w_g * gordon.value + (1.0 - w_g) * exit_v.value
        blended = ExplainedValue(
            name="terminal_value",
            value=blended_val,
            formula="TV = w×Gordon + (1−w)×ExitMultiple",
            inputs={
                "method": "both",
                "exit_weight_gordon": w_g,
            },
            intermediates={
                "gordon": gordon.value,
                "exit_multiple": exit_v.value,
            },
            confidence="medium",
        )

    return TerminalValueResult(
        gordon_value=gordon,
        exit_multiple_value=exit_v,
        blended_value=blended,
        method=assumptions.method,
    )
