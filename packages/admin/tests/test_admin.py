"""EPIC-A010 Enterprise Admin & Audit Console unit tests."""

from __future__ import annotations

import pytest

from admin import (
    AdminService,
    get_admin_service,
    reset_admin_service_for_tests,
)
from auth import (
    AuthService,
    RoleRegistry,
    reset_auth_service_for_tests,
    reset_role_registry_for_tests,
)
from persistence import (
    InMemoryStorageProvider,
    PersistenceService,
    RepositoryRegistry,
    get_persistence_service,
    reset_persistence_service_for_tests,
    reset_repository_registry_for_tests,
)

FIXED = "2026-07-28T15:00:00+00:00"
FIXED2 = "2026-07-28T16:00:00+00:00"


@pytest.fixture(autouse=True)
def _reset() -> None:
    store = InMemoryStorageProvider()
    registry = RepositoryRegistry(storage=store)
    reset_repository_registry_for_tests(registry)
    ps = PersistenceService(registry)
    reset_persistence_service_for_tests(ps)
    reset_role_registry_for_tests(RoleRegistry())
    auth = AuthService(ps, jwt_secret="test-secret")
    reset_auth_service_for_tests(auth)
    reset_admin_service_for_tests(AdminService(ps, auth))
    yield
    reset_admin_service_for_tests(None)
    reset_auth_service_for_tests(None)
    reset_role_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    reset_repository_registry_for_tests(None)


def test_user_and_role_management() -> None:
    svc = get_admin_service()
    user = svc.create_user(
        username="adminops",
        email="ops@example.com",
        password="Secret123!",
        roles=["read_only"],
        user_id="u-ops",
        created_at=FIXED,
        password_salt="aabbccddeeff0011",
    )
    assert user["username"] == "adminops"
    assert "password_hash" not in user
    users = svc.list_users()
    assert any(u["user_id"] == "u-ops" for u in users)
    updated = svc.set_user_roles("u-ops", ["administrator"])
    assert updated["roles"] == ["administrator"]
    roles = svc.list_roles()
    assert any(r["role_id"] == "administrator" for r in roles)
    perms = svc.list_permissions()
    assert "view_audit" in perms
    role = svc.upsert_role(
        role_id="ops_viewer",
        name="Ops Viewer",
        permissions=["view_audit", "read_research"],
    )
    assert role["role_id"] == "ops_viewer"


def test_audit_view_search_export_determinism() -> None:
    ps = get_persistence_service()
    ps.persist_audit_record(
        {
            "event_id": "e1",
            "event_type": "login",
            "subject": "INFY",
            "workflow_id": "wf-1",
            "created_at": FIXED,
            "message": "user logged in",
        },
        created_at=FIXED,
    )
    ps.persist_audit_record(
        {
            "event_id": "e2",
            "event_type": "approve",
            "subject": "TCS",
            "workflow_id": "wf-2",
            "created_at": FIXED2,
            "message": "workflow approved",
        },
        created_at=FIXED2,
    )
    svc = get_admin_service()
    rows = svc.list_audit_records()
    assert len(rows) == 2
    assert rows[0]["entity_id"] == "audit-e1"
    filtered = svc.list_audit_records(subject="INFY")
    assert len(filtered) == 1
    searched = svc.search("approve", scope="audit")
    assert searched["count"] == 1
    export1 = svc.export_audit()
    export2 = svc.export_audit()
    assert export1 == export2
    assert export1["count"] == 2
    assert export1["records"][0]["entity_id"] == "audit-e1"


def test_health_metrics_dashboard() -> None:
    svc = get_admin_service()
    svc.create_user(
        username="metric1",
        email="m@example.com",
        password="Secret123!",
        user_id="u-m",
        created_at=FIXED,
        password_salt="aabbccddeeff0011",
    )
    get_persistence_service().persist_audit_record(
        {"event_id": "m1", "event_type": "note", "created_at": FIXED},
        created_at=FIXED,
    )
    health = svc.health_panel()
    assert health["ready"] is True
    assert health["status"] == "pass"
    metrics = svc.system_metrics()
    assert metrics["users"] == 1
    assert metrics["audit_records"] == 1
    dash = svc.dashboard(generated_at=FIXED)
    assert dash["generated_at"] == FIXED
    assert dash["users_count"] == 1
    assert dash["audit_records_count"] == 1
    assert dash["health_status"] == "pass"
    assert dash["metadata"]["research_mutated"] is False


def test_sessions_timeline_versions_flags() -> None:
    svc = get_admin_service()
    svc.create_user(
        username="sess1",
        email="s@example.com",
        password="Secret123!",
        roles=["portfolio_manager"],
        user_id="u-s",
        created_at=FIXED,
        password_salt="aabbccddeeff0011",
    )
    svc.auth.login(
        username="sess1",
        password="Secret123!",
        created_at=FIXED,
        session_id="sess-1",
        access_jti="a1",
        refresh_jti="r1",
    )
    sessions = svc.list_sessions()
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "sess-1"
    get_persistence_service().persist_workflow_record(
        {
            "workflow_id": "wf-x",
            "stage": "review",
            "subject": "INFY",
            "created_at": FIXED,
            "updated_at": FIXED,
            "artifact_refs": {},
            "audit_trail": [],
            "comments": [],
        },
        created_at=FIXED,
    )
    timeline = svc.activity_timeline(limit=10)
    assert any(e["kind"] == "workflow_record" for e in timeline)
    versions = svc.versions()
    assert any(p["package"] == "admin" for p in versions["packages"])
    flags = svc.feature_flags({"demo_flag": True, "aaa": False})
    assert list(flags["flags"].keys()) == ["aaa", "demo_flag"]
    cfg = svc.configuration()
    assert "items" in cfg
    archive = svc.list_research_archive_metadata()
    assert archive == []


def test_no_research_mutation_via_admin() -> None:
    """Admin export/list must not introduce research payload keys."""
    ps = get_persistence_service()
    ps.put(
        kind="research_ref",
        entity_id="ref-1",
        payload={"ref_id": "r1", "symbol": "INFY"},
        created_at=FIXED,
    )
    svc = get_admin_service()
    refs = svc.list_research_archive_metadata()
    assert len(refs) == 1
    blob = str(refs)
    assert "research_object" not in blob
    assert "institutional_report" not in blob
    assert "analysis_payload" not in blob


def test_platform_facade() -> None:
    from dsp_platform.platform import DSPPlatform

    p = DSPPlatform()
    schema = p.admin_schema()
    assert "admin_dashboard" in schema["capabilities"]
    dash = p.admin_dashboard(generated_at=FIXED)
    assert dash["generated_at"] == FIXED
    assert p.admin_health_panel()["ready"] is True
