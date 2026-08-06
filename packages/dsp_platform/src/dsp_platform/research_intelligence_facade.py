"""Platform façade helpers for Research Intelligence (EPIC-011B)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.research_intelligence import (
    RI_SCHEMA_VERSION,
    RI_SERVICE_VERSION,
    ResearchIntelligenceService,
    get_research_intelligence_service,
)

__all__ = [
    "capture_canonical_research_snapshot",
    "research_intelligence_calibration",
    "research_intelligence_insights",
    "research_intelligence_list_snapshots",
    "research_intelligence_measure",
    "research_intelligence_measure_batch",
    "research_intelligence_performance",
    "research_intelligence_schema",
    "research_intelligence_timeline",
]


def research_intelligence_schema() -> dict[str, Any]:
    return get_research_intelligence_service().schema()


def capture_canonical_research_snapshot(
    payload: Mapping[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    return get_research_intelligence_service().capture_from_payload(payload, **kwargs)


def research_intelligence_list_snapshots(**kwargs: Any) -> dict[str, Any]:
    return get_research_intelligence_service().list_snapshots(**kwargs)


def research_intelligence_timeline(**kwargs: Any) -> dict[str, Any]:
    return get_research_intelligence_service().timeline(**kwargs)


def research_intelligence_measure(**kwargs: Any) -> dict[str, Any]:
    return get_research_intelligence_service().measure(**kwargs)


def research_intelligence_measure_batch(**kwargs: Any) -> dict[str, Any]:
    return get_research_intelligence_service().measure_batch(**kwargs)


def research_intelligence_calibration(**kwargs: Any) -> dict[str, Any]:
    return get_research_intelligence_service().calibration(**kwargs)


def research_intelligence_performance(**kwargs: Any) -> dict[str, Any]:
    return get_research_intelligence_service().performance_dashboard(**kwargs)


def research_intelligence_insights(**kwargs: Any) -> dict[str, Any]:
    return get_research_intelligence_service().insights(**kwargs)


def bind_research_intelligence_service(
    service: ResearchIntelligenceService,
) -> ResearchIntelligenceService:
    """Test/helper: replace process registry with a provided service."""
    from dsp_platform.research_intelligence import reset_research_intelligence_for_tests

    reset_research_intelligence_for_tests(service)
    return service


# silence unused version exports for importers that introspect module attrs
_ = (RI_SCHEMA_VERSION, RI_SERVICE_VERSION)
