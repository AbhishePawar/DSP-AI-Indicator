"""API tests — RC1 Milestone 8 Research Workspace (P1-07 auth + owner)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from auth_test_helpers import bearer_headers, register_user
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.research_workspace import reset_research_workspace_store_for_tests
from dsp_platform.research_workspace.store import ResearchWorkspaceStore


@pytest.fixture
def platform() -> DSPPlatform:
    reset_research_workspace_store_for_tests(ResearchWorkspaceStore())
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )


@pytest.fixture
def client(platform: DSPPlatform) -> TestClient:
    return TestClient(create_app(platform=platform))


@pytest.fixture
def headers(client: TestClient) -> dict[str, str]:
    register_user(client, user_id="ws-owner", username="wsowner")
    return bearer_headers(client, username="wsowner")


def test_schema_and_dashboard(client: TestClient, headers: dict[str, str]) -> None:
    schema = client.get("/api/v1/research-workspace/schema")
    assert schema.status_code == 200
    assert "templates" in schema.json()["schema"]
    assert client.get("/api/v1/research-workspace").status_code == 401
    dash = client.get("/api/v1/research-workspace", headers=headers)
    assert dash.status_code == 200
    assert dash.json()["ok"] is True


def test_note_lifecycle(client: TestClient, headers: dict[str, str]) -> None:
    created = client.post(
        "/api/v1/research-workspace/note",
        headers=headers,
        json={"title": "Memo", "body": "draft body", "company": "TCS"},
    )
    assert created.status_code == 200
    note_id = created.json()["result"]["note"]["note_id"]
    assert created.json()["result"]["note"]["created_by"] == "ws-owner"

    updated = client.put(
        f"/api/v1/research-workspace/note/{note_id}",
        headers=headers,
        json={"body": "updated body"},
    )
    assert updated.status_code == 200
    assert updated.json()["result"]["note"]["body"] == "updated body"

    versions = client.get(
        f"/api/v1/research-workspace/note/{note_id}/versions", headers=headers
    )
    assert versions.status_code == 200
    assert versions.json()["result"]["versions"]

    deleted = client.delete(
        f"/api/v1/research-workspace/note/{note_id}", headers=headers
    )
    assert deleted.status_code == 200
    assert deleted.json()["result"]["deleted"] is True


def test_folder_bookmark_template_search(
    client: TestClient, headers: dict[str, str]
) -> None:
    folder = client.post(
        "/api/v1/research-workspace/folder",
        headers=headers,
        json={"name": "Ideas"},
    )
    assert folder.status_code == 200
    bookmark = client.post(
        "/api/v1/research-workspace/bookmark",
        headers=headers,
        json={"kind": "report", "label": "TCS report", "target_id": "r1"},
    )
    assert bookmark.status_code == 200
    template = client.post(
        "/api/v1/research-workspace/template",
        headers=headers,
        json={"template_id": "meeting_notes", "title": "IC Sync"},
    )
    assert template.status_code == 200
    search = client.get(
        "/api/v1/research-workspace/search",
        headers=headers,
        params={"q": "IC"},
    )
    assert search.status_code == 200
