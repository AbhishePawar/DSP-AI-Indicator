"""Analyzer abstraction and concrete business-analysis analyzers.

Each concrete analyzer here has exactly one responsibility (Section 5.1
of the architecture document's Single Responsibility guidance) and
produces one or more :class:`~fundamental.models.FundamentalMetric`
objects. Adding a new category of analysis (liquidity, efficiency, and
so on) means adding a new module here and registering it in
:mod:`fundamental.registry` — it never requires modifying
:class:`~fundamental.engine.service.FundamentalEngine`.
"""

from fundamental.analyzers.base import Analyzer
from fundamental.analyzers.growth import GrowthAnalyzer
from fundamental.analyzers.leverage import LeverageAnalyzer
from fundamental.analyzers.profitability import ProfitabilityAnalyzer
from fundamental.analyzers.quality import QualityAnalyzer

__all__ = [
    "Analyzer",
    "GrowthAnalyzer",
    "LeverageAnalyzer",
    "ProfitabilityAnalyzer",
    "QualityAnalyzer",
]
