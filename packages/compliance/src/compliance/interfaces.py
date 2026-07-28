"""Shared protocol / type exports for the compliance context."""

from __future__ import annotations

from compliance.ai_governance import ChallengeBrief, ChallengeModePort
from compliance.analyst_consensus import ConsensusProviderPort, ConsensusSnapshot
from compliance.audit import AuditEvent, AuditPort
from compliance.bundle import ComplianceBundle, CompliancePort
from compliance.conflicts import ConflictPort, ConflictRecord
from compliance.consent import ConsentPort, ConsentRecord, ConsentVersion
from compliance.disclaimer_engine import Disclaimer, DisclaimerEnginePort
from compliance.disclosures import Disclosure, DisclosurePort
from compliance.export import ComplianceExportPort
from compliance.feature_flags import FeatureFlags
from compliance.methodology import MethodologyNote, MethodologyPort
from compliance.recommendation_history import (
    RecommendationHistoryEntry,
    RecommendationHistoryPort,
)
from compliance.research_archive import ArchivedResearch, ResearchArchivePort
from compliance.retention import AuditRetentionPort, ImmutableAuditReference

__all__ = [
    "ArchivedResearch",
    "AuditEvent",
    "AuditPort",
    "AuditRetentionPort",
    "ChallengeBrief",
    "ChallengeModePort",
    "ComplianceBundle",
    "ComplianceExportPort",
    "CompliancePort",
    "ConflictPort",
    "ConflictRecord",
    "ConsensusProviderPort",
    "ConsensusSnapshot",
    "ConsentPort",
    "ConsentRecord",
    "ConsentVersion",
    "Disclaimer",
    "DisclaimerEnginePort",
    "Disclosure",
    "DisclosurePort",
    "FeatureFlags",
    "ImmutableAuditReference",
    "MethodologyNote",
    "MethodologyPort",
    "RecommendationHistoryEntry",
    "RecommendationHistoryPort",
    "ResearchArchivePort",
]
