"""Platform orchestration — the single official analysis pipeline.

Sprint 7.0 introduces the application layer that composes completed
packages into one legal path:

    Instrument → Data → Snapshots → Engines → Committee → CommitteeReport

This package owns **flow only**. It never performs indicator math,
fundamental scoring, economic regime classification, voting, provider
parsing, or snapshot construction.
"""

from __future__ import annotations

from orchestration.committee_mapping import (
    to_economic_context,
    to_fundamental_context,
    to_technical_context,
    to_valuation_context,
)
from orchestration.exceptions import OrchestrationError
from orchestration.models import AnalysisRequest
from orchestration.service import InvestmentAnalysisService
from recommendation import RecommendationMapper

__all__ = [
    "AnalysisRequest",
    "InvestmentAnalysisService",
    "OrchestrationError",
    "RecommendationMapper",
    "to_economic_context",
    "to_fundamental_context",
    "to_technical_context",
    "to_valuation_context",
]

__version__ = "0.2.0"
