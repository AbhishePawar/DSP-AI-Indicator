"""Enumerations for Risk domain models (structure only)."""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "RiskAnalysisStatus",
    "RiskAssemblyStatus",
    "RiskConstraintKind",
    "RiskCoverageKind",
    "RiskCoverageStatus",
    "RiskIntegrationStatus",
    "RiskLevel",
    "RiskReportingStatus",
]


class RiskLevel(StrEnum):
    """Categorical risk posture — never a numeric score."""

    LOW = "low"
    MODERATE = "moderate"
    ELEVATED = "elevated"
    HIGH = "high"
    UNKNOWN = "unknown"


class RiskCoverageKind(StrEnum):
    """Coverage dimension — qualitative only."""

    DECISION = "decision"
    EVIDENCE = "evidence"
    COMPARISON = "comparison"


class RiskCoverageStatus(StrEnum):
    """Coverage completeness — not a quality score."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    ABSENT = "absent"
    UNKNOWN = "unknown"


class RiskConstraintKind(StrEnum):
    """Risk-policy descriptor kinds — not Portfolio constraints / optimizer limits."""

    CONCENTRATION_POSTURE = "concentration_posture"
    DIVERSIFICATION_POSTURE = "diversification_posture"
    EVIDENCE_COVERAGE_POSTURE = "evidence_coverage_posture"
    DECISION_COVERAGE_POSTURE = "decision_coverage_posture"
    LIQUIDITY_POSTURE = "liquidity_posture"
    EXPOSURE_POSTURE = "exposure_posture"
    CUSTOM = "custom"


class RiskAssemblyStatus(StrEnum):
    """Assembler outcome — structural completeness only, not a risk score."""

    COMPLETE = "complete"
    PARTIAL = "partial"


class RiskAnalysisStatus(StrEnum):
    """Qualitative analysis outcome — not a risk quality score."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    EMPTY = "empty"


class RiskReportingStatus(StrEnum):
    """Reporting completeness — presentation only, not a risk score."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    EMPTY = "empty"


class RiskIntegrationStatus(StrEnum):
    """Integration completeness — coordination only, not a risk score."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    EMPTY = "empty"
