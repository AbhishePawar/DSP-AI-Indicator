"""Canonical Research Object models (EPIC-R001).

Immutable aggregate of existing authenticated data + analysis outputs.
No calculations, scoring, valuation, or AI reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Mapping

__all__ = [
    "RESEARCH_OBJECT_SCHEMA_VERSION",
    "RS_SECTION_ORDER",
    "ResearchMetadata",
    "ResearchObject",
    "ResearchSection",
    "ResearchVersion",
    "UNAVAILABLE_MESSAGE",
    "freeze_mapping",
    "utc_now",
]

RESEARCH_OBJECT_SCHEMA_VERSION = "1.0.0"
UNAVAILABLE_MESSAGE = "Data unavailable."

# RS-aligned deterministic section order for the research contract
RS_SECTION_ORDER = (
    "metadata",
    "identity",
    "market_data",
    "financial_statements",
    "corporate_actions",
    "historical_series",
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


def freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    """Deep-freeze a mapping into a read-only MappingProxyType tree."""
    if value is None:
        return None

    def _freeze(obj: Any) -> Any:
        if isinstance(obj, Mapping):
            return MappingProxyType({str(k): _freeze(v) for k, v in obj.items()})
        if isinstance(obj, list):
            return tuple(_freeze(v) for v in obj)
        if isinstance(obj, tuple):
            return tuple(_freeze(v) for v in obj)
        return obj

    return _freeze(value)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class ResearchSection:
    """One RS-aligned section — payload is pass-through only."""

    name: str
    available: bool
    status: str  # ok | unavailable | partial
    source: str  # data_bundle | analysis | request | aggregated | none
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
            "available": self.available,
            "status": self.status,
            "source": self.source,
            "payload": _plain(self.payload) if self.payload is not None else None,
            "provenance": _plain(self.provenance)
            if self.provenance is not None
            else None,
            "message": self.message,
            "retrieved_at": self.retrieved_at,
        }

    @classmethod
    def unavailable(cls, name: str, *, source: str = "none") -> ResearchSection:
        return cls(
            name=name,
            available=False,
            status="unavailable",
            source=source,
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
        source: str,
        payload: Mapping[str, Any] | None,
        provenance: Mapping[str, Any] | None = None,
        retrieved_at: str | None = None,
    ) -> ResearchSection:
        if payload is None:
            return cls.unavailable(name, source=source)
        return cls(
            name=name,
            available=True,
            status="ok",
            source=source,
            payload=freeze_mapping(dict(payload)),
            provenance=freeze_mapping(dict(provenance) if provenance else None),
            message=None,
            retrieved_at=retrieved_at,
        )


@dataclass(frozen=True, slots=True)
class ResearchMetadata:
    research_object_id: str
    schema_version: str
    created_at: str
    research_mode: str
    correlation_id: str | None = None
    ticker: str | None = None
    company: str | None = None
    exchange: str | None = None
    report_version: str | None = None
    pipeline_version: str | None = None
    platform_version: str | None = None
    api_version: str | None = None
    package_versions: Mapping[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "research_object_id": self.research_object_id,
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "research_mode": self.research_mode,
            "correlation_id": self.correlation_id,
            "ticker": self.ticker,
            "company": self.company,
            "exchange": self.exchange,
            "report_version": self.report_version,
            "pipeline_version": self.pipeline_version,
            "platform_version": self.platform_version,
            "api_version": self.api_version,
            "package_versions": dict(self.package_versions),
        }


@dataclass(frozen=True, slots=True)
class ResearchVersion:
    schema_version: str
    object_version: str
    builder_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "object_version": self.object_version,
            "builder_version": self.builder_version,
        }


@dataclass(frozen=True, slots=True)
class ResearchObject:
    """Canonical immutable research contract (RS-001…RS-010 compatible)."""

    metadata: ResearchMetadata
    identity: ResearchSection
    market_data: ResearchSection
    financial_statements: ResearchSection
    corporate_actions: ResearchSection
    historical_series: ResearchSection
    valuation: ResearchSection
    margin_of_safety: ResearchSection
    business_quality: ResearchSection
    risk: ResearchSection
    scenarios: ResearchSection
    recommendation: ResearchSection
    explainability: ResearchSection
    audit: ResearchSection
    provenance: Mapping[str, Any]
    version: ResearchVersion
    data_retrieval: Mapping[str, Any] | None = None
    data_health: Mapping[str, Any] | None = None

    def section(self, name: str) -> ResearchSection:
        mapping = {
            "identity": self.identity,
            "market_data": self.market_data,
            "financial_statements": self.financial_statements,
            "corporate_actions": self.corporate_actions,
            "historical_series": self.historical_series,
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

    def sections(self) -> tuple[ResearchSection, ...]:
        return tuple(self.section(n) for n in RS_SECTION_ORDER if n not in {"metadata"})

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
            "identity": self.identity.to_dict(),
            "market_data": self.market_data.to_dict(),
            "financial_statements": self.financial_statements.to_dict(),
            "corporate_actions": self.corporate_actions.to_dict(),
            "historical_series": self.historical_series.to_dict(),
            "valuation": self.valuation.to_dict(),
            "margin_of_safety": self.margin_of_safety.to_dict(),
            "business_quality": self.business_quality.to_dict(),
            "risk": self.risk.to_dict(),
            "scenarios": self.scenarios.to_dict(),
            "recommendation": self.recommendation.to_dict(),
            "explainability": self.explainability.to_dict(),
            "audit": self.audit.to_dict(),
            "provenance": _plain(self.provenance),
            "data_retrieval": _plain(self.data_retrieval)
            if self.data_retrieval is not None
            else None,
            "data_health": _plain(self.data_health)
            if self.data_health is not None
            else None,
        }
