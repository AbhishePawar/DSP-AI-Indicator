"""Deterministic DCF sensitivity matrix."""

from __future__ import annotations

from dataclasses import dataclass, replace

from valuation.dcf_intelligence.assumptions import (
    DcfForecastAssumptions,
    DcfSensitivitySpec,
    DcfTerminalAssumptions,
)
from valuation.dcf_intelligence.explain import ExplainedValue
from valuation.exceptions import ValuationError

__all__ = ["SensitivityCell", "SensitivityMatrix", "build_sensitivity_matrix"]


@dataclass(frozen=True, slots=True)
class SensitivityCell:
    """One sensitivity grid cell."""

    dimension: str
    delta: float
    parameter_value: float
    enterprise_value: float
    equity_value: float
    intrinsic_value_per_share: float | None


@dataclass(frozen=True, slots=True)
class SensitivityMatrix:
    """Sensitivity results for growth, WACC, and terminal growth."""

    growth: tuple[SensitivityCell, ...]
    wacc: tuple[SensitivityCell, ...]
    terminal_growth: tuple[SensitivityCell, ...]
    explained: ExplainedValue


def build_sensitivity_matrix(
    *,
    base_forecast: DcfForecastAssumptions,
    base_terminal: DcfTerminalAssumptions,
    base_wacc: float,
    base_bridge_equity_fn,
    spec: DcfSensitivitySpec,
) -> SensitivityMatrix:
    """Build one-factor-at-a-time sensitivity around the base case.

    ``base_bridge_equity_fn(forecast, terminal, wacc) -> tuple[ev, equity, ivps]``
    """
    growth_cells: list[SensitivityCell] = []
    for delta in spec.growth_deltas:
        g = base_forecast.revenue_growth + delta
        try:
            forecast = replace(base_forecast, revenue_growth=g)
            ev, eq, ivps = base_bridge_equity_fn(forecast, base_terminal, base_wacc)
        except (ValuationError, ValueError):
            continue
        growth_cells.append(
            SensitivityCell(
                dimension="revenue_growth",
                delta=delta,
                parameter_value=g,
                enterprise_value=ev,
                equity_value=eq,
                intrinsic_value_per_share=ivps,
            )
        )

    wacc_cells: list[SensitivityCell] = []
    for delta in spec.wacc_deltas:
        w = base_wacc + delta
        if w <= base_terminal.perpetual_growth:
            continue
        try:
            ev, eq, ivps = base_bridge_equity_fn(
                base_forecast, base_terminal, w
            )
        except (ValuationError, ValueError):
            continue
        wacc_cells.append(
            SensitivityCell(
                dimension="wacc",
                delta=delta,
                parameter_value=w,
                enterprise_value=ev,
                equity_value=eq,
                intrinsic_value_per_share=ivps,
            )
        )

    tg_cells: list[SensitivityCell] = []
    for delta in spec.terminal_growth_deltas:
        tg = base_terminal.perpetual_growth + delta
        if base_wacc <= tg:
            continue
        try:
            terminal = replace(base_terminal, perpetual_growth=tg)
            ev, eq, ivps = base_bridge_equity_fn(
                base_forecast, terminal, base_wacc
            )
        except (ValuationError, ValueError):
            continue
        tg_cells.append(
            SensitivityCell(
                dimension="terminal_growth",
                delta=delta,
                parameter_value=tg,
                enterprise_value=ev,
                equity_value=eq,
                intrinsic_value_per_share=ivps,
            )
        )

    explained = ExplainedValue(
        name="sensitivity_matrix",
        value=float(len(growth_cells) + len(wacc_cells) + len(tg_cells)),
        formula="One-factor OTAT grid on growth, WACC, terminal growth",
        inputs={
            "growth_deltas": list(spec.growth_deltas),
            "wacc_deltas": list(spec.wacc_deltas),
            "terminal_growth_deltas": list(spec.terminal_growth_deltas),
        },
        intermediates={
            "growth_cells": len(growth_cells),
            "wacc_cells": len(wacc_cells),
            "terminal_growth_cells": len(tg_cells),
        },
        confidence="high",
        notes="Deterministic; no Monte Carlo.",
    )

    return SensitivityMatrix(
        growth=tuple(growth_cells),
        wacc=tuple(wacc_cells),
        terminal_growth=tuple(tg_cells),
        explained=explained,
    )
