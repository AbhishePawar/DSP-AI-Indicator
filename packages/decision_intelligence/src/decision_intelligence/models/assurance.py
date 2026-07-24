"""Decision Assurance domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contracts.domain.instrument import Instrument
from contracts.enums import RecommendationAction
from core.exceptions import ValidationError

from decision_intelligence.models.enums import (
    AgreementQuality,
    AssuranceLevel,
    AssumptionRiskLevel,
    DecisionResilience,
    DriverDirection,
    EvidenceConsistency,
    GuidanceStance,
    InvalidationSensitivity,
    ReviewUrgency,
)

__all__ = [
    "AssuranceAssessment",
    "ConfidenceDriver",
    "InvestorGuidance",
    "ReviewTrigger",
]


@dataclass(frozen=True, slots=True)
class ConfidenceDriver:
    """One factor that supports or weakens assurance."""

    code: str
    direction: DriverDirection
    statement: str

    def __post_init__(self) -> None:
        code = self.code.strip().lower()
        statement = self.statement.strip()
        if not code:
            msg = "code must not be empty"
            raise ValidationError(msg)
        if not statement:
            msg = "statement must not be empty"
            raise ValidationError(msg)
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "statement", statement)


@dataclass(frozen=True, slots=True)
class ReviewTrigger:
    """Condition that warrants revisiting the recommendation."""

    condition: str
    urgency: ReviewUrgency

    def __post_init__(self) -> None:
        condition = self.condition.strip()
        if not condition:
            msg = "condition must not be empty"
            raise ValidationError(msg)
        object.__setattr__(self, "condition", condition)


@dataclass(frozen=True, slots=True)
class InvestorGuidance:
    """Structured engagement posture for the investor."""

    stance: GuidanceStance
    rationale: str

    def __post_init__(self) -> None:
        rationale = self.rationale.strip()
        if not rationale:
            msg = "rationale must not be empty"
            raise ValidationError(msg)
        object.__setattr__(self, "rationale", rationale)


@dataclass(frozen=True, slots=True)
class AssuranceAssessment:
    """Fiduciary quality assessment of an already completed recommendation."""

    instrument: Instrument
    action: RecommendationAction
    conviction: float
    assurance_level: AssuranceLevel
    robustness_summary: str
    agreement_quality: AgreementQuality
    key_strengths: tuple[str, ...]
    key_fragilities: tuple[str, ...]
    confidence_drivers: tuple[ConfidenceDriver, ...]
    single_engine_dependence: bool
    dominant_supporting_source: str | None
    assumption_risk: AssumptionRiskLevel
    evidence_consistency: EvidenceConsistency
    decision_resilience: DecisionResilience
    invalidation_sensitivity: InvalidationSensitivity
    review_triggers: tuple[ReviewTrigger, ...]
    investor_guidance: InvestorGuidance
    generated_at: datetime

    def __post_init__(self) -> None:
        summary = self.robustness_summary.strip()
        if not summary:
            msg = "robustness_summary must not be empty"
            raise ValidationError(msg)
        if not (0.0 <= self.conviction <= 1.0):
            msg = "conviction must be in [0.0, 1.0]"
            raise ValidationError(msg)
        object.__setattr__(self, "robustness_summary", summary)
        object.__setattr__(self, "key_strengths", tuple(self.key_strengths))
        object.__setattr__(self, "key_fragilities", tuple(self.key_fragilities))
        object.__setattr__(
            self, "confidence_drivers", tuple(self.confidence_drivers)
        )
        object.__setattr__(self, "review_triggers", tuple(self.review_triggers))
        if self.dominant_supporting_source is not None:
            object.__setattr__(
                self,
                "dominant_supporting_source",
                self.dominant_supporting_source.strip().lower() or None,
            )
