"""DSP Compliance bounded context (PR1.0 + PEP-004 India Compliance Foundation)."""

from __future__ import annotations

from compliance.analysis_sections import ANALYSIS_PAGE_ORDER, AnalysisSection
from compliance.bundle import ComplianceBundle, CompliancePort
from compliance.consent import (
    ConsentPort,
    ConsentPurpose,
    ConsentRecord,
    ConsentVersion,
    InMemoryConsentPort,
)
from compliance.disclosure_templates import (
    DisclosureTemplateCatalog,
    InMemoryDisclosurePort,
    ResearchModeDisclosureEngine,
    format_inr,
    format_ist,
    research_mode_templates,
)
from compliance.export import ComplianceExport, ComplianceExportPort
from compliance.feature_flags import FeatureFlags, load_feature_flags
from compliance.history_adapters import (
    InMemoryRecommendationHistoryPort,
    InMemoryResearchArchivePort,
)
from compliance.retention import (
    AuditRetentionPolicy,
    AuditRetentionPort,
    ImmutableAuditReference,
    InMemoryAuditRetentionPort,
)
from compliance.terminology import (
    ResearchLabel,
    present_action,
    present_field_label,
)

__all__ = [
    "ANALYSIS_PAGE_ORDER",
    "AnalysisSection",
    "AuditRetentionPolicy",
    "AuditRetentionPort",
    "ComplianceBundle",
    "ComplianceExport",
    "ComplianceExportPort",
    "CompliancePort",
    "ConsentPort",
    "ConsentPurpose",
    "ConsentRecord",
    "ConsentVersion",
    "DisclosureTemplateCatalog",
    "FeatureFlags",
    "ImmutableAuditReference",
    "InMemoryAuditRetentionPort",
    "InMemoryConsentPort",
    "InMemoryDisclosurePort",
    "InMemoryRecommendationHistoryPort",
    "InMemoryResearchArchivePort",
    "ResearchLabel",
    "ResearchModeDisclosureEngine",
    "format_inr",
    "format_ist",
    "load_feature_flags",
    "present_action",
    "present_field_label",
    "research_mode_templates",
]

__version__ = "0.2.0"
