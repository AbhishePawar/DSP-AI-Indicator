"""EPIC-R004 Research Archive API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from auth_test_helpers import bearer_headers, register_user
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

@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    register_user(client, user_id="research-arch-user", username="researcharch")
    return bearer_headers(client, username="researcharch")


def _payload() -> dict:
    return research_object_to_dict(
        build_research_object(
            symbol="AAPL",
            object_id="ro-api-arch",
            created_at=FIXED,
        )
    )


def test_archive_schema(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/research/archive/schema")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["schema"]["immutable"] is True
    assert "research_object" in body["schema"]["kinds"]


def test_archive_retrieve_history_compare(client: TestClient, auth_headers: dict[str, str]) -> None:
    payload = _payload()
    r1 = client.post(
        "/api/v1/research/archive/snapshots",
        headers=auth_headers,
        json={
            "kind": "research_object",
            "payload": payload,
            "snapshot_id": "api-snap-1",
            "lineage_id": "api-line-1",
            "archived_at": FIXED,
        },
    )
    assert r1.status_code == 200
    assert r1.json()["snapshot"]["content_sha256"]

    r2 = client.post(
        "/api/v1/research/archive/snapshots",
        headers=auth_headers,
        json={
            "kind": "research_object",
            "payload": {**payload, "x": 1},
            "snapshot_id": "api-snap-2",
            "parent_snapshot_id": "api-snap-1",
            "archived_at": FIXED,
        },
    )
    assert r2.status_code == 200
    assert r2.json()["snapshot"]["version"]["version_number"] == 2

    got = client.get("/api/v1/research/archive/snapshots/api-snap-1",
        headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["snapshot"]["snapshot_id"] == "api-snap-1"

    hist = client.get("/api/v1/research/archive/lineages/api-line-1/history",
        headers=auth_headers)
    assert hist.status_code == 200
    assert len(hist.json()["history"]) == 2

    cmp_ = client.post(
        "/api/v1/research/archive/compare",
        headers=auth_headers,
        json={"left_snapshot_id": "api-snap-1", "right_snapshot_id": "api-snap-2"},
    )
    assert cmp_.status_code == 200
    assert cmp_.json()["comparison"]["same_content_hash"] is False

    ret = client.post(
        "/api/v1/research/archive/retention/evaluate",
        headers=auth_headers,
        json={"snapshot_id": "api-snap-1"},
    )
    assert ret.status_code == 200
    assert ret.json()["retention"]["retain"] is True


def test_archive_missing(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/research/archive/snapshots/missing",
        headers=auth_headers)
    assert response.status_code == 404
