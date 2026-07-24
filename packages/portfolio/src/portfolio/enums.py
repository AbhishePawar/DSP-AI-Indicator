"""Enumerations for Portfolio domain models (structure only)."""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "PortfolioAnalysisStatus",
    "PortfolioAssemblyStatus",
    "PortfolioChangeType",
    "PortfolioCitationStatus",
    "PortfolioConstraintKind",
    "PortfolioMonitoringStatus",
    "PortfolioType",
]


class PortfolioType(StrEnum):
    """Descriptive portfolio classification — not a strategy engine."""

    MODEL = "model"
    LIVE = "live"
    PAPER = "paper"
    RESEARCH = "research"
    WATCHLIST = "watchlist"
    OTHER = "other"


class PortfolioConstraintKind(StrEnum):
    """Policy constraint kinds — descriptive only; no evaluation logic."""

    MAX_POSITION_WEIGHT = "max_position_weight"
    MAX_SECTOR_WEIGHT = "max_sector_weight"
    MAX_INDUSTRY_WEIGHT = "max_industry_weight"
    MIN_CASH_WEIGHT = "min_cash_weight"
    MAX_HOLDINGS = "max_holdings"
    CUSTOM = "custom"


class PortfolioAssemblyStatus(StrEnum):
    """Assembler outcome — not a portfolio quality score."""

    COMPLETE = "complete"
    PARTIAL = "partial"


class PortfolioAnalysisStatus(StrEnum):
    """Qualitative analysis outcome — not a portfolio quality score."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    EMPTY = "empty"


class PortfolioCitationStatus(StrEnum):
    """Citation aggregation outcome — not a portfolio quality score."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    EMPTY = "empty"
    ABSENT = "absent"


class PortfolioMonitoringStatus(StrEnum):
    """Monitoring outcome — historical completeness only, not quality."""

    EMPTY = "empty"
    INITIAL = "initial"
    UNCHANGED = "unchanged"
    CHANGED = "changed"


class PortfolioChangeType(StrEnum):
    """Descriptive portfolio state-change kinds — never trade signals."""

    HOLDING_ADDED = "holding_added"
    HOLDING_REMOVED = "holding_removed"
    WEIGHT_CHANGED = "weight_changed"
    CASH_CHANGED = "cash_changed"
    EVIDENCE_COVERAGE_CHANGED = "evidence_coverage_changed"
    DECISION_COVERAGE_CHANGED = "decision_coverage_changed"
    CONSTRAINT_METADATA_CHANGED = "constraint_metadata_changed"
    SNAPSHOT_RECORDED = "snapshot_recorded"
