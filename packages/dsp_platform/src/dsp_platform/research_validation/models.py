"""Canonical ResearchPackage-bound AI validation models.

PATH SPLIT (do not silently merge):
    NEW PATH (this module):
        ResearchPackage → CanonicalAIResearchOutput → validation
        → PublicResearchReport
    OLD PATH (unchanged):
        DecisionPack / tool catalog → llm_adapters.orchestrator.validation
        → PublicDecisionPack

``llm_adapters.orchestrator.schema.AIResearchOutput`` remains the tool-loop
AI schema. This module does not import llm_adapters.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from dsp_platform.research_report.models import PublicResearchReport

__all__ = [
    "ALLOWED_AI_FIELD_NAMES",
    "CanonicalAIResearchOutput",
    "CanonicalValidationIssue",
    "CanonicalValidationKind",
    "CanonicalValidationResult",
    "CanonicalValidationStatus",
]

ALLOWED_AI_FIELD_NAMES = frozenset(
    {
        "executive_summary",
        "valuation_narrative",
        "business_quality_narrative",
        "economic_moat_narrative",
        "management_quality_narrative",
        "financial_strength_narrative",
        "earnings_quality_narrative",
        "growth_quality_narrative",
        "financials_narrative",
        "buffett_narrative",
        "risk_narrative",
        "recommendation_narrative",
        "current_price",
        "intrinsic_value",
        "intrinsic_value_per_share",
        "valuation_range_low",
        "valuation_range_mid",
        "valuation_range_high",
        "margin_of_safety",
        "financial_metrics",
        "quality_scores",
        "buffett_overall_score_100",
        "buffett_methodology",
        "buffett_weights",
        "circle_of_competence_score",
        "recommendation_action",
        "recommendation_score_100",
        "score_10",
        "score_10_status",
        "entry_price",
        "buy_price",
        "target_price",
        "exit_price",
        "stop_loss",
        "entry_zone",
        "scenarios",
        "expected_return",
        "expected_returns",
        "forward_cagr",
        "forecast_cagr",
        "evidence_ids",
    }
)


class CanonicalValidationStatus(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    FAILED_CLOSED = "failed_closed"


class CanonicalValidationKind(StrEnum):
    INVALID_INPUT = "invalid_input"
    NUMERICAL_MISMATCH = "numerical_mismatch"
    RECOMMENDATION_MISMATCH = "recommendation_mismatch"
    BUFFETT_MISMATCH = "buffett_mismatch"
    SCORE_10_FORBIDDEN = "score_10_forbidden"
    ENTRY_EXIT_FORBIDDEN = "entry_exit_forbidden"
    SCENARIO_FORBIDDEN = "scenario_forbidden"
    EXPECTED_RETURN_FORBIDDEN = "expected_return_forbidden"
    INVALID_EVIDENCE = "invalid_evidence"
    MISSING_EVIDENCE = "missing_evidence"
    PRIVACY = "privacy"
    CANARY = "canary"
    MISSING_DATA_FILL = "missing_data_fill"


@dataclass(frozen=True, slots=True)
class CanonicalValidationIssue:
    kind: CanonicalValidationKind
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind.value, "message": self.message}


@dataclass(frozen=True, slots=True)
class CanonicalValidationResult:
    status: CanonicalValidationStatus
    report: PublicResearchReport | None
    issues: tuple[CanonicalValidationIssue, ...]

    @property
    def ok(self) -> bool:
        return (
            self.status is CanonicalValidationStatus.VALID
            and self.report is not None
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "report": None if self.report is None else self.report.to_public_dict(),
            "issues": [item.to_dict() for item in self.issues],
        }


@dataclass(frozen=True, slots=True)
class CanonicalAIResearchOutput:
    """AI-owned draft for the ResearchPackage path.

    Numeric fields are optional attempted DSP values. If present they must
    equal ResearchPackage. If omitted, DSP values are used unchanged.
    """

    executive_summary: str | None = None
    valuation_narrative: str | None = None
    business_quality_narrative: str | None = None
    economic_moat_narrative: str | None = None
    management_quality_narrative: str | None = None
    financial_strength_narrative: str | None = None
    earnings_quality_narrative: str | None = None
    growth_quality_narrative: str | None = None
    financials_narrative: str | None = None
    buffett_narrative: str | None = None
    risk_narrative: str | None = None
    recommendation_narrative: str | None = None
    current_price: float | None = None
    intrinsic_value: float | None = None
    valuation_range_low: float | None = None
    valuation_range_mid: float | None = None
    valuation_range_high: float | None = None
    margin_of_safety: float | None = None
    financial_metrics: Mapping[str, float | None] | None = None
    quality_scores: Mapping[str, float | None] | None = None
    buffett_overall_score_100: float | None = None
    buffett_methodology: str | None = None
    buffett_weights: Mapping[str, Any] | None = None
    circle_of_competence_score: float | None = None
    recommendation_action: str | None = None
    recommendation_score_100: float | None = None
    score_10: float | Mapping[str, float | None] | None = None
    score_10_status: str | None = None
    entry_price: float | None = None
    buy_price: float | None = None
    target_price: float | None = None
    exit_price: float | None = None
    stop_loss: float | None = None
    entry_zone: float | None = None
    scenarios: Mapping[str, Any] | None = None
    expected_return: float | None = None
    expected_returns: float | None = None
    forward_cagr: float | None = None
    forecast_cagr: float | None = None
    evidence_ids: tuple[str, ...] = ()
