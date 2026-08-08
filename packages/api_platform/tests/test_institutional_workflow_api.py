"""EPIC-A007 Institutional Workflow API tests + A006 regression."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.institutional_workflow import reset_workflow_registry_for_tests

FIXED = "2026-07-28T12:00:00+00:00"


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_workflow_registry_for_tests()
    yield
    reset_workflow_registry_for_tests()


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


def test_schema_and_templates(client: TestClient) -> None:
    schema = client.get("/api/v1/workflow/schema")
    assert schema.status_code == 200
    body = schema.json()
    assert body["ok"] is True
    assert "no_research_mutation" in body["schema"]["rules"]
    assert "draft" in body["schema"]["stages"]
    assert "assign_reviewer" in body["schema"]["actions"]

    templates = client.get("/api/v1/workflow/templates")
    assert templates.status_code == 200
    assert templates.json()["templates"][0]["template_id"]


def test_lifecycle_via_api(client: TestClient) -> None:
    create = client.post(
        "/api/v1/workflow/action",
        json={
            "action": "create",
            "subject": "AAPL",
            "workflow_id": "wf-api-1",
            "artifact_refs": {
                "research_object_id": "ro-api",
                "report_id": "rpt-api",
            },
            "result_id": "res-api-c",
            "created_at": FIXED,
        },
    )
    assert create.status_code == 200
    assert create.json()["result"]["workflow"]["stage"] == "draft"
    assert create.json()["result"]["provenance"]["research_mutated"] is False

    transition = client.post(
        "/api/v1/workflow/action",
        json={
            "action": "transition",
            "workflow_id": "wf-api-1",
            "to_stage": "review",
            "actor_id": "analyst-1",
            "approval_id": "ap-api-1",
            "event_id": "ev-api-1",
            "result_id": "res-api-t",
            "created_at": FIXED,
        },
    )
    assert transition.status_code == 200
    assert transition.json()["result"]["workflow"]["stage"] == "review"


def test_assign_and_history_api(client: TestClient) -> None:
    client.post(
        "/api/v1/workflow/action",
        json={
            "action": "create",
            "subject": "MSFT",
            "workflow_id": "wf-api-2",
            "result_id": "res-api2-c",
            "created_at": FIXED,
        },
    )
    assign = client.post(
        "/api/v1/workflow/action",
        json={
            "action": "assign_reviewer",
            "workflow_id": "wf-api-2",
            "reviewer_id": "rev-1",
            "role": "reviewer",
            "actor_id": "admin",
            "result_id": "res-api2-a",
            "created_at": FIXED,
        },
    )
    assert assign.status_code == 200
    assert any(
        r["reviewer_id"] == "rev-1"
        for r in assign.json()["result"]["workflow"]["reviewers"]
    )
    hist = client.post(
        "/api/v1/workflow/action",
        json={
            "action": "history",
            "workflow_id": "wf-api-2",
            "result_id": "res-api2-h",
            "created_at": FIXED,
        },
    )
    assert hist.status_code == 200
    assert hist.json()["result"]["action"] == "history"


def test_invalid_transition_api(client: TestClient) -> None:
    client.post(
        "/api/v1/workflow/action",
        json={
            "action": "create",
            "subject": "IBM",
            "workflow_id": "wf-api-3",
            "created_at": FIXED,
        },
    )
    response = client.post(
        "/api/v1/workflow/action",
        json={
            "action": "transition",
            "workflow_id": "wf-api-3",
            "to_stage": "published",
            "actor_id": "u1",
            "created_at": FIXED,
        },
    )
    assert response.status_code == 400
    assert response.json()["message"] == "Data unavailable."


def test_a006_regression(client: TestClient) -> None:
    response = client.get("/api/v1/policy/schema")
    assert response.status_code == 200
    assert response.json()["ok"] is True
