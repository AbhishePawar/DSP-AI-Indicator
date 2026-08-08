"""EPIC-A003 Continuous Research Monitoring API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.research_archive import (
    InMemoryArchiveStore,
    ResearchArchiveService,
    get_research_archive,
    reset_research_archive_for_tests,
)
from dsp_platform.research_monitoring import reset_monitoring_registry_for_tests
from dsp_platform.research_object import build_research_object, research_object_to_dict

FIXED = "2026-07-28T12:00:00+00:00"


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_research_archive_for_tests(ResearchArchiveService(InMemoryArchiveStore()))
    reset_monitoring_registry_for_tests()
    yield
    reset_research_archive_for_tests(None)
    reset_monitoring_registry_for_tests()


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
    response = client.get("/api/v1/research/monitoring/schema")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "no_recommendations" in body["schema"]["rules"]
    assert body["schema"]["read_only"] is True


def test_watchlist_track_evaluate(client: TestClient) -> None:
    base = research_object_to_dict(
        build_research_object(
            symbol="AAPL",
            object_id="ro-api-mon",
            created_at=FIXED,
            analysis_payload={
                "ok": True,
                "recommendation_summary": {
                    "label": "Research Mode",
                    "margin_of_safety": 0.1,
                },
            },
        )
    )
    changed = {
        **base,
        "recommendation": {
            **base["recommendation"],
            "payload": {
                **dict(base["recommendation"]["payload"] or {}),
                "margin_of_safety": 0.4,
            },
        },
    }
    archive = get_research_archive()
    a = archive.archive(
        "research_object",
        base,
        snapshot_id="api-mon-a",
        archived_at=FIXED,
        lineage_id="api-mon",
    )
    b = archive.archive(
        "research_object",
        changed,
        snapshot_id="api-mon-b",
        archived_at=FIXED,
        parent_snapshot_id=a.snapshot_id,
    )

    wl = client.post(
        "/api/v1/research/monitoring/watchlist", json={"symbols": ["AAPL"]}
    )
    assert wl.status_code == 200
    assert "AAPL" in wl.json()["symbols"]

    track = client.post(
        "/api/v1/research/monitoring/track",
        json={
            "subject": "AAPL",
            "baseline_snapshot_id": a.snapshot_id,
            "current_snapshot_id": b.snapshot_id,
            "tracked_at": FIXED,
        },
    )
    assert track.status_code == 200

    response = client.post(
        "/api/v1/research/monitoring/evaluate",
        json={
            "snapshot_pairs": {
                "AAPL": {
                    "baseline_snapshot_id": a.snapshot_id,
                    "current_snapshot_id": b.snapshot_id,
                }
            },
            "result_id": "mon-api-1",
            "created_at": FIXED,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["result"]["provenance"]["engines_called"] is False
    assert len(body["result"]["alerts"]) >= 1
    assert body["result"]["alerts"][0]["citations"]


def test_portfolio_register(client: TestClient) -> None:
    response = client.post(
        "/api/v1/research/monitoring/portfolio",
        json={"portfolio_id": "pf-api", "metadata": {"label": "core"}},
    )
    assert response.status_code == 200
    assert response.json()["portfolio"]["portfolio_id"] == "pf-api"


def test_a002_regression_unchanged(client: TestClient) -> None:
    """A002 routes remain available after A003 wiring."""
    ro = research_object_to_dict(
        build_research_object(
            symbol="AAPL",
            object_id="ro-reg-a2",
            created_at=FIXED,
            analysis_payload={
                "ok": True,
                "recommendation_summary": {
                    "label": "Research Mode",
                    "margin_of_safety": 0.1,
                },
            },
        )
    )
    response = client.post(
        "/api/v1/portfolio/intelligence",
        json={
            "portfolio": {
                "portfolio_id": "pf-reg",
                "holdings": [{"symbol": "AAPL", "weight": 1.0}],
            },
            "research_objects": {"AAPL": ro},
            "result_id": "pi-reg",
            "created_at": FIXED,
        },
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
