"""Platform façade helpers for Research Monitoring (EPIC-A003)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.research_monitoring import (
    MONITORING_SCHEMA_VERSION,
    MONITORING_SERVICE_VERSION,
    ResearchMonitoringService,
    evaluate_research_monitoring,
    get_monitoring_registry,
)

__all__ = [
    "evaluate_canonical_research_monitoring",
    "register_monitoring_portfolio",
    "register_monitoring_watchlist",
    "research_monitoring_schema",
    "track_monitoring_snapshot",
]


def research_monitoring_schema() -> dict[str, Any]:
    return {
        "schema_version": MONITORING_SCHEMA_VERSION,
        "service_version": MONITORING_SERVICE_VERSION,
        "read_only": True,
        "sources": [
            "research_object",
            "institutional_report",
            "research_archive",
            "research_diff",
            "portfolio_intelligence",
        ],
        "rules": [
            "existing_artifacts_only",
            "no_provider_calls",
            "no_engine_execution",
            "no_valuation",
            "no_scoring",
            "no_optimisation",
            "no_recommendations",
            "no_data_mutation",
            "missing_is_data_unavailable",
        ],
        "severities": ["info", "watch", "important", "unavailable"],
    }


def register_monitoring_watchlist(symbols: list[str]) -> list[str]:
    return list(get_monitoring_registry().register_watchlist(symbols))


def register_monitoring_portfolio(
    portfolio_id: str, *, metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    return get_monitoring_registry().register_portfolio(
        portfolio_id, metadata=metadata
    )


def track_monitoring_snapshot(
    subject: str,
    *,
    subject_kind: str = "symbol",
    baseline_snapshot_id: str | None = None,
    current_snapshot_id: str | None = None,
    tracked_at: str | None = None,
) -> dict[str, Any]:
    return (
        ResearchMonitoringService()
        .track_snapshot(
            subject,
            subject_kind=subject_kind,
            baseline_snapshot_id=baseline_snapshot_id,
            current_snapshot_id=current_snapshot_id,
            tracked_at=tracked_at,
        )
        .to_dict()
    )


def evaluate_canonical_research_monitoring(
    *,
    snapshot_pairs: Mapping[str, Mapping[str, str]] | None = None,
    portfolio_intelligence_baseline: Mapping[str, Any] | None = None,
    portfolio_intelligence_current: Mapping[str, Any] | None = None,
    portfolio_id: str | None = None,
    result_id: str | None = None,
    created_at: str | None = None,
    register_watchlist_symbols: list[str] | None = None,
) -> dict[str, Any]:
    return evaluate_research_monitoring(
        snapshot_pairs=snapshot_pairs,
        portfolio_intelligence_baseline=portfolio_intelligence_baseline,
        portfolio_intelligence_current=portfolio_intelligence_current,
        portfolio_id=portfolio_id,
        result_id=result_id,
        created_at=created_at,
        register_watchlist_symbols=register_watchlist_symbols,
    )
