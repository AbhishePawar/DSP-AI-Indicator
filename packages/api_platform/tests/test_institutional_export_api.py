"""EPIC-R003 Institutional Export API tests."""

from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.institutional_report import (
    generate_institutional_report,
    institutional_report_to_dict,
)
from dsp_platform.research_object import build_research_object


@pytest.fixture
def platform() -> DSPPlatform:
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .build()
    )


@pytest.fixture
def client(platform: DSPPlatform) -> TestClient:
    return TestClient(create_app(platform=platform))


def _report_dict() -> dict:
    ro = build_research_object(
        symbol="AAPL",
        object_id="ro-api-exp",
        created_at="2026-07-28T00:00:00+00:00",
        analysis_payload={
            "ok": True,
            "recommendation_summary": {"label": "Research Mode"},
        },
    )
    report = generate_institutional_report(
        ro, report_id="rpt-api-exp", generated_at="2026-07-28T00:00:00+00:00"
    )
    return institutional_report_to_dict(report)


def test_export_schema(client: TestClient) -> None:
    response = client.get("/api/v1/research/export/schema")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["schema"]["source"] == "institutional_report"
    assert "pdf" in body["schema"]["formats"]


def test_export_json(client: TestClient) -> None:
    response = client.post(
        "/api/v1/research/export",
        json={
            "report": _report_dict(),
            "format": "json",
            "export_id": "exp-api-1",
            "exported_at": "2026-07-28T12:00:00+00:00",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["export"]["metadata"]["format"] == "json"
    assert body["export"]["structured_json"]["executive_summary"]["rs_id"] == "RS-001"


def test_export_pdf(client: TestClient) -> None:
    response = client.post(
        "/api/v1/research/export",
        json={"report": _report_dict(), "format": "pdf"},
    )
    assert response.status_code == 200
    raw = base64.b64decode(response.json()["export"]["content_base64"])
    assert raw.startswith(b"%PDF")


def test_export_docx(client: TestClient) -> None:
    response = client.post(
        "/api/v1/research/export",
        json={"report": _report_dict(), "format": "docx"},
    )
    assert response.status_code == 200
    raw = base64.b64decode(response.json()["export"]["content_base64"])
    assert raw[:2] == b"PK"


def test_export_pptx(client: TestClient) -> None:
    response = client.post(
        "/api/v1/research/export",
        json={"report": _report_dict(), "format": "pptx"},
    )
    assert response.status_code == 200
    raw = base64.b64decode(response.json()["export"]["content_base64"])
    assert raw[:2] == b"PK"


def test_export_bad_format(client: TestClient) -> None:
    response = client.post(
        "/api/v1/research/export",
        json={"report": _report_dict(), "format": "txt"},
    )
    assert response.status_code == 400
