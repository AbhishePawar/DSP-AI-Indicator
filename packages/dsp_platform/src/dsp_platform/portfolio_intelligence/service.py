"""Portfolio Intelligence service (EPIC-A002).

Summarizes portfolios/watchlists using linked Research Objects only.
"""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from dsp_platform.portfolio_intelligence.citations import build_portfolio_citations
from dsp_platform.portfolio_intelligence.linker import link_research_map
from dsp_platform.portfolio_intelligence.loader import load_portfolio, load_watchlist
from dsp_platform.portfolio_intelligence.models import (
    PORTFOLIO_SCHEMA_VERSION,
    PORTFOLIO_SERVICE_VERSION,
    PortfolioIntelligenceResult,
    freeze_mapping,
    utc_now,
)
from dsp_platform.portfolio_intelligence.serde import portfolio_intelligence_to_dict
from dsp_platform.portfolio_intelligence.summaries import (
    build_linked_holdings,
    build_summaries,
)
from dsp_platform.portfolio_intelligence.validation import validate_portfolio_intelligence

__all__ = [
    "PORTFOLIO_SERVICE_VERSION",
    "PortfolioIntelligenceService",
    "evaluate_portfolio_intelligence",
]


class PortfolioIntelligenceService:
    def evaluate(
        self,
        *,
        portfolio: Mapping[str, Any] | None = None,
        watchlist: Mapping[str, Any] | None = None,
        research_objects: Mapping[str, Any] | list[Any] | None = None,
        reports: Mapping[str, Any] | list[Any] | None = None,
        snapshots: Mapping[str, Any] | list[Any] | None = None,
        snapshot_ids: Mapping[str, str] | None = None,
        result_id: str | None = None,
        created_at: str | None = None,
    ) -> PortfolioIntelligenceResult:
        port = load_portfolio(portfolio)
        watch = load_watchlist(watchlist)
        if port is None and watch is None:
            raise ValueError("portfolio or watchlist is required")

        research = link_research_map(
            research_objects=research_objects,
            reports=reports,
            snapshots=snapshots,
            snapshot_ids=snapshot_ids,
        )

        holdings = port.holdings if port else ()
        linked_portfolio = build_linked_holdings(holdings, research)
        summaries = build_summaries(
            portfolio=port,
            watchlist=watch,
            linked=linked_portfolio,
            research=research,
        )
        citations = build_portfolio_citations(linked_portfolio, research)
        # Add watchlist-only missing citations
        if watch:
            port_symbols = {h.symbol for h in holdings}
            for sym in watch.symbols:
                if sym in port_symbols:
                    continue
                bundle = research.get(sym)
                linked = bool(
                    bundle
                    and (
                        bundle.research_object is not None
                        or bundle.report is not None
                        or bundle.snapshot is not None
                    )
                )
                citations = citations + (
                    {
                        "symbol": sym,
                        "source_kind": "watchlist",
                        "section": "research",
                        "path": f"watchlist.{sym}.research",
                        "available": linked,
                        "label": f"watchlist/{sym}",
                    },
                )

        created = created_at or utc_now().isoformat()
        rid = result_id or str(uuid.uuid4())
        provenance = {
            "source": "portfolio_intelligence",
            "service_version": PORTFOLIO_SERVICE_VERSION,
            "providers_called": False,
            "engines_called": False,
            "research_symbols": sorted(research.keys()),
        }
        audit = {
            "result_id": rid,
            "created_at": created,
            "portfolio_id": port.portfolio_id if port else None,
            "watchlist_id": watch.watchlist_id if watch else None,
            "holding_count": len(holdings),
            "citation_count": len(citations),
            "missing_research_count": len(summaries["missing_research"]),
        }
        limitations = (
            "Summarizes caller-provided holdings/watchlist linked to existing research only.",
            "No valuation, scoring, optimisation, or trade generation.",
            "No market/fundamental providers consulted.",
        )

        result = PortfolioIntelligenceResult(
            result_id=rid,
            schema_version=PORTFOLIO_SCHEMA_VERSION,
            service_version=PORTFOLIO_SERVICE_VERSION,
            created_at=created,
            portfolio=freeze_mapping(port.to_dict()) if port else None,
            watchlist=freeze_mapping(watch.to_dict()) if watch else None,
            linked_holdings=linked_portfolio,
            portfolio_summary=freeze_mapping(summaries["portfolio_summary"])
            or freeze_mapping({}),
            diversification_summary=freeze_mapping(
                summaries["diversification_summary"]
            )
            or freeze_mapping({}),
            sector_allocation=freeze_mapping(summaries["sector_allocation"])
            or freeze_mapping({}),
            position_concentration=freeze_mapping(
                summaries["position_concentration"]
            )
            or freeze_mapping({}),
            portfolio_risk_summary=freeze_mapping(
                summaries["portfolio_risk_summary"]
            )
            or freeze_mapping({}),
            margin_of_safety_summary=freeze_mapping(
                summaries["margin_of_safety_summary"]
            )
            or freeze_mapping({}),
            quality_summary=freeze_mapping(summaries["quality_summary"])
            or freeze_mapping({}),
            watchlist_summary=freeze_mapping(summaries["watchlist_summary"])
            or freeze_mapping({}),
            missing_research=tuple(
                freeze_mapping(dict(m)) or freeze_mapping({})
                for m in summaries["missing_research"]
            ),
            citations=tuple(
                freeze_mapping(dict(c)) or freeze_mapping({}) for c in citations
            ),
            provenance=freeze_mapping(provenance) or freeze_mapping({}),
            audit=freeze_mapping(audit) or freeze_mapping({}),
            limitations=limitations,
        )
        validate_portfolio_intelligence(result)
        return result


def evaluate_portfolio_intelligence(
    *,
    portfolio: Mapping[str, Any] | None = None,
    watchlist: Mapping[str, Any] | None = None,
    research_objects: Mapping[str, Any] | list[Any] | None = None,
    reports: Mapping[str, Any] | list[Any] | None = None,
    snapshots: Mapping[str, Any] | list[Any] | None = None,
    snapshot_ids: Mapping[str, str] | None = None,
    result_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    result = PortfolioIntelligenceService().evaluate(
        portfolio=portfolio,
        watchlist=watchlist,
        research_objects=research_objects,
        reports=reports,
        snapshots=snapshots,
        snapshot_ids=snapshot_ids,
        result_id=result_id,
        created_at=created_at,
    )
    return portfolio_intelligence_to_dict(result)
