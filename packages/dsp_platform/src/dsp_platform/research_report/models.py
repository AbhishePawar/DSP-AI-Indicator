"""Public DSP research report contract.

Typed, fail-closed client-facing schema. Not an HTTP route. Not a
ResearchPackage dump. DSP owns numbers; AI owns narrative slots (empty
until a later step populates them).

This contract is intentionally separate from:
    * AnalyseResponse.payload (unbounded dict, production HTTP)
    * PublicDecisionPack (eight-field AI tool-loop pack)
    * InstitutionalResearchReport (ResearchObject RS pass-through)
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal

__all__ = [
    "BUFFETT_METHODOLOGY",
    "CANONICAL_VALUATION_AUTHORITY",
    "FUTURE_VALIDATION_CHECKS",
    "PRIVATE_REPORT_FIELD_NAMES",
    "PUBLIC_RESEARCH_REPORT_SCHEMA_VERSION",
    "SCORE_10_STATUS",
    "AiNarrative",
    "BuffettAnalysisPublic",
    "DspValue",
    "EntryExitPublic",
    "EvidenceRefPublic",
    "ExpectedReturnsPublic",
    "FactorScorecardRow",
    "FinancialsPublic",
    "IdentityPublic",
    "IndustryPublic",
    "PublicMetric",
    "PublicResearchReport",
    "PublicResearchReportError",
    "PUBLIC_TOP_LEVEL_KEYS",
    "QualityFactorPublic",
    "RecommendationPublic",
    "ReportStatus",
    "RiskCategoryPublic",
    "RiskPublic",
    "ScenariosPublic",
    "UnavailableBlock",
    "ValuationMethodPublic",
    "ValuationPublic",
    "ValuationRangePublic",
    "assert_public_report_privacy",
    "empty_ai_narrative",
]

PUBLIC_RESEARCH_REPORT_SCHEMA_VERSION = "dsp.public_research_report.v1"
CANONICAL_VALUATION_AUTHORITY = "compose_intelligence.valuation_signals"
BUFFETT_METHODOLOGY = "existing_pipeline_stages"
SCORE_10_STATUS = "not_implemented"

PUBLIC_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "methodology_version",
        "source_pipeline",
        "research_status",
        "identity",
        "executive_summary",
        "business_quality",
        "economic_moat",
        "management_quality",
        "financial_strength",
        "earnings_quality",
        "growth_quality",
        "factor_scorecard",
        "buffett_analysis",
        "financials",
        "valuation",
        "recommendation",
        "risk",
        "entry_exit",
        "scenarios",
        "expected_returns",
        "industry",
        "evidence",
        "limitations",
    }
)

# Implemented by dsp_platform.research_validation (STEP 4F).
FUTURE_VALIDATION_CHECKS: tuple[str, ...] = (
    "dsp_intrinsic_value_equality",
    "dsp_margin_of_safety_equality",
    "dsp_quality_score_equality",
    "dsp_recommendation_equality",
    "evidence_reference_validity",
    "score_10_remains_not_implemented",
    "entry_exit_remains_not_implemented",
    "scenarios_remain_unavailable",
    "expected_returns_remain_unavailable",
    "private_field_scan",
    "methodology_canary_scan",
)

PRIVATE_REPORT_FIELD_NAMES = frozenset(
    {
        "api_key",
        "api_keys",
        "canary",
        "chain_of_thought",
        "completion_tokens",
        "cost",
        "ai_cost",
        "estimated_cost_usd",
        "input_tokens",
        "internal_prompt",
        "internal_validation",
        "model",
        "model_name",
        "output_tokens",
        "private_prompt",
        "prompt",
        "provider",
        "provider_id",
        "raw_ai_response",
        "research_package",
        "routing",
        "routing_reason",
        "routing_reasons",
        "routing_tier",
        "secret",
        "system_prompt",
        "token_count",
        "tokens",
        "tool_calls",
        "tool_internals",
        "tool_results",
    }
)


class PublicResearchReportError(TypeError):
    """Raised when the public report is built from a non-ResearchPackage."""


class ReportStatus(StrEnum):
    COMPLETE = "complete"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class DspValue:
    """A DSP-owned numeric fact. AI must not overwrite ``value``."""

    value: float | None
    status: str
    source: Literal["dsp"] = "dsp"
    unit: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "status": self.status,
            "source": self.source,
            "unit": self.unit,
        }


@dataclass(frozen=True, slots=True)
class AiNarrative:
    """AI-owned explanation. Empty until a later step supplies text."""

    text: str | None
    status: str
    source: Literal["ai"] = "ai"

    def to_public_dict(self) -> dict[str, Any]:
        return {"text": self.text, "status": self.status, "source": self.source}


def empty_ai_narrative() -> AiNarrative:
    return AiNarrative(text=None, status="unavailable", source="ai")


@dataclass(frozen=True, slots=True)
class EvidenceRefPublic:
    id: str
    kind: str
    label: str

    def to_public_dict(self) -> dict[str, Any]:
        return {"id": self.id, "kind": self.kind, "label": self.label}


@dataclass(frozen=True, slots=True)
class IdentityPublic:
    ticker: str | None
    company_name: str | None
    exchange: str | None
    status: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "exchange": self.exchange,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class QualityFactorPublic:
    name: str
    status: str
    score_100: float | None
    score_10: None
    score_10_status: str
    rating: str | None
    narrative: AiNarrative
    evidence_refs: tuple[EvidenceRefPublic, ...]
    limitations: tuple[str, ...]

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "score_100": self.score_100,
            "score_10": self.score_10,
            "score_10_status": self.score_10_status,
            "rating": self.rating,
            "narrative": self.narrative.to_public_dict(),
            "evidence_refs": [e.to_public_dict() for e in self.evidence_refs],
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class FactorScorecardRow:
    """Future-compatible factor row. score_10 is never calculated here."""

    factor_id: str
    label: str
    status: str
    score_100: float | None
    score_10: None
    score_10_status: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "factor_id": self.factor_id,
            "label": self.label,
            "status": self.status,
            "score_100": self.score_100,
            "score_10": self.score_10,
            "score_10_status": self.score_10_status,
        }


@dataclass(frozen=True, slots=True)
class BuffettAnalysisPublic:
    methodology: str
    authority: str
    status: str
    buffett_overall_score_100: float | None
    buffett_overall_label: str | None
    narrative: AiNarrative
    limitations: tuple[str, ...]

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "methodology": self.methodology,
            "authority": self.authority,
            "status": self.status,
            "buffett_overall_score_100": self.buffett_overall_score_100,
            "buffett_overall_label": self.buffett_overall_label,
            "narrative": self.narrative.to_public_dict(),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class PublicMetric:
    name: str
    value: float | None
    status: str
    source: Literal["dsp"] = "dsp"

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "status": self.status,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class FinancialsPublic:
    status: str
    metrics: tuple[PublicMetric, ...]
    narrative: AiNarrative
    limitations: tuple[str, ...]

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "metrics": [m.to_public_dict() for m in self.metrics],
            "narrative": self.narrative.to_public_dict(),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class ValuationMethodPublic:
    method: str | None
    intrinsic_value: float | None
    applicable: bool | None
    status: str
    source: Literal["dsp"] = "dsp"

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "intrinsic_value": self.intrinsic_value,
            "applicable": self.applicable,
            "status": self.status,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class ValuationRangePublic:
    low: float | None
    mid: float | None
    high: float | None
    status: str
    source: Literal["dsp"] = "dsp"

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "low": self.low,
            "mid": self.mid,
            "high": self.high,
            "status": self.status,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class ValuationPublic:
    authority: str
    status: str
    current_price: DspValue
    intrinsic_value_per_share: DspValue
    valuation_range: ValuationRangePublic
    methods: tuple[ValuationMethodPublic, ...]
    dcf: ValuationMethodPublic
    margin_of_safety: DspValue
    confidence: DspValue
    narrative: AiNarrative
    limitations: tuple[str, ...]

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "authority": self.authority,
            "status": self.status,
            "current_price": self.current_price.to_public_dict(),
            "intrinsic_value_per_share": (
                self.intrinsic_value_per_share.to_public_dict()
            ),
            "valuation_range": self.valuation_range.to_public_dict(),
            "methods": [m.to_public_dict() for m in self.methods],
            "dcf": self.dcf.to_public_dict(),
            "margin_of_safety": self.margin_of_safety.to_public_dict(),
            "confidence": self.confidence.to_public_dict(),
            "narrative": self.narrative.to_public_dict(),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class RecommendationPublic:
    action: str | None
    recommendation_score_100: float | None
    confidence: float | None
    status: str
    canonical_rationale: str | None
    narrative: AiNarrative
    risks: tuple[str, ...]
    limitations: tuple[str, ...]
    source: Literal["dsp"] = "dsp"

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "recommendation_score_100": self.recommendation_score_100,
            "confidence": self.confidence,
            "status": self.status,
            "source": self.source,
            "canonical_rationale": self.canonical_rationale,
            "narrative": self.narrative.to_public_dict(),
            "risks": list(self.risks),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class RiskCategoryPublic:
    category: str
    available: bool
    level: str | None
    status: str
    message: str | None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "available": self.available,
            "level": self.level,
            "status": self.status,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class RiskPublic:
    overall_risk_level: str | None
    status: str
    score_100: None
    score_10: None
    score_10_status: str
    categories: tuple[RiskCategoryPublic, ...]
    narrative: AiNarrative
    limitations: tuple[str, ...]

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "overall_risk_level": self.overall_risk_level,
            "status": self.status,
            "score_100": self.score_100,
            "score_10": self.score_10,
            "score_10_status": self.score_10_status,
            "categories": [c.to_public_dict() for c in self.categories],
            "narrative": self.narrative.to_public_dict(),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class UnavailableBlock:
    status: str
    message: str

    def to_public_dict(self) -> dict[str, Any]:
        return {"status": self.status, "message": self.message}


@dataclass(frozen=True, slots=True)
class EntryExitPublic:
    entry: UnavailableBlock
    exit: UnavailableBlock

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "entry": self.entry.to_public_dict(),
            "exit": self.exit.to_public_dict(),
        }


@dataclass(frozen=True, slots=True)
class ScenariosPublic:
    bear: UnavailableBlock
    base: UnavailableBlock
    bull: UnavailableBlock

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "bear": self.bear.to_public_dict(),
            "base": self.base.to_public_dict(),
            "bull": self.bull.to_public_dict(),
        }


@dataclass(frozen=True, slots=True)
class ExpectedReturnsPublic:
    status: str
    value: None
    message: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "value": self.value,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class IndustryPublic:
    industry: UnavailableBlock
    competitors: UnavailableBlock

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "industry": self.industry.to_public_dict(),
            "competitors": self.competitors.to_public_dict(),
        }


@dataclass(frozen=True, slots=True)
class PublicResearchReport:
    """Client-facing research report. Serialize only via ``to_public_dict``."""

    schema_version: str
    methodology_version: str
    source_pipeline: str
    research_status: str
    identity: IdentityPublic
    executive_summary: AiNarrative
    business_quality: QualityFactorPublic
    economic_moat: QualityFactorPublic
    management_quality: QualityFactorPublic
    financial_strength: QualityFactorPublic
    earnings_quality: QualityFactorPublic
    growth_quality: QualityFactorPublic
    factor_scorecard: tuple[FactorScorecardRow, ...]
    buffett_analysis: BuffettAnalysisPublic
    financials: FinancialsPublic
    valuation: ValuationPublic
    recommendation: RecommendationPublic
    risk: RiskPublic
    entry_exit: EntryExitPublic
    scenarios: ScenariosPublic
    expected_returns: ExpectedReturnsPublic
    industry: IndustryPublic
    evidence: tuple[EvidenceRefPublic, ...]
    limitations: tuple[str, ...]

    def to_public_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "methodology_version": self.methodology_version,
            "source_pipeline": self.source_pipeline,
            "research_status": self.research_status,
            "identity": self.identity.to_public_dict(),
            "executive_summary": self.executive_summary.to_public_dict(),
            "business_quality": self.business_quality.to_public_dict(),
            "economic_moat": self.economic_moat.to_public_dict(),
            "management_quality": self.management_quality.to_public_dict(),
            "financial_strength": self.financial_strength.to_public_dict(),
            "earnings_quality": self.earnings_quality.to_public_dict(),
            "growth_quality": self.growth_quality.to_public_dict(),
            "factor_scorecard": [r.to_public_dict() for r in self.factor_scorecard],
            "buffett_analysis": self.buffett_analysis.to_public_dict(),
            "financials": self.financials.to_public_dict(),
            "valuation": self.valuation.to_public_dict(),
            "recommendation": self.recommendation.to_public_dict(),
            "risk": self.risk.to_public_dict(),
            "entry_exit": self.entry_exit.to_public_dict(),
            "scenarios": self.scenarios.to_public_dict(),
            "expected_returns": self.expected_returns.to_public_dict(),
            "industry": self.industry.to_public_dict(),
            "evidence": [e.to_public_dict() for e in self.evidence],
            "limitations": list(self.limitations),
        }
        assert_public_report_privacy(payload)
        return payload


def assert_public_report_privacy(payload: Mapping[str, Any]) -> None:
    leaked = _find_private_keys(payload)
    if leaked:
        raise ValueError(f"private fields leaked into public report: {leaked}")


def _find_private_keys(obj: Any) -> list[str]:
    found: list[str] = []
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            name = str(key)
            if name in PRIVATE_REPORT_FIELD_NAMES:
                found.append(name)
            found.extend(_find_private_keys(value))
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            found.extend(_find_private_keys(item))
    return found
