"""EPIC-R001 Research Object unit + integration tests."""

from __future__ import annotations

from types import MappingProxyType

import pytest

from dsp_platform.research_object import (
    RESEARCH_OBJECT_SCHEMA_VERSION,
    RS_SECTION_ORDER,
    ResearchObjectValidationError,
    build_research_object,
    research_object_from_dict,
    research_object_to_dict,
    validate_research_object,
)


FIXED_TS = "2026-07-28T12:00:00+00:00"
FIXED_ID = "ro-test-001"


def _sample_bundle() -> dict:
    return {
        "identity": {
            "symbol": "AAPL",
            "ticker": "AAPL",
            "company_name": "Apple Inc",
            "exchange": "NASDAQ",
            "resolved_by": "request",
        },
        "market_quote": {
            "status": {
                "available": True,
                "status": "ok",
                "message": None,
                "retrieved_at": FIXED_TS,
            },
            "payload": {"current_price": 190.5, "currency": "USD"},
            "provenance": {
                "provider_id": "mq",
                "source_type": "licensed_vendor",
                "retrieved_at": FIXED_TS,
            },
        },
        "financial_statements": {
            "status": {
                "available": False,
                "status": "unavailable",
                "message": "Data unavailable.",
                "retrieved_at": None,
            },
            "payload": None,
            "provenance": None,
        },
        "corporate_actions": {
            "status": {
                "available": False,
                "status": "unavailable",
                "message": "Data unavailable.",
            },
            "payload": None,
        },
        "historical_series": {
            "status": {
                "available": False,
                "status": "unavailable",
                "message": "Data unavailable.",
            },
            "payload": None,
        },
        "retrieval": {
            "partial": True,
            "any_available": True,
            "sections_ok": ["market_quote"],
        },
        "health": {"overall": "partial"},
        "provenance": {"bundle": "d005"},
    }


def _sample_analysis() -> dict:
    return {
        "ok": True,
        "metadata": {
            "correlation_id": "corr-1",
            "pipeline_version": "pipe-1",
            "package_versions": {"valuation": "0.12.0"},
        },
        "stage_summaries": [
            {
                "stage": "valuation",
                "has_result": True,
                "summary": "pass-through valuation summary",
            },
            {
                "stage": "business_quality_aggregator",
                "has_result": True,
                "summary": "pass-through quality summary",
            },
        ],
        "recommendation_summary": {
            "label": "Research Mode",
            "margin_of_safety": 0.25,
            "confidence": "medium",
        },
        "risk": {"overall": "moderate", "notes": "from analysis"},
        "scenarios": {"base": {"label": "base"}},
    }


def test_builder_aggregates_sections() -> None:
    obj = build_research_object(
        symbol="aapl",
        data_bundle=_sample_bundle(),
        analysis_payload=_sample_analysis(),
        object_id=FIXED_ID,
        created_at=FIXED_TS,
    )
    validate_research_object(obj)
    assert obj.metadata.research_object_id == FIXED_ID
    assert obj.metadata.schema_version == RESEARCH_OBJECT_SCHEMA_VERSION
    assert obj.identity.available is True
    assert obj.market_data.available is True
    assert obj.market_data.payload["current_price"] == 190.5
    assert obj.financial_statements.available is False
    assert obj.financial_statements.message == "Data unavailable."
    assert obj.valuation.available is True
    assert obj.margin_of_safety.available is True
    assert obj.margin_of_safety.payload["margin_of_safety"] == 0.25
    assert obj.business_quality.available is True
    assert obj.risk.available is True
    assert obj.scenarios.available is True
    assert obj.recommendation.available is True
    assert obj.explainability.available is True
    assert obj.audit.available is True


def test_builder_without_sources_marks_unavailable() -> None:
    obj = build_research_object(
        symbol="MSFT",
        object_id=FIXED_ID,
        created_at=FIXED_TS,
    )
    assert obj.market_data.available is False
    assert obj.valuation.available is False
    assert obj.risk.message == "Data unavailable."
    assert obj.recommendation.available is False


def test_validator_rejects_bad_status() -> None:
    obj = build_research_object(
        symbol="X",
        object_id=FIXED_ID,
        created_at=FIXED_TS,
    )
    # Mutate via object.__setattr__ bypass is blocked by frozen; rebuild invalid via from_dict
    raw = research_object_to_dict(obj)
    raw["market_data"]["status"] = "invented"
    with pytest.raises(ResearchObjectValidationError):
        research_object_from_dict(raw)


def test_serialization_roundtrip() -> None:
    obj = build_research_object(
        symbol="AAPL",
        data_bundle=_sample_bundle(),
        analysis_payload=_sample_analysis(),
        object_id=FIXED_ID,
        created_at=FIXED_TS,
    )
    raw = research_object_to_dict(obj)
    restored = research_object_from_dict(raw)
    assert research_object_to_dict(restored) == raw


def test_immutability() -> None:
    obj = build_research_object(
        symbol="AAPL",
        data_bundle=_sample_bundle(),
        object_id=FIXED_ID,
        created_at=FIXED_TS,
    )
    with pytest.raises(Exception):
        obj.metadata.ticker = "HACK"  # type: ignore[misc]
    assert isinstance(obj.market_data.payload, MappingProxyType)
    with pytest.raises(TypeError):
        obj.market_data.payload["current_price"] = 1  # type: ignore[index]


def test_determinism() -> None:
    kwargs = dict(
        symbol="AAPL",
        data_bundle=_sample_bundle(),
        analysis_payload=_sample_analysis(),
        object_id=FIXED_ID,
        created_at=FIXED_TS,
        correlation_id="corr-1",
    )
    a = research_object_to_dict(build_research_object(**kwargs))
    b = research_object_to_dict(build_research_object(**kwargs))
    assert a == b


def test_rs_section_order_coverage() -> None:
    obj = build_research_object(
        symbol="AAPL",
        object_id=FIXED_ID,
        created_at=FIXED_TS,
    )
    names = [s.name for s in obj.sections()]
    expected = [n for n in RS_SECTION_ORDER if n != "metadata"]
    assert names == expected


def test_no_fabrication_when_partial_bundle() -> None:
    obj = build_research_object(
        symbol="AAPL",
        data_bundle=_sample_bundle(),
        object_id=FIXED_ID,
        created_at=FIXED_TS,
    )
    assert obj.financial_statements.payload is None
    assert obj.corporate_actions.message == "Data unavailable."


def test_valuation_signals_passthrough() -> None:
    obj = build_research_object(
        symbol="AAPL",
        valuation_signals={
            "margin_of_safety": 0.1,
            "intrinsic_value_per_share": 200.0,
            "current_market_price": 180.0,
        },
        object_id=FIXED_ID,
        created_at=FIXED_TS,
    )
    assert obj.valuation.available is True
    assert obj.valuation.source == "request"
    assert obj.margin_of_safety.payload["margin_of_safety"] == 0.1
