"""Present value of forecast FCFF and terminal value → Enterprise Value."""

from __future__ import annotations

from dataclasses import dataclass

from valuation.dcf_intelligence.explain import ExplainedValue
from valuation.dcf_intelligence.forecast import ForecastLine
from valuation.exceptions import ValuationError

__all__ = ["PresentValueResult", "compute_present_values"]


@dataclass(frozen=True, slots=True)
class DiscountedLine:
    """One discounted forecast year."""

    year: int
    fcff: float
    discount_factor: float
    present_value: float
    explained: ExplainedValue


@dataclass(frozen=True, slots=True)
class PresentValueResult:
    """Enterprise value from discounted FCFF + discounted terminal value."""

    discounted_lines: tuple[DiscountedLine, ...]
    sum_pv_fcff: ExplainedValue
    pv_terminal: ExplainedValue
    enterprise_value: ExplainedValue
    terminal_share_of_ev: ExplainedValue


def compute_present_values(
    *,
    lines: tuple[ForecastLine, ...],
    terminal_value: float,
    wacc: float,
) -> PresentValueResult:
    """Discount explicit FCFF and terminal value at WACC.

    Raises:
        ValuationError: If WACC is non-positive or lines empty.
    """
    if wacc <= 0:
        raise ValuationError(f"wacc must be positive, got {wacc}")
    if not lines:
        raise ValuationError("forecast lines must not be empty")

    discounted: list[DiscountedLine] = []
    sum_pv = 0.0
    for line in lines:
        df = 1.0 / ((1.0 + wacc) ** line.year)
        pv = line.fcff * df
        sum_pv += pv
        discounted.append(
            DiscountedLine(
                year=line.year,
                fcff=line.fcff,
                discount_factor=df,
                present_value=pv,
                explained=ExplainedValue(
                    name=f"pv_fcff_year_{line.year}",
                    value=pv,
                    formula="PV = FCFFₜ / (1+WACC)ᵗ",
                    inputs={"fcff": line.fcff, "wacc": wacc, "year": line.year},
                    intermediates={"discount_factor": df},
                    confidence="high",
                ),
            )
        )

    n = lines[-1].year
    df_n = 1.0 / ((1.0 + wacc) ** n)
    pv_tv = terminal_value * df_n
    pv_terminal = ExplainedValue(
        name="present_value_terminal",
        value=pv_tv,
        formula="PV_TV = TV / (1+WACC)ⁿ",
        inputs={"terminal_value": terminal_value, "wacc": wacc, "n": n},
        intermediates={"discount_factor": df_n},
        confidence="high",
    )

    sum_pv_fcff = ExplainedValue(
        name="sum_present_value_fcff",
        value=sum_pv,
        formula="Σ PV(FCFFₜ)",
        inputs={"years": len(lines), "wacc": wacc},
        intermediates={"sum": sum_pv},
        confidence="high",
    )

    ev = sum_pv + pv_tv
    enterprise_value = ExplainedValue(
        name="enterprise_value",
        value=ev,
        formula="EV = Σ PV(FCFF) + PV(TV)",
        inputs={"sum_pv_fcff": sum_pv, "pv_terminal": pv_tv},
        intermediates={},
        confidence="high",
    )

    share = 0.0 if ev == 0 else pv_tv / ev
    terminal_share = ExplainedValue(
        name="terminal_value_share_of_ev",
        value=share,
        formula="TV_share = PV(TV) / EV",
        inputs={"pv_terminal": pv_tv, "enterprise_value": ev},
        intermediates={},
        confidence="high",
        notes="High terminal share increases terminal-model dependence risk.",
    )

    return PresentValueResult(
        discounted_lines=tuple(discounted),
        sum_pv_fcff=sum_pv_fcff,
        pv_terminal=pv_terminal,
        enterprise_value=enterprise_value,
        terminal_share_of_ev=terminal_share,
    )
