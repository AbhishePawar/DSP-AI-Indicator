"""Unit tests — RC1 Milestone 8 Research Workspace (P1-07 actor required)."""

from __future__ import annotations

from typing import Any

import pytest

from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.research_workspace import (
    UNAVAILABLE_MESSAGE,
    get_research_workspace_store,
    reset_research_workspace_store_for_tests,
    run_research_workspace,
)
from dsp_platform.research_workspace.store import ResearchWorkspaceStore

ACTOR = "ws-unit-actor"


def _p(**kwargs: Any) -> dict[str, Any]:
    data = dict(kwargs)
    data["actor_user_id"] = ACTOR
    return data


@pytest.fixture
def platform() -> DSPPlatform:
    reset_research_workspace_store_for_tests(ResearchWorkspaceStore())
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .build()
    )


def test_schema(platform: DSPPlatform) -> None:
    schema = platform.research_workspace_schema()
    assert "investment_memo" in schema["templates"]
    dash = run_research_workspace("dashboard", platform=platform, payload=_p())
    assert dash["ok"] is True


def test_note_crud_and_versions(platform: DSPPlatform) -> None:
    created = platform.run_research_workspace(
        "create_note",
        payload=_p(title="TCS thesis", body="v1 body", company="TCS"),
    )
    note = created["result"]["note"]
    note_id = note["note_id"]
    assert note["version"] == 1
    assert note["created_by"] == ACTOR

    updated = platform.run_research_workspace(
        "update_note",
        payload=_p(note_id=note_id, body="v2 body"),
    )
    assert updated["result"]["note"]["body"] == "v2 body"
    assert updated["result"]["note"]["version"] >= 2

    versions = platform.run_research_workspace(
        "list_versions", payload=_p(note_id=note_id)
    )
    assert len(versions["result"]["versions"]) >= 2

    diff = platform.run_research_workspace(
        "diff_versions",
        payload=_p(note_id=note_id, from_version=1, to_version=2),
    )
    assert "hunks" in diff["result"]


def test_folders_nested(platform: DSPPlatform) -> None:
    parent = platform.run_research_workspace(
        "create_folder", payload=_p(name="India Banks")
    )
    pid = parent["result"]["folder"]["folder_id"]
    child = platform.run_research_workspace(
        "create_folder", payload=_p(name="Private", parent_id=pid)
    )
    assert child["result"]["folder"]["parent_id"] == pid
    renamed = platform.run_research_workspace(
        "rename_folder", payload=_p(folder_id=pid, name="Banks")
    )
    assert renamed["result"]["folder"]["name"] == "Banks"


def test_bookmark_tag_comment_share(platform: DSPPlatform) -> None:
    note = platform.run_research_workspace(
        "create_note", payload=_p(title="Note", body="body")
    )["result"]["note"]
    bm = platform.run_research_workspace(
        "create_bookmark",
        payload=_p(kind="company", label="TCS", target_id="TCS"),
    )
    assert bm["result"]["bookmark"]["kind"] == "company"
    tag = platform.run_research_workspace(
        "upsert_tag", payload=_p(label="Moat", color="#0ea5e9", kind="company")
    )
    assert tag["result"]["tag"]["label"] == "Moat"
    comment = platform.run_research_workspace(
        "add_comment",
        payload=_p(
            note_id=note["note_id"],
            body="Please check MoS",
            mentions=["analyst1"],
        ),
    )
    cid = comment["result"]["comment"]["comment_id"]
    resolved = platform.run_research_workspace(
        "resolve_comment", payload=_p(comment_id=cid, resolved=True)
    )
    assert resolved["result"]["comment"]["resolved"] is True
    share = platform.run_research_workspace(
        "share",
        payload=_p(note_id=note["note_id"], user_ids=["u2"], permission="read"),
    )
    assert share["result"]["share"]["user_ids"] == ["u2"]


def test_template_and_search(platform: DSPPlatform) -> None:
    templated = platform.run_research_workspace(
        "apply_template",
        payload=_p(template_id="checklist", company="INFY", title="INFY checklist"),
    )
    assert "Checklist" in templated["result"]["note"]["title"] or "checklist" in templated[
        "result"
    ]["note"]["title"].lower()
    assert UNAVAILABLE_MESSAGE in templated["result"]["note"]["body"] or "- [ ]" in templated[
        "result"
    ]["note"]["body"]
    found = platform.run_research_workspace("search", payload=_p(query="INFY"))
    assert found["result"]["notes"]


def test_publish_updates_status(platform: DSPPlatform) -> None:
    note = platform.run_research_workspace(
        "create_note", payload=_p(title="Publish me", body="draft")
    )["result"]["note"]
    published = platform.run_research_workspace(
        "publish",
        payload=_p(note_id=note["note_id"], status="review"),
    )
    assert published["result"]["note"]["status"] == "review"


def test_ai_assist_reuses_copilot(platform: DSPPlatform) -> None:
    note = platform.run_research_workspace(
        "create_note",
        payload=_p(title="Risks", body="Concentration unknown", company="TCS"),
    )["result"]["note"]
    ai = platform.run_research_workspace(
        "ai",
        payload=_p(
            note_id=note["note_id"],
            instruction="Explain risks",
            mode="risk",
            company="TCS",
        ),
    )
    assert ai["ok"] is True
    assert "answer" in ai["result"]


def test_dashboard(platform: DSPPlatform) -> None:
    platform.run_research_workspace(
        "create_note", payload=_p(title="Recent", body="x", company="TCS")
    )
    dash = platform.run_research_workspace("dashboard", payload=_p())
    assert dash["result"]["recent_notes"]
    assert "folders" in dash["result"]


def test_delete_note(platform: DSPPlatform) -> None:
    note = platform.run_research_workspace(
        "create_note", payload=_p(title="tmp", body="x")
    )["result"]["note"]
    deleted = platform.run_research_workspace(
        "delete_note", payload=_p(note_id=note["note_id"])
    )
    assert deleted["result"]["deleted"] is True
    assert get_research_workspace_store().get_note(note["note_id"]) is None
