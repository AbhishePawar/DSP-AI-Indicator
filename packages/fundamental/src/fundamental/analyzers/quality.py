"""Quality analysis: how much of a company's earnings convert to cash."""

from __future__ import annotations

from fundamental.analyzers.base import Analyzer
from fundamental.enums import MetricUnit
from fundamental.models import FinancialSnapshot, FundamentalMetric

__all__ = ["QualityAnalyzer"]


class QualityAnalyzer(Analyzer):
    """Computes cash-generation quality metrics for the latest period.

    Produces ``free_cash_flow`` as ``operating_cash_flow -
    capital_expenditures``. This assumes ``capital_expenditures`` is
    reported as a non-negative magnitude of cash outflow, consistent
    with ``FundamentalStatement``'s own docstring ("cash used for
    capital expenditures").
    """

    @property
    def name(self) -> str:
        """Canonical analyzer identifier."""
        return "quality"

    def analyze(self, snapshot: FinancialSnapshot) -> tuple[FundamentalMetric, ...]:
        """Compute free cash flow for the latest reporting period.

        Args:
            snapshot: The financial statements to analyze.

        Returns:
            The free cash flow metric, with ``value=None`` if
            ``operating_cash_flow`` or ``capital_expenditures`` was not
            reported.
        """
        latest = snapshot.latest
        ocf = latest.operating_cash_flow
        capex = latest.capital_expenditures
        value = None if ocf is None or capex is None else ocf - capex
        return (
            FundamentalMetric(
                instrument=snapshot.instrument,
                name="free_cash_flow",
                value=value,
                unit=MetricUnit.CURRENCY,
                period_end=latest.period_end,
            ),
        )
