"""Typed models for EPIC-001 platform composition."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from financial import FinancialAnalysis, FinancialStatements
from investment_recommendation import ValuationSignals
from valuation import OverallValuationResult

__all__ = [
    "CompositionRequest",
    "ExecutionMetadata",
    "ExecutionTraceEntry",
    "PipelineResult",
    "StageOutcome",
    "StageStatus",
]


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    DEGRADED = "degraded"


@dataclass(frozen=True, slots=True)
class CompositionRequest:
    """Inputs for the internal intelligence composition pipeline.

    Provide ``financial_statements`` and ``current_market_price`` at minimum.
    Optional public artefacts skip or enrich stages without recalculating logic.
    """

    financial_statements: FinancialStatements | None = None
    current_market_price: float | None = None
    financial_analysis: FinancialAnalysis | None = None
    overall_valuation: OverallValuationResult | None = None
    valuation_signals: ValuationSignals | None = None
    financial_snapshot: object | None = None  # contracts.FinancialSnapshot
    market_snapshot: object | None = None  # contracts.MarketSnapshot
    company: str = ""
    ticker: str = ""
    stop_on_stage_failure: bool = False


@dataclass(frozen=True, slots=True)
class ExecutionTraceEntry:
    stage: str
    status: StageStatus
    elapsed_ms: float
    package: str
    package_version: str | None = None
    message: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status.value,
            "elapsed_ms": self.elapsed_ms,
            "package": self.package,
            "package_version": self.package_version,
            "message": self.message,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class StageOutcome:
    stage: str
    status: StageStatus
    result: Any = None
    error: str | None = None
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status.value,
            "error": self.error,
            "warnings": list(self.warnings),
            "has_result": self.result is not None,
        }


@dataclass(frozen=True, slots=True)
class ExecutionMetadata:
    pipeline_version: str
    platform_version: str
    execution_order: tuple[str, ...]
    package_versions: dict[str, str]
    evidence_counts: dict[str, int]
    confidence_summary: dict[str, float | None]
    warnings: tuple[str, ...]
    total_elapsed_ms: float
    ok: bool
    failed_stage: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_version": self.pipeline_version,
            "platform_version": self.platform_version,
            "execution_order": list(self.execution_order),
            "package_versions": dict(self.package_versions),
            "evidence_counts": dict(self.evidence_counts),
            "confidence_summary": dict(self.confidence_summary),
            "warnings": list(self.warnings),
            "total_elapsed_ms": self.total_elapsed_ms,
            "ok": self.ok,
            "failed_stage": self.failed_stage,
        }


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Unified platform composition result — orchestration envelope only."""

    ok: bool
    metadata: ExecutionMetadata
    trace: tuple[ExecutionTraceEntry, ...]
    stages: tuple[StageOutcome, ...]
    financial_analysis: Any = None
    valuation: Any = None  # ValuationSignals | OverallValuationResult | assessment
    valuation_signals: Any = None
    economic_moat: Any = None
    management_quality: Any = None
    financial_strength: Any = None
    earnings_quality: Any = None
    growth_quality: Any = None
    business_quality_analysis: Any = None  # F3 BQ input analysis
    business_quality: Any = None  # aggregator output
    investment_recommendation: Any = None
    investment_committee: Any = None
    limitations: tuple[str, ...] = (
        "Composition orchestrates public package APIs only.",
        "No score/recommendation overrides are applied by the platform.",
        "HTTP exposure is via api_platform DTOs over compose_intelligence only.",
    )
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "metadata": self.metadata.to_dict(),
            "trace": [t.to_dict() for t in self.trace],
            "stages": [s.to_dict() for s in self.stages],
            "has_financial_analysis": self.financial_analysis is not None,
            "has_valuation": self.valuation is not None,
            "has_valuation_signals": self.valuation_signals is not None,
            "has_economic_moat": self.economic_moat is not None,
            "has_management_quality": self.management_quality is not None,
            "has_financial_strength": self.financial_strength is not None,
            "has_earnings_quality": self.earnings_quality is not None,
            "has_growth_quality": self.growth_quality is not None,
            "has_business_quality_analysis": self.business_quality_analysis is not None,
            "has_business_quality": self.business_quality is not None,
            "has_investment_recommendation": self.investment_recommendation is not None,
            "has_investment_committee": self.investment_committee is not None,
            "limitations": list(self.limitations),
            "errors": list(self.errors),
        }
