"""Serialize portfolio intelligence results (EPIC-A002)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.portfolio_intelligence.models import (
    PORTFOLIO_SCHEMA_VERSION,
    PORTFOLIO_SERVICE_VERSION,
    LinkedHolding,
    PortfolioIntelligenceResult,
    freeze_mapping,
)
from dsp_platform.portfolio_intelligence.validation import (
    PortfolioIntelligenceValidationError,
    validate_portfolio_intelligence,
)

__all__ = [
    "portfolio_intelligence_from_dict",
    "portfolio_intelligence_to_dict",
]


def portfolio_intelligence_to_dict(
    result: PortfolioIntelligenceResult,
) -> dict[str, Any]:
    validate_portfolio_intelligence(result)
    return result.to_dict()


def portfolio_intelligence_from_dict(
    data: Mapping[str, Any],
) -> PortfolioIntelligenceResult:
    if not isinstance(data, Mapping):
        raise PortfolioIntelligenceValidationError("result must be a mapping")
    linked_raw = data.get("linked_holdings") or []
    linked: list[LinkedHolding] = []
    if isinstance(linked_raw, list):
        for row in linked_raw:
            if not isinstance(row, Mapping):
                continue
            linked.append(
                LinkedHolding(
                    symbol=str(row.get("symbol") or ""),
                    weight=row.get("weight"),
                    research_linked=bool(row.get("research_linked")),
                    research_object_id=row.get("research_object_id"),
                    report_id=row.get("report_id"),
                    snapshot_id=row.get("snapshot_id"),
                    sector=row.get("sector"),
                    industry=row.get("industry"),
                    margin_of_safety=row.get("margin_of_safety"),
                    business_quality_available=bool(
                        row.get("business_quality_available")
                    ),
                    risk_available=bool(row.get("risk_available")),
                    recommendation_available=bool(
                        row.get("recommendation_available")
                    ),
                    message=row.get("message"),
                )
            )
    missing = tuple(data.get("missing_research") or ())
    citations = tuple(data.get("citations") or ())
    limitations = data.get("limitations") or ()
    result = PortfolioIntelligenceResult(
        result_id=str(data.get("result_id") or ""),
        schema_version=str(data.get("schema_version") or PORTFOLIO_SCHEMA_VERSION),
        service_version=str(
            data.get("service_version") or PORTFOLIO_SERVICE_VERSION
        ),
        created_at=str(data.get("created_at") or ""),
        portfolio=freeze_mapping(dict(data["portfolio"]))
        if isinstance(data.get("portfolio"), Mapping)
        else None,
        watchlist=freeze_mapping(dict(data["watchlist"]))
        if isinstance(data.get("watchlist"), Mapping)
        else None,
        linked_holdings=tuple(linked),
        portfolio_summary=freeze_mapping(dict(data.get("portfolio_summary") or {}))
        or freeze_mapping({}),
        diversification_summary=freeze_mapping(
            dict(data.get("diversification_summary") or {})
        )
        or freeze_mapping({}),
        sector_allocation=freeze_mapping(dict(data.get("sector_allocation") or {}))
        or freeze_mapping({}),
        position_concentration=freeze_mapping(
            dict(data.get("position_concentration") or {})
        )
        or freeze_mapping({}),
        portfolio_risk_summary=freeze_mapping(
            dict(data.get("portfolio_risk_summary") or {})
        )
        or freeze_mapping({}),
        margin_of_safety_summary=freeze_mapping(
            dict(data.get("margin_of_safety_summary") or {})
        )
        or freeze_mapping({}),
        quality_summary=freeze_mapping(dict(data.get("quality_summary") or {}))
        or freeze_mapping({}),
        watchlist_summary=freeze_mapping(dict(data.get("watchlist_summary") or {}))
        or freeze_mapping({}),
        missing_research=tuple(
            freeze_mapping(dict(m)) or freeze_mapping({})
            for m in missing
            if isinstance(m, Mapping)
        ),
        citations=tuple(
            freeze_mapping(dict(c)) or freeze_mapping({})
            for c in citations
            if isinstance(c, Mapping)
        ),
        provenance=freeze_mapping(dict(data.get("provenance") or {}))
        or freeze_mapping({}),
        audit=freeze_mapping(dict(data.get("audit") or {})) or freeze_mapping({}),
        limitations=tuple(limitations)
        if isinstance(limitations, (list, tuple))
        else (),
    )
    validate_portfolio_intelligence(result)
    return result
