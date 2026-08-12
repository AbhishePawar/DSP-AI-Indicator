"""EPIC-A008 Persistence API tests + A007 regression."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from persistence import (
    InMemoryStorageProvider,
    PersistenceService,
    RepositoryRegistry,
    reset_persistence_service_for_tests,
    reset_repository_registry_for_tests,
)

FIXED = "2026-07-28T12:00:00+00:00"


@pytest.fixture(autouse=True)
def _reset() -> None:
    registry = RepositoryRegistry(storage=InMemoryStorageProvider())
    reset_repository_registry_for_tests(registry)
    reset_persistence_service_for_tests(PersistenceService(registry))
    yield
    reset_persistence_service_for_tests(None)
    reset_repository_registry_for_tests(None)


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


def test_schema(client: TestClient) -> None:
    response = client.get("/api/v1/persistence/schema")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "no_research_mutation" in body["schema"]["rules"]


def test_entity_put_get(client: TestClient) -> None:
    put = client.post(
        "/api/v1/persistence/entity",
        json={
            "kind": "metadata",
            "entity_id": "api-meta-1",
            "payload": {"name": "desk"},
            "refs": {"owner": "u1"},
            "created_at": FIXED,
        },
    )
    assert put.status_code == 200
    assert put.json()["result"]["entity_id"] == "api-meta-1"

    got = client.get("/api/v1/persistence/entity/metadata/api-meta-1")
    assert got.status_code == 200
    assert got.json()["result"]["payload"]["name"] == "desk"


def test_workflow_and_snapshot(client: TestClient) -> None:
    wf = client.post(
        "/api/v1/persistence/workflow",
        json={
            "workflow": {
                "workflow_id": "wf-api",
                "stage": "draft",
                "subject": "AAPL",
                "artifact_refs": {"report_id": "rpt-1"},
                "updated_at": FIXED,
            },
            "created_at": FIXED,
        },
    )
    assert wf.status_code == 200
    assert wf.json()["result"]["kind"] == "workflow_record"

    snap = client.post(
        "/api/v1/persistence/snapshot",
        json={
            "kind": "workflow",
            "source_entity_id": "wf-api",
            "payload": {"stage": "draft"},
            "snapshot_id": "snap-api-1",
            "created_at": FIXED,
        },
    )
    assert snap.status_code == 200
    assert snap.json()["result"]["read_only"] is True


def test_a007_regression_unchanged(client: TestClient) -> None:
    response = client.get("/api/v1/workflow/schema")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert "draft" in response.json()["schema"]["stages"]
