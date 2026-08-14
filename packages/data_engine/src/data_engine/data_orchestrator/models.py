"""Unified authenticated data models (EPIC-D005).

Aggregation only — no calculations, valuation, scoring, or derived metrics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

__all__ = [
    "DataSectionStatus",
    "RetrievalStatus",
    "SectionResult",
    "UnifiedCompanyIdentity",
    "UnifiedDataBundle",
    "UnifiedHealthReport",
    "utc_now",
]


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True)
class UnifiedCompanyIdentity:
    symbol: str
    exchange: str | None = None
    company_name: str | None = None
    isin: str | None = None
    provider_company_id: str | None = None
    currency: str | None = None
    resolved_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "company_name": self.company_name,
            "isin": self.isin,
            "provider_company_id": self.provider_company_id,
            "currency": self.currency,
            "resolved_by": self.resolved_by,
        }


# Deterministic section order for CV consistency
SECTION_ORDER = (
    "market_quote",
    "financial_statements",
    "corporate_actions",
    "historical_series",
)


@dataclass(frozen=True, slots=True)
class DataSectionStatus:
    """Per-source retrieval outcome — never fabricates payload content."""

    section: str
    available: bool
    authenticated: bool
    status: str  # ok | unavailable | error
    message: str | None
    error: str | None = None
    retrieved_at: str | None = None
    provider_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "section": self.section,
            "available": self.available,
            "authenticated": self.authenticated,
            "status": self.status,
            "message": self.message,
            "error": self.error,
            "retrieved_at": self.retrieved_at,
            "provider_id": self.provider_id,
        }


@dataclass(frozen=True, slots=True)
class SectionResult:
    status: DataSectionStatus
    payload: dict[str, Any] | None
    provenance: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.to_dict(),
            "payload": self.payload,
            "provenance": self.provenance,
        }


@dataclass(frozen=True, slots=True)
class RetrievalStatus:
    """Aggregate retrieval summary across sections."""

    requested_at: str
    completed_at: str
    sections_requested: tuple[str, ...]
    sections_ok: tuple[str, ...]
    sections_unavailable: tuple[str, ...]
    sections_error: tuple[str, ...]
    partial: bool
    all_available: bool
    any_available: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_at": self.requested_at,
            "completed_at": self.completed_at,
            "sections_requested": list(self.sections_requested),
            "sections_ok": list(self.sections_ok),
            "sections_unavailable": list(self.sections_unavailable),
            "sections_error": list(self.sections_error),
            "partial": self.partial,
            "all_available": self.all_available,
            "any_available": self.any_available,
        }


@dataclass(frozen=True, slots=True)
class UnifiedHealthReport:
    overall_ok: bool
    overall_authenticated: bool
    providers: dict[str, dict[str, Any]]
    checked_at: str

    def to_dict(self) -> dict[str, Any]:
        # Deterministic provider key order
        ordered = {k: self.providers[k] for k in sorted(self.providers)}
        return {
            "overall_ok": self.overall_ok,
            "overall_authenticated": self.overall_authenticated,
            "providers": ordered,
            "checked_at": self.checked_at,
        }


@dataclass(frozen=True, slots=True)
class UnifiedDataBundle:
    """Canonical read-only aggregation of authenticated data sources."""

    identity: UnifiedCompanyIdentity
    market_quote: SectionResult
    financial_statements: SectionResult
    corporate_actions: SectionResult
    historical_series: SectionResult
    retrieval: RetrievalStatus
    health: UnifiedHealthReport
    provider_metadata: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "authenticated_gateway": True,
            "identity": self.identity.to_dict(),
            "market_quote": self.market_quote.to_dict(),
            "financial_statements": self.financial_statements.to_dict(),
            "corporate_actions": self.corporate_actions.to_dict(),
            "historical_series": self.historical_series.to_dict(),
            "provider_metadata": {
                k: self.provider_metadata[k] for k in sorted(self.provider_metadata)
            },
            "provenance": {
                section: getattr(self, section).provenance
                for section in SECTION_ORDER
            },
            "health": self.health.to_dict(),
            "retrieval": self.retrieval.to_dict(),
        }
