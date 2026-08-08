"""EPIC-R002 Institutional Research Report tests."""

from __future__ import annotations

from types import MappingProxyType

import pytest

from dsp_platform.institutional_report import (
    REPORT_SCHEMA_VERSION,
    REPORT_SECTION_ORDER,
    InstitutionalReportValidationError,
    generate_institutional_report,
    institutional_report_from_dict,
    institutional_report_to_dict,
    validate_institutional_report,
)
from dsp_platform.research_object import build_research_object, research_object_to_dict

FIXED_TS = "2026-07-28T12:00:00+00:00"
FIXED_RO_ID = "ro-r002-001"
FIXED_REPORT_ID = "rpt-r002-001"


def _sample_bundle() -> dict:
    return {
        "identity": {
            "symbol": "AAPL",
            "ticker": "AAPL",
            "company_name": "Apple Inc",
            "exchange": "NASDAQ",
            "sector": "Technology",
            "industry": "Consumer Electronics",
        },
        "market_quote": {
            "status": {
                "available": True,
                "status": "ok",
                "message": None,
                "retrieved_at": FIXED_TS,
            },
            "payload": {
                "fields": {
                    "current_price": 190.5,
                    "market_cap": 3.0e12,
                    "volume": 50_000_000,
                },
                "currency": "USD",
            },
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
            },
            "payload": None,
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
        "retrieval": {"partial": True, "any_available": True},
        "health": {"overall": "partial"},
    }


def _sample_analysis() -> dict:
    return {
        "ok": True,
        "metadata": {
            "correlation_id": "corr-r002",
            "pipeline_version": "pipe-1",
            "package_versions": {"valuation": "0.12.0"},
        },
        "stage_summaries": [
            {"stage": "valuation", "has_result": True, "summary": "v"},
            {
                "stage": "business_quality_aggregator",
                "has_result": True,
                "summary": "q",
            },
        ],
        "recommendation_summary": {
            "label": "Research Mode",
            "margin_of_safety": 0.25,
            "confidence": "medium",
            "intrinsic_value_per_share": 240.0,
        },
        "risk": {"overall": "moderate"},
        "scenarios": {"base": {"label": "base"}},
    }


def _research_object():
    return build_research_object(
        symbol="AAPL",
        data_bundle=_sample_bundle(),
        analysis_payload=_sample_analysis(),
        object_id=FIXED_RO_ID,
        created_at=FIXED_TS,
        company="Apple Inc",
        exchange="NASDAQ",
    )


def test_generator_projects_rs_sections() -> None:
    report = generate_institutional_report(
        _research_object(),
        report_id=FIXED_REPORT_ID,
        generated_at=FIXED_TS,
    )
    validate_institutional_report(report)
    assert report.metadata.report_id == FIXED_REPORT_ID
    assert report.version.schema_version == REPORT_SCHEMA_VERSION
    assert report.executive_summary.rs_id == "RS-001"
    assert report.market_data.rs_id == "RS-002"
    assert report.audit.rs_id == "RS-010"
    assert report.header.available is True
    assert report.executive_summary.payload["fields"]["ticker"] == "AAPL"
    assert report.market_data.payload["fields"]["current_price"] == 190.5
    assert report.margin_of_safety.available is True
    assert report.financial_statements.available is False
    assert report.financial_statements.message == "Data unavailable."
    assert report.audit.payload["calculation_metadata"] == "Data unavailable."


def test_missing_sections_honest() -> None:
    ro = build_research_object(
        symbol="MSFT",
        object_id=FIXED_RO_ID,
        created_at=FIXED_TS,
    )
    report = generate_institutional_report(
        ro, report_id=FIXED_REPORT_ID, generated_at=FIXED_TS
    )
    assert report.market_data.available is False
    assert report.valuation.available is False
    assert report.risk.message == "Data unavailable."
    assert report.header.payload["fields"]["current_market_price"] == "Data unavailable."
    assert report.executive_summary.available is True  # identity always present


def test_serialization_roundtrip() -> None:
    report = generate_institutional_report(
        _research_object(),
        report_id=FIXED_REPORT_ID,
        generated_at=FIXED_TS,
    )
    raw = institutional_report_to_dict(report)
    restored = institutional_report_from_dict(raw)
    assert institutional_report_to_dict(restored) == raw


def test_determinism() -> None:
    ro = _research_object()
    a = institutional_report_to_dict(
        generate_institutional_report(
            ro, report_id=FIXED_REPORT_ID, generated_at=FIXED_TS
        )
    )
    b = institutional_report_to_dict(
        generate_institutional_report(
            research_object_to_dict(ro),
            report_id=FIXED_REPORT_ID,
            generated_at=FIXED_TS,
        )
    )
    assert a == b


def test_immutability() -> None:
    report = generate_institutional_report(
        _research_object(),
        report_id=FIXED_REPORT_ID,
        generated_at=FIXED_TS,
    )
    with pytest.raises(Exception):
        report.metadata.ticker = "HACK"  # type: ignore[misc]
    assert isinstance(report.executive_summary.payload, MappingProxyType)


def test_validator_rejects_missing_rs() -> None:
    report = generate_institutional_report(
        _research_object(),
        report_id=FIXED_REPORT_ID,
        generated_at=FIXED_TS,
    )
    raw = institutional_report_to_dict(report)
    raw["executive_summary"]["rs_id"] = "WRONG"
    with pytest.raises(InstitutionalReportValidationError):
        institutional_report_from_dict(raw)


def test_section_order() -> None:
    report = generate_institutional_report(
        _research_object(),
        report_id=FIXED_REPORT_ID,
        generated_at=FIXED_TS,
    )
    names = [s.name for s in report.sections()]
    expected = [n for n in REPORT_SECTION_ORDER if n != "metadata"]
    assert names == expected


def test_source_is_research_object_only() -> None:
    report = generate_institutional_report(
        _research_object(),
        report_id=FIXED_REPORT_ID,
        generated_at=FIXED_TS,
    )
    assert report.research_object_ref["research_object_id"] == FIXED_RO_ID
    assert report.research_object_ref["schema_version"] == "1.0.0"
    assert report.metadata.research_object_id == FIXED_RO_ID
