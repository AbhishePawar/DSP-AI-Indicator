"""Enumerations for Recommendation Intelligence domain models (G1.0)."""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "AssemblyStatus",
    "ConfidenceLevel",
    "ConflictSeverity",
    "EngineStatus",
    "RecommendationType",
    "ReportingStatus",
    "SignalPosture",
]


class RecommendationType(StrEnum):
    """Action posture for a recommendation option — not an OMS order."""

    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    REDUCE = "reduce"
    SELL = "sell"
    WATCH = "watch"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ConflictSeverity(StrEnum):
    """Declared conflict severity — descriptive only."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ConfidenceLevel(StrEnum):
    """Categorical confidence label — complements Decimal RecommendationScore."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class AssemblyStatus(StrEnum):
    """Assembler outcome — structural completeness only, not recommendation quality."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    EMPTY = "empty"
    FAILED = "failed"


class EngineStatus(StrEnum):
    """Recommendation engine run completeness — not a market-quality score."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


class SignalPosture(StrEnum):
    """Caller-declared cite-backed posture — never computed by primary analysis."""

    SUPPORTIVE = "supportive"
    NEUTRAL = "neutral"
    CAUTIONARY = "cautionary"
    ADVERSE = "adverse"
    UNKNOWN = "unknown"


class ReportingStatus(StrEnum):
    """Reporting completeness — presentation only, not a recommendation score."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    EMPTY = "empty"
    FAILED = "failed"
