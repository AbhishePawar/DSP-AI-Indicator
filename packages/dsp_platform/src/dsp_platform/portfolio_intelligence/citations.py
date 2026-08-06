"""Citations for portfolio intelligence (EPIC-A002)."""

from __future__ import annotations

from typing import Any

from dsp_platform.portfolio_intelligence.linker import ResearchBundle
from dsp_platform.portfolio_intelligence.models import LinkedHolding

__all__ = ["build_portfolio_citations"]


def build_portfolio_citations(
    linked: tuple[LinkedHolding, ...],
    research: dict[str, ResearchBundle],
) -> tuple[dict[str, Any], ...]:
    citations: list[dict[str, Any]] = []
    for holding in linked:
        if not holding.research_linked:
            citations.append(
                {
                    "symbol": holding.symbol,
                    "source_kind": "none",
                    "section": "research",
                    "path": f"holding.{holding.symbol}.research",
                    "available": False,
                    "label": f"{holding.symbol}/research",
                }
            )
            continue
        bundle = research.get(holding.symbol)
        source_kind = (
            "research_object"
            if bundle and bundle.research_object is not None
            else (
                "institutional_report"
                if bundle and bundle.report is not None
                else "archive_snapshot"
            )
        )
        for section in (
            "identity",
            "margin_of_safety",
            "business_quality",
            "risk",
            "recommendation",
        ):
            available = True
            if section == "identity":
                available = holding.sector != "Data unavailable." or holding.research_linked
            elif section == "margin_of_safety":
                available = holding.margin_of_safety != "Data unavailable."
            elif section == "business_quality":
                available = holding.business_quality_available
            elif section == "risk":
                available = holding.risk_available
            elif section == "recommendation":
                available = holding.recommendation_available
            citations.append(
                {
                    "symbol": holding.symbol,
                    "source_kind": source_kind,
                    "section": section,
                    "path": f"{source_kind}.{holding.symbol}.{section}",
                    "available": available,
                    "label": f"{holding.symbol}/{section}",
                    "research_object_id": holding.research_object_id,
                    "report_id": holding.report_id,
                    "snapshot_id": holding.snapshot_id,
                }
            )
    citations.sort(key=lambda c: (c["symbol"], c["section"], c["path"]))
    return tuple(citations)
