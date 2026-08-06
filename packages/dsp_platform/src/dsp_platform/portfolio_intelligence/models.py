"""Portfolio Intelligence models (EPIC-A002).

Read-only summaries of portfolios/watchlists linked to Research Objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping

from dsp_platform.research_object.models import UNAVAILABLE_MESSAGE, freeze_mapping

__all__ = [
    "PORTFOLIO_SCHEMA_VERSION",
    "PORTFOLIO_SERVICE_VERSION",
    "UNAVAILABLE_MESSAGE",
    "Holding",
    "LinkedHolding",
    "Portfolio",
    "PortfolioIntelligenceResult",
    "Watchlist",
    "freeze_mapping",
    "utc_now",
]

PORTFOLIO_SCHEMA_VERSION = "1.0.0"
PORTFOLIO_SERVICE_VERSION = "1.0.0"


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True)
class Holding:
    symbol: str
    weight: float | None = None
    shares: float | None = None
    labels: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "weight": self.weight,
            "shares": self.shares,
            "labels": dict(self.labels),
        }


@dataclass(frozen=True, slots=True)
class Portfolio:
    portfolio_id: str
    name: str | None
    holdings: tuple[Holding, ...]
    created_at: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "name": self.name,
            "holdings": [h.to_dict() for h in self.holdings],
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class Watchlist:
    watchlist_id: str
    name: str | None
    symbols: tuple[str, ...]
    created_at: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "watchlist_id": self.watchlist_id,
            "name": self.name,
            "symbols": list(self.symbols),
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class LinkedHolding:
    symbol: str
    weight: float | None
    research_linked: bool
    research_object_id: str | None
    report_id: str | None
    snapshot_id: str | None
    sector: Any
    industry: Any
    margin_of_safety: Any
    business_quality_available: bool
    risk_available: bool
    recommendation_available: bool
    message: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "weight": self.weight,
            "research_linked": self.research_linked,
            "research_object_id": self.research_object_id,
            "report_id": self.report_id,
            "snapshot_id": self.snapshot_id,
            "sector": self.sector,
            "industry": self.industry,
            "margin_of_safety": self.margin_of_safety,
            "business_quality_available": self.business_quality_available,
            "risk_available": self.risk_available,
            "recommendation_available": self.recommendation_available,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class PortfolioIntelligenceResult:
    result_id: str
    schema_version: str
    service_version: str
    created_at: str
    portfolio: Mapping[str, Any] | None
    watchlist: Mapping[str, Any] | None
    linked_holdings: tuple[LinkedHolding, ...]
    portfolio_summary: Mapping[str, Any]
    diversification_summary: Mapping[str, Any]
    sector_allocation: Mapping[str, Any]
    position_concentration: Mapping[str, Any]
    portfolio_risk_summary: Mapping[str, Any]
    margin_of_safety_summary: Mapping[str, Any]
    quality_summary: Mapping[str, Any]
    watchlist_summary: Mapping[str, Any]
    missing_research: tuple[Mapping[str, Any], ...]
    citations: tuple[Mapping[str, Any], ...]
    provenance: Mapping[str, Any]
    audit: Mapping[str, Any]
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        def _plain(obj: Any) -> Any:
            if isinstance(obj, Mapping):
                return {str(k): _plain(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_plain(v) for v in obj]
            return obj

        return {
            "result_id": self.result_id,
            "schema_version": self.schema_version,
            "service_version": self.service_version,
            "created_at": self.created_at,
            "portfolio": _plain(self.portfolio),
            "watchlist": _plain(self.watchlist),
            "linked_holdings": [h.to_dict() for h in self.linked_holdings],
            "portfolio_summary": _plain(self.portfolio_summary),
            "diversification_summary": _plain(self.diversification_summary),
            "sector_allocation": _plain(self.sector_allocation),
            "position_concentration": _plain(self.position_concentration),
            "portfolio_risk_summary": _plain(self.portfolio_risk_summary),
            "margin_of_safety_summary": _plain(self.margin_of_safety_summary),
            "quality_summary": _plain(self.quality_summary),
            "watchlist_summary": _plain(self.watchlist_summary),
            "missing_research": [_plain(m) for m in self.missing_research],
            "citations": [_plain(c) for c in self.citations],
            "provenance": _plain(self.provenance),
            "audit": _plain(self.audit),
            "limitations": list(self.limitations),
        }
