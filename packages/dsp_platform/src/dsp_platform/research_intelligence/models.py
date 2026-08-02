"""Research Intelligence & Validation models (EPIC-011B).

Measures research quality over time. Never rewrites recommendations or
runs valuation / scoring engines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping

from dsp_platform.research_object.models import UNAVAILABLE_MESSAGE, freeze_mapping

__all__ = [
    "CALIBRATION_BUCKETS",
    "OUTCOME_WINDOWS_MONTHS",
    "RI_SCHEMA_VERSION",
    "RI_SERVICE_VERSION",
    "UNAVAILABLE_MESSAGE",
    "CalibrationReport",
    "OutcomeMeasurement",
    "PerformanceDashboard",
    "ResearchInsightBundle",
    "ResearchSnapshot",
    "freeze_mapping",
    "utc_now",
]

RI_SCHEMA_VERSION = "1.0.0"
RI_SERVICE_VERSION = "1.0.0"
OUTCOME_WINDOWS_MONTHS = (3, 6, 12, 24, 36)
CALIBRATION_BUCKETS = ("high", "medium", "low")


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True)
class ResearchSnapshot:
    """Immutable research recommendation snapshot — append-only registry record."""

    research_id: str
    company: str | None
    exchange: str | None
    sector: str | None
    industry: str | None
    timestamp: str
    recommendation: str | None
    confidence: float | None
    confidence_label: str | None
    intrinsic_value: float | None
    price: float | None
    margin_of_safety: float | None
    business_quality_score: float | None
    management_score: float | None
    moat_score: float | None
    risk_score: float | None
    ai_committee_decision: str | None
    explainability_summary: str | None
    evidence_refs: tuple[str, ...]
    source_confidence: float | None
    research_version: str | None
    model_version: str | None
    content_sha256: str
    symbol: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "research_id": self.research_id,
            "symbol": self.symbol,
            "company": self.company,
            "exchange": self.exchange,
            "sector": self.sector,
            "industry": self.industry,
            "timestamp": self.timestamp,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "confidence_label": self.confidence_label,
            "intrinsic_value": self.intrinsic_value,
            "price": self.price,
            "margin_of_safety": self.margin_of_safety,
            "business_quality_score": self.business_quality_score,
            "management_score": self.management_score,
            "moat_score": self.moat_score,
            "risk_score": self.risk_score,
            "ai_committee_decision": self.ai_committee_decision,
            "explainability_summary": self.explainability_summary,
            "evidence_refs": list(self.evidence_refs),
            "source_confidence": self.source_confidence,
            "research_version": self.research_version,
            "model_version": self.model_version,
            "content_sha256": self.content_sha256,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class OutcomeMeasurement:
    """Outcome measurement for a snapshot at a holding window — measure only."""

    research_id: str
    window_months: int
    measured_at: str
    price_at_research: float | None
    price_at_horizon: float | None
    price_change_pct: float | None
    iv_at_research: float | None
    iv_gap_at_research: float | None
    iv_gap_at_horizon: float | None
    recommendation: str | None
    recommendation_accuracy: str | None
    confidence_label: str | None
    confidence_accuracy: str | None
    mos_at_research: float | None
    mos_performance: str | None
    success_failure: str | None
    availability: Mapping[str, Any]
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "research_id": self.research_id,
            "window_months": self.window_months,
            "measured_at": self.measured_at,
            "price_at_research": self.price_at_research,
            "price_at_horizon": self.price_at_horizon,
            "price_change_pct": self.price_change_pct,
            "iv_at_research": self.iv_at_research,
            "iv_gap_at_research": self.iv_gap_at_research,
            "iv_gap_at_horizon": self.iv_gap_at_horizon,
            "recommendation": self.recommendation,
            "recommendation_accuracy": self.recommendation_accuracy,
            "confidence_label": self.confidence_label,
            "confidence_accuracy": self.confidence_accuracy,
            "mos_at_research": self.mos_at_research,
            "mos_performance": self.mos_performance,
            "success_failure": self.success_failure,
            "availability": dict(self.availability),
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class CalibrationReport:
    result_id: str
    schema_version: str
    service_version: str
    created_at: str
    window_months: int
    bucket_accuracy: Mapping[str, Any]
    calibration_curve: tuple[Mapping[str, Any], ...]
    drift: Mapping[str, Any]
    reliability: Mapping[str, Any]
    sample_size: int
    provenance: Mapping[str, Any]
    limitations: tuple[str, ...] = ()
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "schema_version": self.schema_version,
            "service_version": self.service_version,
            "created_at": self.created_at,
            "window_months": self.window_months,
            "bucket_accuracy": dict(self.bucket_accuracy),
            "calibration_curve": [dict(p) for p in self.calibration_curve],
            "drift": dict(self.drift),
            "reliability": dict(self.reliability),
            "sample_size": self.sample_size,
            "provenance": dict(self.provenance),
            "limitations": list(self.limitations),
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class PerformanceDashboard:
    result_id: str
    schema_version: str
    service_version: str
    created_at: str
    window_months: int
    overall_accuracy: Any
    recommendation_accuracy: Any
    iv_error: Any
    avg_mos: Any
    calibration_summary: Mapping[str, Any]
    bull_success: Any
    bear_success: Any
    false_positives: Any
    false_negatives: Any
    holding_horizon_months: int
    coverage: Mapping[str, Any]
    trends: tuple[Mapping[str, Any], ...]
    provenance: Mapping[str, Any]
    limitations: tuple[str, ...] = ()
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "schema_version": self.schema_version,
            "service_version": self.service_version,
            "created_at": self.created_at,
            "window_months": self.window_months,
            "overall_accuracy": self.overall_accuracy,
            "recommendation_accuracy": self.recommendation_accuracy,
            "iv_error": self.iv_error,
            "avg_mos": self.avg_mos,
            "calibration_summary": dict(self.calibration_summary),
            "bull_success": self.bull_success,
            "bear_success": self.bear_success,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "holding_horizon_months": self.holding_horizon_months,
            "coverage": dict(self.coverage),
            "trends": [dict(t) for t in self.trends],
            "provenance": dict(self.provenance),
            "limitations": list(self.limitations),
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ResearchInsightBundle:
    result_id: str
    schema_version: str
    service_version: str
    created_at: str
    window_months: int
    best_performers: tuple[Mapping[str, Any], ...]
    worst_performers: tuple[Mapping[str, Any], ...]
    coverage_gaps: tuple[Mapping[str, Any], ...]
    sector_performance: tuple[Mapping[str, Any], ...]
    industry_performance: tuple[Mapping[str, Any], ...]
    drift_signals: tuple[Mapping[str, Any], ...]
    provenance: Mapping[str, Any]
    limitations: tuple[str, ...] = ()
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "schema_version": self.schema_version,
            "service_version": self.service_version,
            "created_at": self.created_at,
            "window_months": self.window_months,
            "best_performers": [dict(x) for x in self.best_performers],
            "worst_performers": [dict(x) for x in self.worst_performers],
            "coverage_gaps": [dict(x) for x in self.coverage_gaps],
            "sector_performance": [dict(x) for x in self.sector_performance],
            "industry_performance": [dict(x) for x in self.industry_performance],
            "drift_signals": [dict(x) for x in self.drift_signals],
            "provenance": dict(self.provenance),
            "limitations": list(self.limitations),
            "message": self.message,
        }
