"""EPS-002 enterprise foundation unit tests."""

from __future__ import annotations

import pytest

from enterprise import (
    EnterpriseService,
    ForbiddenError,
    NullBillingAdapter,
    reset_enterprise_service_for_tests,
)
from enterprise.service import EnterpriseService as ES


@pytest.fixture()
def svc() -> EnterpriseService:
    service = ES()
    reset_enterprise_service_for_tests(service)
    yield service
    reset_enterprise_service_for_tests(None)


def test_org_isolation_and_rbac(svc: EnterpriseService) -> None:
    a = svc.create_organization(
        name="Alpha Capital", slug="alpha-capital", owner_user_id="u-owner-a"
    )
    b = svc.create_organization(
        name="Beta Funds", slug="beta-funds", owner_user_id="u-owner-b"
    )
    assert a["org_id"] != b["org_id"]

    svc.add_member(
        a["org_id"],
        user_id="u-analyst",
        role_id="analyst",
        actor_user_id="u-owner-a",
    )

    # Cross-org access denied
    with pytest.raises(ForbiddenError):
        svc.list_members(b["org_id"], actor_user_id="u-analyst")

    # Permission-based (not role-name) check
    eval_ok = svc.evaluate_permission(a["org_id"], "u-analyst", "org.view")
    assert eval_ok["allowed"] is True
    eval_deny = svc.evaluate_permission(a["org_id"], "u-analyst", "roles.manage")
    assert eval_deny["allowed"] is False


def test_license_billing_honest_empties(svc: EnterpriseService) -> None:
    org = svc.create_organization(
        name="Lic Org", slug="lic-org", owner_user_id="u1"
    )
    empty = svc.get_license(org["org_id"], actor_user_id="u1")
    assert empty["available"] is False
    assert empty["message"] == "No license assigned."

    lic = svc.assign_license(
        org["org_id"],
        tier="professional",
        seats=5,
        actor_user_id="u1",
    )
    assert lic["tier"] == "professional"
    assert svc.validate_license(org["org_id"])["valid"] is True

    billing = svc.billing_status(org["org_id"], actor_user_id="u1")
    assert billing["available"] is False
    assert billing["message"] == "Billing unavailable."
    assert isinstance(svc.billing, NullBillingAdapter)


def test_audit_immutability_and_api_key_scopes(svc: EnterpriseService) -> None:
    org = svc.create_organization(
        name="Sec Org", slug="sec-org", owner_user_id="u-sec"
    )
    key = svc.create_api_key(
        org["org_id"],
        name="CI",
        scopes=["org.view", "usage.view"],
        actor_user_id="u-sec",
    )
    assert "secret" in key
    assert "secret_hash" not in key
    secret = key["secret"]

    listed = svc.list_api_keys(org["org_id"], actor_user_id="u-sec")
    assert listed["keys"]
    assert "secret" not in listed["keys"][0]
    assert "secret_hash" not in listed["keys"][0]

    verified = svc.verify_api_key(key["key_id"], secret, required_scope="org.view")
    assert verified["key_id"] == key["key_id"]
    with pytest.raises(ForbiddenError):
        svc.verify_api_key(key["key_id"], secret, required_scope="roles.manage")

    svc.disable_api_key(org["org_id"], key["key_id"], actor_user_id="u-sec")
    with pytest.raises(ForbiddenError):
        svc.verify_api_key(key["key_id"], secret)

    with pytest.raises(ForbiddenError):
        svc.mutate_audit_forbidden("any")

    audit = svc.list_audit(org["org_id"], actor_user_id="u-sec")
    assert len(audit) >= 1
    assert all(r["immutable"] is True for r in audit)


def test_session_revoke(svc: EnterpriseService) -> None:
    org = svc.create_organization(
        name="Sess Org", slug="sess-org", owner_user_id="u-sess"
    )
    session = svc.create_session(
        org["org_id"], user_id="u-sess", device_label="laptop"
    )
    active = svc.list_sessions(org["org_id"], actor_user_id="u-sess")
    assert len(active) == 1
    revoked = svc.revoke_session(
        org["org_id"], session["session_id"], actor_user_id="u-sess"
    )
    assert revoked["status"] == "revoked"
    assert svc.list_sessions(org["org_id"], actor_user_id="u-sess") == []


def test_portal_and_ops(svc: EnterpriseService) -> None:
    org = svc.create_organization(
        name="Portal Org", slug="portal-org", owner_user_id="u-p"
    )
    portal = svc.customer_portal(org["org_id"], actor_user_id="u-p")
    assert portal["organization"]["slug"] == "portal-org"
    assert portal["billing"]["message"] == "Billing unavailable."
    assert portal["api_keys"]["message"] == "No API keys."

    usage = svc.platform_usage_analytics()
    assert usage["organizations"] == 1
    assert usage["dau"] == 0

    ops = svc.operational_dashboard()
    assert ops["collaboration"]["realtime"] is False
    assert "shared_research" in ops["collaboration"]["capabilities_reserved"]


def test_teams_hierarchy_ready(svc: EnterpriseService) -> None:
    org = svc.create_organization(
        name="Team Org", slug="team-org", owner_user_id="u-t"
    )
    parent = svc.create_team(
        org["org_id"],
        name="Research",
        kind="research",
        actor_user_id="u-t",
    )
    child = svc.create_team(
        org["org_id"],
        name="Equity Analysts",
        kind="analyst",
        actor_user_id="u-t",
        parent_team_id=parent["team_id"],
    )
    assert child["parent_team_id"] == parent["team_id"]
    teams = svc.list_teams(org["org_id"], actor_user_id="u-t")
    assert len(teams) == 2
