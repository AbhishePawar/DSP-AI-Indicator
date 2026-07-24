"""Profitability analysis: how efficiently a company turns inputs into profit."""

from __future__ import annotations

from contracts.domain.fundamental_statement import FundamentalStatement
from fundamental.analyzers._math import safe_divide
from fundamental.analyzers.base import Analyzer
from fundamental.enums import MetricUnit
from fundamental.models import FinancialSnapshot, FundamentalMetric

__all__ = ["ProfitabilityAnalyzer"]


def _capital_employed(statement: FundamentalStatement) -> float | None:
    """Approximate capital employed as total equity plus total debt.

    ``FundamentalStatement`` does not report current liabilities
    separately, so the textbook "assets minus current liabilities"
    definition of capital employed is not computable from it. Equity
    plus interest-bearing debt is the standard, widely used
    approximation when only balance-sheet totals are available.
    """
    if statement.total_equity is None:
        return None
    return statement.total_equity + (statement.total_debt or 0.0)


class ProfitabilityAnalyzer(Analyzer):
    """Computes profitability ratios for the latest reporting period.

    Produces ``roe`` (return on equity), ``roce`` (return on capital
    employed), and ``operating_margin``. All three describe the same
    reporting period, so this analyzer only ever needs
    ``snapshot.latest``.
    """

    @property
    def name(self) -> str:
        """Canonical analyzer identifier."""
        return "profitability"

    def analyze(self, snapshot: FinancialSnapshot) -> tuple[FundamentalMetric, ...]:
        """Compute ROE, ROCE, and operating margin for the latest period.

        Args:
            snapshot: The financial statements to analyze.

        Returns:
            The three profitability metrics, each with ``value=None``
            if its required line items were not reported.
        """
        latest = snapshot.latest
        instrument = snapshot.instrument
        return (
            FundamentalMetric(
                instrument=instrument,
                name="roe",
                value=safe_divide(latest.net_income, latest.total_equity),
                unit=MetricUnit.PERCENT,
                period_end=latest.period_end,
            ),
            FundamentalMetric(
                instrument=instrument,
                name="roce",
                value=safe_divide(latest.operating_income, _capital_employed(latest)),
                unit=MetricUnit.PERCENT,
                period_end=latest.period_end,
            ),
            FundamentalMetric(
                instrument=instrument,
                name="operating_margin",
                value=safe_divide(latest.operating_income, latest.revenue),
                unit=MetricUnit.PERCENT,
                period_end=latest.period_end,
            ),
        )
