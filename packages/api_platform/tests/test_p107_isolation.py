"""P1-07 — multi-tenant isolation (IDOR / cross-tenant / spoofing)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from api_platform.api.dependencies import DatabaseReportStore
from api_platform.api.tenant_isolation import stamp_report_owner
from auth_test_helpers import bearer_headers, register_user
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.research_workspace import reset_research_workspace_store_for_tests
from dsp_platform.research_workspace.db_store import DatabaseResearchWorkspaceStore
from dsp_platform.research_workspace.store import ResearchWorkspaceStore
from dsp_platform.saas_platform import reset_saas_overlay_store_for_tests
from dsp_platform.saas_platform.db_store import DatabaseSaasOverlayStore
from enterprise import (
    DatabaseEnterpriseStore,
    EnterpriseService,
    reset_enterprise_service_for_tests,
)
from production_platform import InMemoryDatabasePort


@pytest.fixture()
def platform() -> DSPPlatform:
    reset_enterprise_service_for_tests(EnterpriseService())
    reset_saas_overlay_store_for_tests()
    reset_research_workspace_store_for_tests(ResearchWorkspaceStore())
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )


@pytest.fixture()
def client(platform: DSPPlatform) -> TestClient:
    return TestClient(create_app(platform=platform))


def _two_tenants(client: TestClient) -> tuple[dict[str, str], dict[str, str], str, str]:
    register_user(client, user_id="u-a", username="tenanta")
    register_user(client, user_id="u-b", username="tenantb")
    ha = bearer_headers(client, username="tenanta")
    hb = bearer_headers(client, username="tenantb")
    org_a = client.post(
        "/api/v1/enterprise/organizations",
        headers=ha,
        json={"name": "Org A", "slug": "org-a-p107"},
    )
    org_b = client.post(
        "/api/v1/enterprise/organizations",
        headers=hb,
        json={"name": "Org B", "slug": "org-b-p107"},
    )
    assert org_a.status_code == 200, org_a.text
    assert org_b.status_code == 200, org_b.text
    return ha, hb, org_a.json()["result"]["org_id"], org_b.json()["result"]["org_id"]


def test_enterprise_cross_tenant_read_denied(client: TestClient) -> None:
    ha, hb, org_a, org_b = _two_tenants(client)
    assert client.get(f"/api/v1/enterprise/organizations/{org_a}", headers=ha).status_code == 200
    deny = client.get(f"/api/v1/enterprise/organizations/{org_a}", headers=hb)
    assert deny.status_code == 403
    deny_roles = client.get(
        f"/api/v1/enterprise/organizations/{org_a}/roles", headers=hb
    )
    assert deny_roles.status_code == 403


def test_enterprise_idor_and_spoofing(client: TestClient) -> None:
    ha, hb, org_a, org_b = _two_tenants(client)
    # Org id substitution
    assert (
        client.get(f"/api/v1/enterprise/organizations/{org_b}", headers=ha).status_code
        == 403
    )
    # X-User-Id cannot elevate guest into owner of foreign org
    spoof = client.get(
        f"/api/v1/enterprise/organizations/{org_a}",
        headers={**hb, "X-User-Id": "u-a"},
    )
    assert spoof.status_code == 403
    # Permission oracle against foreign org denied
    probe = client.post(
        f"/api/v1/enterprise/organizations/{org_a}/permissions/evaluate",
        headers=hb,
        json={"user_id": "u-a", "permission": "org.manage"},
    )
    assert probe.status_code == 403


def test_saas_cross_tenant_read_write_denied(client: TestClient) -> None:
    ha, hb, org_a, org_b = _two_tenants(client)
    # Seed SaaS subscription for A via owner
    sub = client.post(
        "/api/v1/saas/subscription",
        headers=ha,
        json={"org_id": org_a, "plan_id": "starter"},
    )
    assert sub.status_code == 200, sub.text

    assert (
        client.get(
            f"/api/v1/saas/organization/{org_a}/subscription", headers=ha
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/v1/saas/organization/{org_a}/subscription", headers=hb
        ).status_code
        == 403
    )
    # Cross-tenant write blocked before overlay mutation
    overwrite = client.post(
        "/api/v1/saas/subscription",
        headers=hb,
        json={"org_id": org_a, "plan_id": "enterprise"},
    )
    assert overwrite.status_code == 403
    still = client.get(
        f"/api/v1/saas/organization/{org_a}/subscription", headers=ha
    )
    assert still.json()["result"]["subscription"]["plan_id"] == "starter"

    # Dashboard must not list foreign orgs
    dash = client.get("/api/v1/saas/dashboard", headers=hb)
    assert dash.status_code == 200
    org_ids = [o["org_id"] for o in dash.json()["result"]["organizations"]]
    assert org_a not in org_ids
    assert org_b in org_ids


def test_workspace_note_isolation(client: TestClient) -> None:
    register_user(client, user_id="ws-a", username="wsa")
    register_user(client, user_id="ws-b", username="wsb")
    ha = bearer_headers(client, username="wsa")
    hb = bearer_headers(client, username="wsb")

    assert client.get("/api/v1/research-workspace").status_code == 401
    created = client.post(
        "/api/v1/research-workspace/note",
        headers={**ha, "X-User-Id": "ws-b"},
        json={"title": "Secret", "body": "A only", "created_by": "ws-b"},
    )
    assert created.status_code == 200, created.text
    note = created.json()["result"]["note"]
    assert note["created_by"] == "ws-a"
    note_id = note["note_id"]

    assert (
        client.get(f"/api/v1/research-workspace/note/{note_id}", headers=ha).status_code
        == 200
    )
    deny = client.get(f"/api/v1/research-workspace/note/{note_id}", headers=hb)
    assert deny.status_code == 403
    deny_write = client.put(
        f"/api/v1/research-workspace/note/{note_id}",
        headers=hb,
        json={"body": "hijack"},
    )
    assert deny_write.status_code == 403
    listed_b = client.get("/api/v1/research-workspace/notes", headers=hb)
    assert listed_b.status_code == 200
    assert all(n["note_id"] != note_id for n in listed_b.json()["result"]["notes"])


def test_report_owner_isolation(client: TestClient) -> None:
    register_user(client, user_id="r-a", username="repa")
    register_user(client, user_id="r-b", username="repb")
    ha = bearer_headers(client, username="repa")
    hb = bearer_headers(client, username="repb")

    assert client.post(
        "/analyze/company",
        json={
            "symbol": "AAPL",
            "asset_class": "equity",
            "currency": "USD",
            "start": "2024-01-01",
            "end": "2024-06-01",
        },
    ).status_code == 401

    created = client.post(
        "/analyze/company",
        headers=ha,
        json={
            "symbol": "AAPL",
            "asset_class": "equity",
            "currency": "USD",
            "start": "2024-01-01",
            "end": "2024-06-01",
        },
    )
    assert created.status_code == 200, created.text
    report_id = created.json()["payload"]["report_id"]
    assert client.get(f"/report/{report_id}", headers=ha).status_code == 200
    assert client.get(f"/report/{report_id}", headers=hb).status_code == 404
    assert client.get(f"/report/{report_id}").status_code == 401


def test_durable_worker_isolation_restart() -> None:
    db = InMemoryDatabasePort()
    # Worker A writes enterprise + saas + workspace + report for tenant A
    ent_a = EnterpriseService(store=DatabaseEnterpriseStore(db))
    org = ent_a.create_organization(
        name="Durable A", slug="durable-a-p107", owner_user_id="owner-a"
    )
    org_id = org["org_id"]
    saas_a = DatabaseSaasOverlayStore(db)
    saas_a.upsert_subscription(org_id, {"plan_id": "starter", "status": "active"})
    ws_a = DatabaseResearchWorkspaceStore(db)
    note = ws_a.create_note(
        {"title": "Private", "body": "A", "created_by": "owner-a"}
    )
    reports_a = DatabaseReportStore(db)
    reports_a.put(
        "rpt-a",
        stamp_report_owner({"capability": "x", "payload": {}, "ok": True}, "owner-a"),
    )

    # Restart / second worker
    ent_b = EnterpriseService(store=DatabaseEnterpriseStore(db))
    assert ent_b.get_organization(org_id, actor_user_id="owner-a") is not None
    with pytest.raises(Exception):
        ent_b.get_organization(org_id, actor_user_id="intruder")

    saas_b = DatabaseSaasOverlayStore(db)
    assert saas_b.get_subscription(org_id)["plan_id"] == "starter"

    ws_b = DatabaseResearchWorkspaceStore(db)
    fetched = ws_b.get_note(note["note_id"])
    assert fetched is not None
    assert fetched["created_by"] == "owner-a"

    reports_b = DatabaseReportStore(db)
    assert reports_b.get("rpt-a")["owner_user_id"] == "owner-a"
