"""Platform façade helpers for Portfolio Intelligence (EPIC-A002)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.portfolio_intelligence import (
    PORTFOLIO_SCHEMA_VERSION,
    PORTFOLIO_SERVICE_VERSION,
    evaluate_portfolio_intelligence,
)

__all__ = [
    "evaluate_canonical_portfolio_intelligence",
    "portfolio_intelligence_schema",
]


def portfolio_intelligence_schema() -> dict[str, Any]:
    return {
        "schema_version": PORTFOLIO_SCHEMA_VERSION,
        "service_version": PORTFOLIO_SERVICE_VERSION,
        "read_only": True,
        "sources": [
            "portfolio_holdings",
            "watchlist",
            "research_object",
            "institutional_report",
            "archive_snapshot",
        ],
        "rules": [
            "research_objects_only",
            "no_provider_calls",
            "no_valuation_calculations",
            "no_scoring_changes",
            "no_optimisation",
            "no_trade_execution",
            "missing_is_data_unavailable",
        ],
    }


def evaluate_canonical_portfolio_intelligence(
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
    return evaluate_portfolio_intelligence(
        portfolio=portfolio,
        watchlist=watchlist,
        research_objects=research_objects,
        reports=reports,
        snapshots=snapshots,
        snapshot_ids=snapshot_ids,
        result_id=result_id,
        created_at=created_at,
    )
