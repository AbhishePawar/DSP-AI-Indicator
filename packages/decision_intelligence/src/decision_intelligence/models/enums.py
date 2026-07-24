"""Enumerations for Decision Intelligence and Assurance."""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "AgreementQuality",
    "AssuranceLevel",
    "AssumptionRiskLevel",
    "DecisionResilience",
    "DriverDirection",
    "EvidenceConsistency",
    "GuidanceStance",
    "InvalidationSensitivity",
    "ReviewUrgency",
]


class AssuranceLevel(StrEnum):
    """How much confidence an investor should place in the recommendation."""

    HIGH = "high"
    MODERATE = "moderate"
    GUARDED = "guarded"
    LOW = "low"


class AgreementQuality(StrEnum):
    """Structural quality of committee agreement."""

    UNANIMOUS = "unanimous"
    STRONG_MAJORITY = "strong_majority"
    MAJORITY = "majority"
    NARROW = "narrow"
    CONFLICT = "conflict"


class AssumptionRiskLevel(StrEnum):
    """Fragility of critical assumptions behind the decision."""

    LOW = "low"
    ELEVATED = "elevated"
    HIGH = "high"


class EvidenceConsistency(StrEnum):
    """Alignment of supporting evidence with the final action."""

    ALIGNED = "aligned"
    MIXED = "mixed"
    THIN = "thin"


class DecisionResilience(StrEnum):
    """Composite structural resilience of the deliberation outcome."""

    ROBUST = "robust"
    ADEQUATE = "adequate"
    FRAGILE = "fragile"
    BRITTLE = "brittle"


class InvalidationSensitivity(StrEnum):
    """How sensitive the outcome is to a single member flip."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DriverDirection(StrEnum):
    """Whether a confidence driver supports or weakens assurance."""

    SUPPORTS = "supports"
    WEAKENS = "weakens"


class ReviewUrgency(StrEnum):
    """When a review trigger should be acted on."""

    IMMEDIATE = "immediate"
    NEXT_EVENT = "next_event"
    ONGOING = "ongoing"


class GuidanceStance(StrEnum):
    """Deterministic investor engagement posture."""

    INVEST_IMMEDIATELY = "invest_immediately"
    ACCUMULATE_GRADUALLY = "accumulate_gradually"
    WAIT_FOR_CONFIRMATION = "wait_for_confirmation"
    REVIEW_AFTER_EARNINGS = "review_after_earnings"
    MONITOR_MACRO_CHANGE = "monitor_macro_change"
    WATCH_VALUATION = "watch_valuation"
    STAND_ASIDE = "stand_aside"
