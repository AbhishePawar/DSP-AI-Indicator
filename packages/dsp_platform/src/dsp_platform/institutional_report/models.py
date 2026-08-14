"""Institutional Research Report models (EPIC-R002).

Immutable report projected from Research Object v1.0.0 only.
No calculations, scoring, valuation, or AI reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Mapping

from dsp_platform.research_object.models import UNAVAILABLE_MESSAGE, freeze_mapping

__all__ = [
    "GENERATOR_VERSION",
    "REPORT_SCHEMA_VERSION",
    "REPORT_SECTION_ORDER",
    "UNAVAILABLE_MESSAGE",
    "InstitutionalResearchReport",
    "ReportMetadata",
    "ReportSection",
    "ReportVersion",
    "freeze_mapping",
    "utc_now",
]

REPORT_SCHEMA_VERSION = "1.0.0"
GENERATOR_VERSION = "1.0.0"

# Deterministic RS-aligned section order (header first per RESEARCH_STANDARDS)
REPORT_SECTION_ORDER = (
    "metadata",
    "header",
    "executive_summary",
    "market_data",
    "financial_statements",
    "corporate_actions",
    "historical_summary",
    "valuation",
    "margin_of_safety",
    "business_quality",
    "risk",
    "scenarios",
    "recommendation",
    "explainability",
    "audit",
)


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True)
class ReportSection:
    """One report section — content is pass-through / field-extract only."""

    name: str
    rs_id: str | None
    available: bool
    status: str  # ok | unavailable | partial
    source_section: str  # research object section name(s)
    payload: Mapping[str, Any] | None
    provenance: Mapping[str, Any] | None = None
    message: str | None = None
    retrieved_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        def _plain(obj: Any) -> Any:
            if isinstance(obj, Mapping):
                return {str(k): _plain(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_plain(v) for v in obj]
            return obj

        return {
            "name": self.name,
            "rs_id": self.rs_id,
            "available": self.available,
            "status": self.status,
            "source_section": self.source_section,
            "payload": _plain(self.payload) if self.payload is not None else None,
            "provenance": _plain(self.provenance)
            if self.provenance is not None
            else None,
            "message": self.message,
            "retrieved_at": self.retrieved_at,
        }

    @classmethod
    def unavailable(
        cls,
        name: str,
        *,
        rs_id: str | None = None,
        source_section: str = "research_object",
    ) -> ReportSection:
        return cls(
            name=name,
            rs_id=rs_id,
            available=False,
            status="unavailable",
            source_section=source_section,
            payload=None,
            provenance=None,
            message=UNAVAILABLE_MESSAGE,
            retrieved_at=None,
        )

    @classmethod
    def from_payload(
        cls,
        name: str,
        *,
        rs_id: str | None,
        source_section: str,
        payload: Mapping[str, Any] | None,
        provenance: Mapping[str, Any] | None = None,
        retrieved_at: str | None = None,
        status: str = "ok",
    ) -> ReportSection:
        if payload is None:
            return cls.unavailable(
                name, rs_id=rs_id, source_section=source_section
            )
        return cls(
            name=name,
            rs_id=rs_id,
            available=True,
            status=status,
            source_section=source_section,
            payload=freeze_mapping(dict(payload)),
            provenance=freeze_mapping(dict(provenance) if provenance else None),
            message=None,
            retrieved_at=retrieved_at,
        )


@dataclass(frozen=True, slots=True)
class ReportMetadata:
    report_id: str
    schema_version: str
    generated_at: str
    research_object_id: str
    research_object_schema_version: str
    research_mode: str
    correlation_id: str | None = None
    ticker: str | None = None
    company: str | None = None
    exchange: str | None = None
    generator_version: str = GENERATOR_VERSION
    api_version: str | None = "v1"
    package_versions: Mapping[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "research_object_id": self.research_object_id,
            "research_object_schema_version": self.research_object_schema_version,
            "research_mode": self.research_mode,
            "correlation_id": self.correlation_id,
            "ticker": self.ticker,
            "company": self.company,
            "exchange": self.exchange,
            "generator_version": self.generator_version,
            "api_version": self.api_version,
            "package_versions": dict(self.package_versions),
        }


@dataclass(frozen=True, slots=True)
class ReportVersion:
    schema_version: str
    report_version: str
    generator_version: str
    research_object_schema_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "report_version": self.report_version,
            "generator_version": self.generator_version,
            "research_object_schema_version": self.research_object_schema_version,
        }


@dataclass(frozen=True, slots=True)
class InstitutionalResearchReport:
    """Canonical institutional research report (RS-001…RS-010)."""

    metadata: ReportMetadata
    header: ReportSection
    executive_summary: ReportSection
    market_data: ReportSection
    financial_statements: ReportSection
    corporate_actions: ReportSection
    historical_summary: ReportSection
    valuation: ReportSection
    margin_of_safety: ReportSection
    business_quality: ReportSection
    risk: ReportSection
    scenarios: ReportSection
    recommendation: ReportSection
    explainability: ReportSection
    audit: ReportSection
    provenance: Mapping[str, Any]
    version: ReportVersion
    research_object_ref: Mapping[str, Any]

    def section(self, name: str) -> ReportSection:
        mapping = {
            "header": self.header,
            "executive_summary": self.executive_summary,
            "market_data": self.market_data,
            "financial_statements": self.financial_statements,
            "corporate_actions": self.corporate_actions,
            "historical_summary": self.historical_summary,
            "valuation": self.valuation,
            "margin_of_safety": self.margin_of_safety,
            "business_quality": self.business_quality,
            "risk": self.risk,
            "scenarios": self.scenarios,
            "recommendation": self.recommendation,
            "explainability": self.explainability,
            "audit": self.audit,
        }
        if name not in mapping:
            raise KeyError(name)
        return mapping[name]

    def sections(self) -> tuple[ReportSection, ...]:
        return tuple(
            self.section(n) for n in REPORT_SECTION_ORDER if n not in {"metadata"}
        )

    def to_dict(self) -> dict[str, Any]:
        def _plain(obj: Any) -> Any:
            if isinstance(obj, Mapping):
                return {str(k): _plain(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_plain(v) for v in obj]
            return obj

        return {
            "schema_version": self.version.schema_version,
            "version": self.version.to_dict(),
            "metadata": self.metadata.to_dict(),
            "header": self.header.to_dict(),
            "executive_summary": self.executive_summary.to_dict(),
            "market_data": self.market_data.to_dict(),
            "financial_statements": self.financial_statements.to_dict(),
            "corporate_actions": self.corporate_actions.to_dict(),
            "historical_summary": self.historical_summary.to_dict(),
            "valuation": self.valuation.to_dict(),
            "margin_of_safety": self.margin_of_safety.to_dict(),
            "business_quality": self.business_quality.to_dict(),
            "risk": self.risk.to_dict(),
            "scenarios": self.scenarios.to_dict(),
            "recommendation": self.recommendation.to_dict(),
            "explainability": self.explainability.to_dict(),
            "audit": self.audit.to_dict(),
            "provenance": _plain(self.provenance),
            "research_object_ref": _plain(self.research_object_ref),
        }
