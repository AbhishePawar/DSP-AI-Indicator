"""Research Intelligence public API — models through reporter (F1.0–F1.3)."""

from __future__ import annotations

from research.assembler import (
    ResearchAssembler,
    ResearchAssemblyContext,
    ResearchAssemblyResult,
)
from research.enums import (
    ResearchAssemblyStatus,
    ResearchConflictSeverity,
    ResearchCoverageStatus,
    ResearchGapStatus,
    ResearchPriorityLevel,
    ResearchReportingStatus,
    ResearchSynthesisStatus,
)
from research.exceptions import ResearchError
from research.models import (
    ResearchAgenda,
    ResearchConflict,
    ResearchCoverage,
    ResearchGap,
    ResearchIdentity,
    ResearchInsight,
    ResearchObservation,
    ResearchPriority,
    ResearchProfile,
    ResearchReport,
    ResearchSummary,
)
from research.refs import (
    ComparisonReference,
    DecisionReference,
    EvidenceReference,
    IntegratedRiskReference,
    MonitoringReference,
    PortfolioReference,
    RiskReference,
)
from research.reporter import (
    ResearchReporter,
    ResearchReportingContext,
    ResearchReportingResult,
)
from research.synthesizer import (
    ResearchSynthesisContext,
    ResearchSynthesisResult,
    ResearchSynthesizer,
)

__all__ = [
    "ComparisonReference",
    "DecisionReference",
    "EvidenceReference",
    "IntegratedRiskReference",
    "MonitoringReference",
    "PortfolioReference",
    "ResearchAgenda",
    "ResearchAssembler",
    "ResearchAssemblyContext",
    "ResearchAssemblyResult",
    "ResearchAssemblyStatus",
    "ResearchConflict",
    "ResearchConflictSeverity",
    "ResearchCoverage",
    "ResearchCoverageStatus",
    "ResearchError",
    "ResearchGap",
    "ResearchGapStatus",
    "ResearchIdentity",
    "ResearchInsight",
    "ResearchObservation",
    "ResearchPriority",
    "ResearchPriorityLevel",
    "ResearchProfile",
    "ResearchReport",
    "ResearchReporter",
    "ResearchReportingContext",
    "ResearchReportingResult",
    "ResearchReportingStatus",
    "ResearchSummary",
    "ResearchSynthesisContext",
    "ResearchSynthesisResult",
    "ResearchSynthesisStatus",
    "ResearchSynthesizer",
    "RiskReference",
]

__version__ = "0.4.0"
