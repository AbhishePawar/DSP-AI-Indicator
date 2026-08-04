"""EPIC-R005 Research Diff API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.research_archive import (
    InMemoryArchiveStore,
    ResearchArchiveService,
    reset_research_archive_for_tests,
)
from dsp_platform.research_object import build_research_object, research_object_to_dict

FIXED = "2026-07-28T12:00:00+00:00"


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_research_archive_for_tests(ResearchArchiveService(InMemoryArchiveStore()))
    yield
    reset_research_archive_for_tests(None)


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


def test_diff_schema(client: TestClient) -> None:
    response = client.get("/api/v1/research/diff/schema")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["schema"]["source"] == "research_archive_snapshots"
    assert body["schema"]["read_only"] is True


def test_diff_api(client: TestClient) -> None:
    payload = research_object_to_dict(
        build_research_object(symbol="AAPL", object_id="ro-api-d", created_at=FIXED)
    )
    client.post(
        "/api/v1/research/archive/snapshots",
        json={
            "kind": "research_object",
            "payload": payload,
            "snapshot_id": "api-d-a",
            "lineage_id": "api-d",
            "archived_at": FIXED,
        },
    )
    changed = {
        **payload,
        "recommendation": {
            **payload["recommendation"],
            "available": True,
            "status": "ok",
            "message": None,
            "payload": {
                **dict(payload.get("recommendation", {}).get("payload") or {}),
                "label": "Research Mode",
                "margin_of_safety": 0.99,
            },
        },
    }
    client.post(
        "/api/v1/research/archive/snapshots",
        json={
            "kind": "research_object",
            "payload": changed,
            "snapshot_id": "api-d-b",
            "parent_snapshot_id": "api-d-a",
            "archived_at": FIXED,
        },
    )
    response = client.post(
        "/api/v1/research/diff",
        json={
            "left_snapshot_id": "api-d-a",
            "right_snapshot_id": "api-d-b",
            "diff_id": "api-diff-1",
            "created_at": FIXED,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["diff"]["diff_id"] == "api-diff-1"
    assert body["diff"]["change_summary"]["identical_content"] is False


def test_diff_missing_snapshot(client: TestClient) -> None:
    response = client.post(
        "/api/v1/research/diff",
        json={"left_snapshot_id": "missing-a", "right_snapshot_id": "missing-b"},
    )
    assert response.status_code == 404
