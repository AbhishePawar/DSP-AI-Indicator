"""Shared protocol / type exports for the compliance context."""

from __future__ import annotations

from compliance.ai_governance import ChallengeBrief, ChallengeModePort
from compliance.analyst_consensus import ConsensusProviderPort, ConsensusSnapshot
from compliance.audit import AuditEvent, AuditPort
from compliance.conflicts import ConflictPort, ConflictRecord
from compliance.disclaimer_engine import Disclaimer, DisclaimerEnginePort
from compliance.disclosures import Disclosure, DisclosurePort
from compliance.feature_flags import FeatureFlags
from compliance.methodology import MethodologyNote, MethodologyPort
from compliance.recommendation_history import (
    RecommendationHistoryEntry,
    RecommendationHistoryPort,
)
from compliance.research_archive import ArchivedResearch, ResearchArchivePort

__all__ = [
    "ArchivedResearch",
    "AuditEvent",
    "AuditPort",
    "ChallengeBrief",
    "ChallengeModePort",
    "ConflictPort",
    "ConflictRecord",
    "ConsensusProviderPort",
    "ConsensusSnapshot",
    "Disclaimer",
    "DisclaimerEnginePort",
    "Disclosure",
    "DisclosurePort",
    "FeatureFlags",
    "MethodologyNote",
    "MethodologyPort",
    "RecommendationHistoryEntry",
    "RecommendationHistoryPort",
    "ResearchArchivePort",
]
