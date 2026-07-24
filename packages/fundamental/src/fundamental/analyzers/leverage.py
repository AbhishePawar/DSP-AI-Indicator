"""Leverage analysis: how much of a company's capital structure is debt."""

from __future__ import annotations

from fundamental.analyzers._math import safe_divide
from fundamental.analyzers.base import Analyzer
from fundamental.enums import MetricUnit
from fundamental.models import FinancialSnapshot, FundamentalMetric

__all__ = ["LeverageAnalyzer"]


class LeverageAnalyzer(Analyzer):
    """Computes balance-sheet leverage ratios for the latest period.

    Produces ``debt_to_equity``. Kept to a single metric this sprint —
    see ``packages/fundamental/README.md`` ("Design Decisions") for why
    a broader balance-sheet-strength signal is deliberately out of
    scope.
    """

    @property
    def name(self) -> str:
        """Canonical analyzer identifier."""
        return "leverage"

    def analyze(self, snapshot: FinancialSnapshot) -> tuple[FundamentalMetric, ...]:
        """Compute debt-to-equity for the latest reporting period.

        Args:
            snapshot: The financial statements to analyze.

        Returns:
            The debt-to-equity metric, with ``value=None`` if
            ``total_debt`` or ``total_equity`` was not reported, or
            ``total_equity`` is zero.
        """
        latest = snapshot.latest
        return (
            FundamentalMetric(
                instrument=snapshot.instrument,
                name="debt_to_equity",
                value=safe_divide(latest.total_debt, latest.total_equity),
                unit=MetricUnit.RATIO,
                period_end=latest.period_end,
            ),
        )
