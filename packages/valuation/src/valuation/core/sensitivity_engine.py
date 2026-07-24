"""Reusable sensitivity grid generator (heatmap-ready)."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from valuation.core.errors import SensitivityError
from valuation.core.interfaces import SensitivityProvider
from valuation.core.result_models import SensitivityCell, SensitivityMatrix

__all__ = ["SensitivityEngine", "SensitivityAxis"]

Evaluator = Callable[[Mapping[str, Any]], float | None]


class SensitivityAxis:
    """One sensitivity dimension and its sample values."""

    __slots__ = ("name", "values")

    def __init__(self, name: str, values: Sequence[float]) -> None:
        self.name = name
        self.values = tuple(float(v) for v in values)


class SensitivityEngine(SensitivityProvider):
    """Build OTAT (one-factor-at-a-time) sensitivity grids.

    Supported axis names (convention): growth, wacc, roe, cost_of_equity,
    terminal_growth, terminal_roe, payout_ratio, margin, forecast_period.
    """

    def sensitivity(
        self,
        context: Mapping[str, Any],
        *,
        axes: Sequence[SensitivityAxis] | None = None,
        evaluator: Evaluator | None = None,
        output_name: str = "intrinsic_value",
    ) -> SensitivityMatrix:
        """Generate named grids.

        ``evaluator(merged_context)`` returns the scalar output for one cell.
        """
        if axes is None:
            axes = (
                SensitivityAxis("growth", (-0.02, 0.0, 0.02)),
                SensitivityAxis("wacc", (-0.01, 0.0, 0.01)),
            )
        if evaluator is None:
            grids = {
                axis.name: tuple(
                    SensitivityCell(
                        dimension=axis.name,
                        parameter_value=v,
                        output_name=output_name,
                        output_value=None,
                        row=0,
                        column=i,
                    )
                    for i, v in enumerate(axis.values)
                )
                for axis in axes
            }
            return SensitivityMatrix(grids=grids, notes="No evaluator provided")

        grids: dict[str, tuple[SensitivityCell, ...]] = {}
        for axis in axes:
            cells: list[SensitivityCell] = []
            for col, value in enumerate(axis.values):
                # OTAT: interpret values as absolute overrides when context
                # already holds the base key; if value looks like a delta
                # key is missing, store as absolute sample.
                merged = dict(context)
                if axis.name in context and isinstance(context[axis.name], (int, float)):
                    # treat sequence as absolute levels when caller passes levels
                    merged[axis.name] = value
                else:
                    merged[axis.name] = value
                try:
                    out = evaluator(merged)
                except Exception as exc:  # noqa: BLE001
                    raise SensitivityError(
                        f"sensitivity {axis.name}={value} failed: {exc}"
                    ) from exc
                cells.append(
                    SensitivityCell(
                        dimension=axis.name,
                        parameter_value=value,
                        output_name=output_name,
                        output_value=None if out is None else float(out),
                        row=0,
                        column=col,
                    )
                )
            grids[axis.name] = tuple(cells)
        return SensitivityMatrix(
            grids=grids,
            notes="OTAT sensitivity; heatmap-ready cells include row/column.",
        )
