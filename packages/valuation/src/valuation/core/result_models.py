"""Standardized valuation result models for future aggregation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence

from valuation.core.metadata import RESEARCH_DISCLAIMER, VALUATION_CORE_VERSION
from valuation.core.quality_flags import QualityFlag

__all__ = [
    "ConfidenceLevel",
    "ValidationSummary",
    "ExplainabilityRecord",
    "SensitivityCell",
    "SensitivityMatrix",
    "ScenarioKind",
    "ScenarioOutcome",
    "ValuationMetadata",
    "ValuationResult",
]

ConfidenceLevel = str  # "high" | "medium" | "low"


@dataclass(frozen=True, slots=True)
class ValidationSummary:
    """Reusable validation outcome."""

    ok: bool
    checks: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "checks": list(self.checks),
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class ExplainabilityRecord:
    """One explained field / calculation step."""

    name: str
    value: float | None
    formula: str
    inputs: Mapping[str, Any]
    intermediates: Mapping[str, Any]
    confidence: ConfidenceLevel
    notes: str = ""
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "formula": self.formula,
            "inputs": dict(self.inputs),
            "intermediates": dict(self.intermediates),
            "confidence": self.confidence,
            "notes": self.notes,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class SensitivityCell:
    """One OTAT sensitivity cell (heatmap-ready)."""

    dimension: str
    parameter_value: float
    output_name: str
    output_value: float | None
    row: int = 0
    column: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SensitivityMatrix:
    """Named grids of sensitivity cells."""

    grids: Mapping[str, tuple[SensitivityCell, ...]]
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "grids": {k: [c.to_dict() for c in v] for k, v in self.grids.items()},
            "notes": self.notes,
            "heatmap_ready": True,
        }


@dataclass(frozen=True, slots=True)
class ScenarioKind:
    """Scenario label container (bear/base/bull/custom)."""

    name: str
    label: str

    @staticmethod
    def bear() -> ScenarioKind:
        return ScenarioKind("bear", "Bear")

    @staticmethod
    def base() -> ScenarioKind:
        return ScenarioKind("base", "Base")

    @staticmethod
    def bull() -> ScenarioKind:
        return ScenarioKind("bull", "Bull")

    @staticmethod
    def custom(name: str, label: str | None = None) -> ScenarioKind:
        return ScenarioKind(name, label or name)


@dataclass(frozen=True, slots=True)
class ScenarioOutcome:
    """Result of one scenario evaluation."""

    kind: ScenarioKind
    intrinsic_value: float | None
    equity_value: float | None
    intrinsic_value_per_share: float | None
    notes: str = ""
    extras: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.name,
            "label": self.kind.label,
            "intrinsic_value": self.intrinsic_value,
            "equity_value": self.equity_value,
            "intrinsic_value_per_share": self.intrinsic_value_per_share,
            "notes": self.notes,
            "extras": dict(self.extras),
        }


@dataclass(frozen=True, slots=True)
class ValuationMetadata:
    """Reusable run metadata."""

    model_name: str
    engine_version: str
    methodology: str
    formula_references: tuple[str, ...] = ()
    assumption_summary: Mapping[str, Any] = field(default_factory=dict)
    research_mode: bool = True
    calculation_timestamp: str | None = None
    execution_time_ms: float | None = None
    core_version: str = VALUATION_CORE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "engine_version": self.engine_version,
            "methodology": self.methodology,
            "formula_references": list(self.formula_references),
            "assumption_summary": dict(self.assumption_summary),
            "research_mode": self.research_mode,
            "calculation_timestamp": self.calculation_timestamp,
            "execution_time_ms": self.execution_time_ms,
            "core_version": self.core_version,
        }


@dataclass(frozen=True, slots=True)
class ValuationResult:
    """Standardized valuation result for all future methods.

    Designed for V2.0 aggregation via :meth:`to_aggregate_payload`.
    """

    model_name: str
    version: str
    methodology: str
    intrinsic_value: float | None
    enterprise_value: float | None
    equity_value: float | None
    intrinsic_value_per_share: float | None
    margin_of_safety: float | None
    confidence_score: float
    confidence_level: ConfidenceLevel
    quality_flags: tuple[QualityFlag, ...]
    sensitivity_results: SensitivityMatrix
    scenario_results: tuple[ScenarioOutcome, ...]
    validation_summary: ValidationSummary
    explainability: tuple[ExplainabilityRecord, ...]
    research_disclaimer: str = RESEARCH_DISCLAIMER
    execution_time_ms: float | None = None
    metadata: ValuationMetadata | None = None
    currency: str = "USD"
    confidence_explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary."""
        return {
            "model_name": self.model_name,
            "version": self.version,
            "methodology": self.methodology,
            "intrinsic_value": self.intrinsic_value,
            "enterprise_value": self.enterprise_value,
            "equity_value": self.equity_value,
            "intrinsic_value_per_share": self.intrinsic_value_per_share,
            "margin_of_safety": self.margin_of_safety,
            "confidence_score": self.confidence_score,
            "confidence_level": self.confidence_level,
            "confidence_explanation": self.confidence_explanation,
            "quality_flags": [f.value for f in self.quality_flags],
            "sensitivity_results": self.sensitivity_results.to_dict(),
            "scenario_results": [s.to_dict() for s in self.scenario_results],
            "validation_summary": self.validation_summary.to_dict(),
            "explainability": [e.to_dict() for e in self.explainability],
            "research_disclaimer": self.research_disclaimer,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata.to_dict() if self.metadata else None,
            "currency": self.currency,
        }

    def to_aggregate_payload(self) -> dict[str, Any]:
        """Stable cite payload for future V2.0 valuation aggregation."""
        return {
            "method": self.model_name,
            "module": "valuation.core",
            "version": self.version,
            "currency": self.currency,
            "intrinsic_value": self.intrinsic_value,
            "enterprise_value": self.enterprise_value,
            "equity_value": self.equity_value,
            "intrinsic_value_per_share": self.intrinsic_value_per_share,
            "confidence": self.confidence_level,
            "confidence_score": self.confidence_score,
            "quality_flags": [f.value for f in self.quality_flags],
            "disclaimer": self.research_disclaimer,
        }
