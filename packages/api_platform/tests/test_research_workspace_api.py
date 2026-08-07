"""API tests — RC1 Milestone 8 Research Workspace."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
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


def test_schema_and_dashboard(client: TestClient) -> None:
    schema = client.get("/api/v1/research-workspace/schema")
    assert schema.status_code == 200
    assert "templates" in schema.json()["schema"]
    dash = client.get("/api/v1/research-workspace")
    assert dash.status_code == 200
    assert dash.json()["ok"] is True


def test_note_lifecycle(client: TestClient) -> None:
    created = client.post(
        "/api/v1/research-workspace/note",
        json={"title": "Memo", "body": "draft body", "company": "TCS"},
    )
    assert created.status_code == 200
    note_id = created.json()["result"]["note"]["note_id"]

    updated = client.put(
        f"/api/v1/research-workspace/note/{note_id}",
        json={"body": "updated body"},
    )
    assert updated.status_code == 200
    assert updated.json()["result"]["note"]["body"] == "updated body"

    versions = client.get(f"/api/v1/research-workspace/note/{note_id}/versions")
    assert versions.status_code == 200
    assert versions.json()["result"]["versions"]

    deleted = client.delete(f"/api/v1/research-workspace/note/{note_id}")
    assert deleted.status_code == 200
    assert deleted.json()["result"]["deleted"] is True


def test_folder_bookmark_template_search(client: TestClient) -> None:
    folder = client.post(
        "/api/v1/research-workspace/folder",
        json={"name": "Ideas"},
    )
    assert folder.status_code == 200
    bookmark = client.post(
        "/api/v1/research-workspace/bookmark",
        json={"kind": "report", "label": "TCS report", "target_id": "r1"},
    )
    assert bookmark.status_code == 200
    template = client.post(
        "/api/v1/research-workspace/template",
        json={"template_id": "meeting_notes", "title": "IC Sync"},
    )
    assert template.status_code == 200
    search = client.get("/api/v1/research-workspace/search", params={"q": "IC"})
    assert search.status_code == 200
    assert search.json()["ok"] is True


def test_comment_share_publish(client: TestClient) -> None:
    note = client.post(
        "/api/v1/research-workspace/note",
        json={"title": "Collab", "body": "text"},
    ).json()["result"]["note"]
    comment = client.post(
        "/api/v1/research-workspace/comment",
        json={"note_id": note["note_id"], "body": "@u2 please review", "mentions": ["u2"]},
    )
    assert comment.status_code == 200
    cid = comment.json()["result"]["comment"]["comment_id"]
    resolved = client.post(
        f"/api/v1/research-workspace/comment/{cid}/resolve",
        json={"resolved": True},
    )
    assert resolved.status_code == 200
    share = client.post(
        "/api/v1/research-workspace/share",
        json={"note_id": note["note_id"], "user_ids": ["u2"]},
    )
    assert share.status_code == 200
    publish = client.post(
        "/api/v1/research-workspace/publish",
        json={"note_id": note["note_id"], "status": "review"},
    )
    assert publish.status_code == 200
    assert publish.json()["result"]["note"]["status"] == "review"


def test_ai_endpoint(client: TestClient) -> None:
    note = client.post(
        "/api/v1/research-workspace/note",
        json={"title": "AI", "body": "draft", "company": "TCS"},
    ).json()["result"]["note"]
    ai = client.post(
        "/api/v1/research-workspace/ai",
        json={
            "note_id": note["note_id"],
            "instruction": "Improve writing",
            "mode": "chat",
        },
    )
    assert ai.status_code == 200
    assert "answer" in ai.json()["result"]
