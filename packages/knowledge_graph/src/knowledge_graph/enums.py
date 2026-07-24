"""Enumerations for Knowledge Graph domain models (I1.0)."""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "AssemblyStatus",
    "EngineStatus",
    "EvidenceLinkCategory",
    "LineageCategory",
    "NodeCategory",
    "RelationshipCategory",
    "ReportingStatus",
]


class AssemblyStatus(StrEnum):
    """Assembler outcome — structural completeness only, not graph quality."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    EMPTY = "empty"
    FAILED = "failed"


class EngineStatus(StrEnum):
    """Knowledge Graph engine run completeness — not a market-quality score."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


class ReportingStatus(StrEnum):
    """Reporting completeness — presentation only, not a graph-quality score."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    EMPTY = "empty"
    FAILED = "failed"


class NodeCategory(StrEnum):
    """Frozen node taxonomy — never a business conclusion."""

    COMPANY = "company"
    SECURITY = "security"
    PORTFOLIO = "portfolio"
    REPORT = "report"
    EVIDENCE = "evidence"
    WORKFLOW = "workflow"
    RECOMMENDATION = "recommendation"
    RISK = "risk"
    RESEARCH = "research"
    ENTITY = "entity"


class RelationshipCategory(StrEnum):
    """Frozen relationship taxonomy."""

    REFERENCES = "references"
    DERIVES_FROM = "derives_from"
    DEPENDS_ON = "depends_on"
    SUPPORTED_BY = "supported_by"
    GENERATED_BY = "generated_by"
    EXECUTED_BY = "executed_by"
    RELATED_TO = "related_to"


class EvidenceLinkCategory(StrEnum):
    """Frozen evidence-link taxonomy."""

    DIRECT = "direct"
    INDIRECT = "indirect"
    DERIVED = "derived"


class LineageCategory(StrEnum):
    """Frozen lineage taxonomy."""

    REPORT = "report"
    EXECUTION = "execution"
    EVIDENCE = "evidence"
