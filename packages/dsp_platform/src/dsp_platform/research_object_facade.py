"""Platform façade helpers for ResearchObject (EPIC-R001)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.research_object import (
    RESEARCH_OBJECT_SCHEMA_VERSION,
    build_research_object,
    research_object_from_dict,
    research_object_to_dict,
)

__all__ = [
    "build_canonical_research_object",
    "research_object_schema",
]


def research_object_schema() -> dict[str, Any]:
    """Static schema descriptor for discovery endpoints."""
    return {
        "schema_version": RESEARCH_OBJECT_SCHEMA_VERSION,
        "immutable": True,
        "read_only": True,
        "sources": [
            "unified_data_bundle",
            "analysis_payload",
            "valuation_signals",
        ],
        "sections": [
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
        ],
    }


def build_canonical_research_object(
    symbol: str,
    *,
    data_bundle: Mapping[str, Any] | None = None,
    analysis_payload: Mapping[str, Any] | None = None,
    valuation_signals: Mapping[str, Any] | None = None,
    company: str | None = None,
    exchange: str | None = None,
    correlation_id: str | None = None,
    fetch_data_bundle: bool = False,
    platform_version: str | None = None,
) -> dict[str, Any]:
    """Build and serialize a ResearchObject.

    When ``fetch_data_bundle`` is True and ``data_bundle`` is omitted, fetch via
    the D005 unified gateway (read-only). Analysis must be supplied by the caller
    — this never re-runs engines.
    """
    bundle = data_bundle
    if bundle is None and fetch_data_bundle:
        from dsp_platform.data_orchestrator import get_unified_data_bundle

        bundle = get_unified_data_bundle(symbol, exchange=exchange)

    obj = build_research_object(
        symbol=symbol,
        data_bundle=bundle,
        analysis_payload=analysis_payload,
        valuation_signals=valuation_signals,
        company=company,
        exchange=exchange,
        correlation_id=correlation_id,
        platform_version=platform_version,
    )
    return research_object_to_dict(obj)
