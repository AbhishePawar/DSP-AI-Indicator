"""Investment universe & multi-stock Decision Pack aggregation.

Sits above Decision Intelligence. Consumes completed ``DecisionPack``
artifacts only — never raw engine votes or recalculated MoS.
"""

from __future__ import annotations

from universe.enums import BatchFailurePolicy, BatchStatus, InstrumentOutcomeStatus
from universe.exceptions import UniverseError
from universe.filters import filter_entries, group_entries
from universe.models import (
    InvestmentUniverse,
    UniverseEntry,
    instrument_identity_key,
)
from universe.results import (
    InstrumentAnalysisFailure,
    InstrumentAnalysisOutcome,
    MultiStockAnalysisRequest,
    MultiStockDecisionResult,
)
from universe.service import DecisionPackAnalyzer, MultiStockAnalysisService
from universe.summary import ComparableDecisionSummary, summarize_decision_pack

__all__ = [
    "BatchFailurePolicy",
    "BatchStatus",
    "ComparableDecisionSummary",
    "DecisionPackAnalyzer",
    "InstrumentAnalysisFailure",
    "InstrumentAnalysisOutcome",
    "InstrumentOutcomeStatus",
    "InvestmentUniverse",
    "MultiStockAnalysisRequest",
    "MultiStockAnalysisService",
    "MultiStockDecisionResult",
    "UniverseEntry",
    "UniverseError",
    "filter_entries",
    "group_entries",
    "instrument_identity_key",
    "summarize_decision_pack",
]

__version__ = "0.1.0"
