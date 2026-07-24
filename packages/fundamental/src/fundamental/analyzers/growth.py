"""Growth analysis: how a company's revenue and earnings change over time."""

from __future__ import annotations

from fundamental.analyzers._math import growth_rate
from fundamental.analyzers.base import Analyzer
from fundamental.enums import MetricUnit
from fundamental.models import FinancialSnapshot, FundamentalMetric

__all__ = ["GrowthAnalyzer"]


class GrowthAnalyzer(Analyzer):
    """Computes period-over-period growth ratios.

    Produces ``revenue_growth`` and ``eps_growth``, each comparing
    ``snapshot.latest`` against ``snapshot.previous``. Unlike
    :class:`~fundamental.analyzers.profitability.ProfitabilityAnalyzer`,
    this analyzer is the reason :class:`FinancialSnapshot` carries more
    than a single reporting period: a growth ratio is undefined without
    a prior period to compare against.

    ``eps_growth`` uses ``eps_diluted`` only. A future sprint could add
    an ``eps_basic`` fallback; kept out of this sprint to match the
    "minimal metric set" scope of Sprint 4.0.
    """

    @property
    def name(self) -> str:
        """Canonical analyzer identifier."""
        return "growth"

    def analyze(self, snapshot: FinancialSnapshot) -> tuple[FundamentalMetric, ...]:
        """Compute revenue and EPS growth from the latest two periods.

        Args:
            snapshot: The financial statements to analyze.

        Returns:
            The two growth metrics, each with ``value=None`` if a prior
            period is unavailable or the underlying line item was not
            reported in either period.
        """
        latest = snapshot.latest
        previous = snapshot.previous
        instrument = snapshot.instrument
        previous_revenue = previous.revenue if previous else None
        previous_eps = previous.eps_diluted if previous else None
        return (
            FundamentalMetric(
                instrument=instrument,
                name="revenue_growth",
                value=growth_rate(previous_revenue, latest.revenue),
                unit=MetricUnit.PERCENT,
                period_end=latest.period_end,
            ),
            FundamentalMetric(
                instrument=instrument,
                name="eps_growth",
                value=growth_rate(previous_eps, latest.eps_diluted),
                unit=MetricUnit.PERCENT,
                period_end=latest.period_end,
            ),
        )
