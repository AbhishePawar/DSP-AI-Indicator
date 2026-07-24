"""Analyzer abstraction for the Fundamental Engine.

An :class:`Analyzer` has a single business-analysis responsibility (e.g.
profitability, growth, leverage) and knows how to turn one
:class:`~fundamental.models.FinancialSnapshot` into zero or more
:class:`~fundamental.models.FundamentalMetric` objects. Mirrors
``dsp.indicators.base.Indicator`` exactly in shape and in the division of
labor with its caller: an indicator's ``compute()`` returns a plain
array and the *engine* (not the indicator) stamps execution metadata
onto ``IndicatorResult``; likewise, ``Analyzer.analyze()`` returns plain
metrics and :class:`~fundamental.engine.service.FundamentalEngine` (not
the analyzer) stamps ``computed_at`` onto
:class:`~fundamental.models.FundamentalResult`. This keeps every
analyzer free of its own clock, which keeps them trivially testable.

Analyzers deliberately take a whole
:class:`~fundamental.models.FinancialSnapshot`, not a single number —
unlike an indicator's single price series, a business ratio routinely
needs several related line items (and sometimes a prior period) from
the same statement at once.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from fundamental.models import FinancialSnapshot, FundamentalMetric

__all__ = ["Analyzer"]


class Analyzer(ABC):
    """Base class every fundamental analyzer must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Canonical, lowercase identifier for this analyzer."""

    @abstractmethod
    def analyze(self, snapshot: FinancialSnapshot) -> tuple[FundamentalMetric, ...]:
        """Compute this analyzer's metrics for one financial snapshot.

        Args:
            snapshot: The financial statements to analyze.

        Returns:
            Every :class:`~fundamental.models.FundamentalMetric`
            this analyzer produces, in a stable order. A metric whose
            required inputs are unavailable is still returned, with
            ``value=None``, rather than omitted — so callers always know
            which metrics this analyzer covers.
        """
