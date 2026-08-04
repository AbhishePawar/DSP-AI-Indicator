"""EPIC-R003 Institutional Export Engine tests."""

from __future__ import annotations

import base64
import zipfile
from io import BytesIO

import pytest

from dsp_platform.institutional_export import (
    EXPORT_SCHEMA_VERSION,
    InstitutionalExportValidationError,
    export_artifact_from_dict,
    export_artifact_to_dict,
    export_institutional_report,
    validate_export_format,
)
from dsp_platform.institutional_report import (
    generate_institutional_report,
    institutional_report_to_dict,
)
from dsp_platform.research_object import build_research_object

FIXED_TS = "2026-07-28T12:00:00+00:00"
FIXED_RO = "ro-r003"
FIXED_RPT = "rpt-r003"
FIXED_EXP = "exp-r003"


def _report():
    ro = build_research_object(
        symbol="AAPL",
        data_bundle={
            "identity": {
                "symbol": "AAPL",
                "ticker": "AAPL",
                "company_name": "Apple Inc",
            },
            "market_quote": {
                "status": {
                    "available": True,
                    "status": "ok",
                    "retrieved_at": FIXED_TS,
                },
                "payload": {"fields": {"current_price": 190.5}},
                "provenance": {"provider_id": "mq"},
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
        },
        analysis_payload={
            "ok": True,
            "recommendation_summary": {
                "label": "Research Mode",
                "margin_of_safety": 0.25,
            },
            "stage_summaries": [
                {"stage": "valuation", "has_result": True, "summary": "v"}
            ],
        },
        object_id=FIXED_RO,
        created_at=FIXED_TS,
    )
    return generate_institutional_report(
        ro, report_id=FIXED_RPT, generated_at=FIXED_TS
    )


def test_json_export_preserves_unavailable() -> None:
    artifact = export_institutional_report(
        _report(), format="json", export_id=FIXED_EXP, exported_at=FIXED_TS
    )
    assert artifact.metadata.format == "json"
    assert artifact.version.schema_version == EXPORT_SCHEMA_VERSION
    assert artifact.structured_json is not None
    assert (
        artifact.structured_json["financial_statements"]["message"]
        == "Data unavailable."
    )
    text = base64.b64decode(artifact.content_base64).decode("utf-8")
    assert "Data unavailable." in text
    assert "190.5" in text


def test_csv_export() -> None:
    artifact = export_institutional_report(
        _report(), format="csv", export_id=FIXED_EXP, exported_at=FIXED_TS
    )
    text = artifact.content_text or ""
    assert text.startswith("section,rs_id,field,value,")
    assert "Data unavailable." in text
    assert "current_price" in text


def test_xlsx_export_is_zip() -> None:
    artifact = export_institutional_report(
        _report(), format="xlsx", export_id=FIXED_EXP, exported_at=FIXED_TS
    )
    raw = base64.b64decode(artifact.content_base64)
    assert raw[:2] == b"PK"
    with zipfile.ZipFile(BytesIO(raw)) as zf:
        names = set(zf.namelist())
        assert "xl/worksheets/sheet1.xml" in names
        sheet = zf.read("xl/worksheets/sheet1.xml").decode("utf-8")
        assert "Data unavailable." in sheet
        assert "current_price" in sheet


def test_pdf_export() -> None:
    artifact = export_institutional_report(
        _report(), format="pdf", export_id=FIXED_EXP, exported_at=FIXED_TS
    )
    raw = base64.b64decode(artifact.content_base64)
    assert raw.startswith(b"%PDF-1.4")
    assert b"%%EOF" in raw
    assert artifact.metadata.content_type == "application/pdf"


def test_determinism() -> None:
    report = institutional_report_to_dict(_report())
    a = export_artifact_to_dict(
        export_institutional_report(
            report, format="json", export_id=FIXED_EXP, exported_at=FIXED_TS
        )
    )
    b = export_artifact_to_dict(
        export_institutional_report(
            report, format="json", export_id=FIXED_EXP, exported_at=FIXED_TS
        )
    )
    assert a == b
    assert a["content_sha256"] == b["content_sha256"]


def test_serialization_roundtrip() -> None:
    artifact = export_institutional_report(
        _report(), format="csv", export_id=FIXED_EXP, exported_at=FIXED_TS
    )
    raw = export_artifact_to_dict(artifact)
    restored = export_artifact_from_dict(raw)
    assert export_artifact_to_dict(restored) == raw


def test_validator_rejects_bad_format() -> None:
    with pytest.raises(InstitutionalExportValidationError):
        validate_export_format("docx")


def test_excel_alias() -> None:
    assert validate_export_format("excel") == "xlsx"
