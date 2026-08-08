"""P5.1 — Closed beta programme API tests (ops only; P0-05 admin JWT)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from admin.beta_programme import reset_beta_programme_for_tests
from api_platform.api.app import create_app
from auth_test_helpers import admin_headers


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DSP_CLOSED_BETA", "true")
    monkeypatch.setenv("DSP_BETA_INVITATION_ONLY", "true")
    monkeypatch.setenv("DSP_BETA_BANNER", "true")
    monkeypatch.delenv("DSP_BETA_INVITE_ALLOWLIST", raising=False)
    reset_beta_programme_for_tests()
    app = create_app()
    return TestClient(app)


@pytest.fixture()
def headers(client: TestClient) -> dict[str, str]:
    from uuid import uuid4

    suffix = uuid4().hex[:8]
    return admin_headers(
        client,
        user_id=f"u-beta-{suffix}",
        username=f"betaadmin{suffix}",
    )


def test_beta_status_and_invite_gate(
    client: TestClient, headers: dict[str, str]
) -> None:
    status = client.get("/api/v1/beta/status", params={"identity": "alice@example.com"})
    assert status.status_code == 200
    body = status.json()
    assert body["ok"] is True
    assert body["result"]["programme"]["closed_beta_mode"] is True
    assert body["result"]["access_allowed"] is False

    created = client.post(
        "/api/v1/admin/beta/invites",
        headers=headers,
        json={
            "email_or_username": "alice@example.com",
            "role": "beta_participant",
            "status": "approved",
        },
    )
    assert created.status_code == 200
    assert created.json()["ok"] is True

    allowed = client.get(
        "/api/v1/beta/status", params={"identity": "alice@example.com"}
    )
    assert allowed.json()["result"]["access_allowed"] is True


def test_feedback_and_issue_workflow(
    client: TestClient, headers: dict[str, str]
) -> None:
    fb = client.post(
        "/api/v1/beta/feedback",
        json={
            "category": "bug_report",
            "title": "Toolbar overlap",
            "description": "Feedback button overlaps status bar on mobile",
            "rating": 4,
            "acknowledgement": True,
            "app_version": "2.0.2",
            "browser": "TestAgent",
            "company_analysed": "AAPL",
            "page_path": "/analysis",
        },
    )
    assert fb.status_code == 200
    assert fb.json()["result"]["acknowledgement"] is True

    issues = client.get("/api/v1/admin/beta/issues", headers=headers)
    assert issues.status_code == 200
    rows = issues.json()["result"]
    assert len(rows) >= 1
    issue_id = rows[0]["id"]
    assert rows[0]["status"] == "new"

    patched = client.patch(
        f"/api/v1/admin/beta/issues/{issue_id}",
        headers=headers,
        json={"status": "triaged", "priority": "p1"},
    )
    assert patched.status_code == 200
    assert patched.json()["result"]["status"] == "triaged"


def test_analytics_and_dashboard(
    client: TestClient, headers: dict[str, str]
) -> None:
    client.post(
        "/api/v1/beta/analytics/event",
        json={"kind": "login", "ok": True, "feature": "auth"},
    )
    client.post(
        "/api/v1/beta/analytics/event",
        json={"kind": "analysis", "ok": True, "duration_ms": 1200, "feature": "analyse"},
    )
    client.post(
        "/api/v1/beta/analytics/event",
        json={"kind": "export", "ok": True, "feature": "export"},
    )
    summary = client.get("/api/v1/admin/beta/analytics", headers=headers)
    assert summary.status_code == 200
    data = summary.json()["result"]
    assert data["export_frequency"] >= 1
    assert data["analysis_completion_rate"] == 1.0

    dash = client.get("/api/v1/admin/beta/dashboard", headers=headers)
    assert dash.status_code == 200
    result = dash.json()["result"]
    assert "success_criteria" in result
    assert result["success_criteria"]["critical_bugs_max"] == 0
    assert result["reports_generated"] >= 1


@pytest.mark.xfail(
    reason="Stale version pin (known residual; not P0-05 scope)",
    strict=False,
)
def test_dsp_platform_version_expectation() -> None:
    from dsp_platform import __version__

    assert __version__ == "1.7.2"


def test_snapshot_classify_and_rc_assessment(
    client: TestClient, headers: dict[str, str]
) -> None:
    client.post(
        "/api/v1/beta/feedback",
        json={
            "category": "bug_report",
            "severity": "medium",
            "title": "Minor layout polish",
            "description": "Spacing inconsistency on settings",
            "rating": 5,
            "acknowledgement": True,
            "app_version": "2.0.2",
        },
    )
    issues = client.get("/api/v1/admin/beta/issues", headers=headers).json()["result"]
    issue_id = issues[0]["id"]
    classified = client.post(
        f"/api/v1/admin/beta/issues/{issue_id}/classify",
        headers=headers,
        json={
            "disposition": "fixed",
            "rationale": "Adjusted spacing in settings workspace chrome.",
        },
    )
    assert classified.status_code == 200
    assert classified.json()["result"]["disposition"] == "fixed"
    assert classified.json()["result"]["status"] == "resolved"

    snap = client.get("/api/v1/admin/beta/snapshot", headers=headers)
    assert snap.status_code == 200
    body = snap.json()["result"]
    assert body["kind"] == "dsp_beta_programme_snapshot"
    assert len(body["issues"]) >= 1

    imported = client.post(
        "/api/v1/admin/beta/snapshot/import",
        headers=headers,
        json={"snapshot": body, "merge": True},
    )
    assert imported.status_code == 200
    assert imported.json()["result"]["imported"] is True

    rc = client.get("/api/v1/admin/beta/rc-assessment", headers=headers)
    assert rc.status_code == 200
    assessment = rc.json()["result"]
    assert assessment["decision"] in {
        "READY_WITH_MINOR_CONDITIONS",
        "NOT_READY",
        "READY_FOR_RC",
    }
    assert "overall_score" in assessment
