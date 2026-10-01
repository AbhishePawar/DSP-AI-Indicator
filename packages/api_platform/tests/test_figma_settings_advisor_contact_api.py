"""API contracts for the Figma pages added in the full-frontend migration:
Control Center (user settings) · Advisor (client book) · Contact · Coupons.

P0-05: per-user routes require a server-validated JWT; the contact form is the
only public write and never echoes the message body. Coupon administration is
gated by admin permissions; listing is available to signed-in users.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from auth_test_helpers import bearer_headers, register_user
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.investor_workspace import (
    InvestorWorkspaceStore,
    reset_investor_workspace_store_for_tests,
)
from dsp_platform.saas_platform import reset_saas_overlay_store_for_tests


@pytest.fixture
def platform() -> DSPPlatform:
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .build()
    )


@pytest.fixture
def client(platform: DSPPlatform) -> Iterator[TestClient]:
    reset_investor_workspace_store_for_tests(InvestorWorkspaceStore())
    reset_saas_overlay_store_for_tests()
    yield TestClient(create_app(platform=platform))
    reset_investor_workspace_store_for_tests(None)
    reset_saas_overlay_store_for_tests()


@pytest.fixture
def auth(client: TestClient) -> dict[str, str]:
    """Ordinary signed-in user (read_only role — no admin permissions)."""
    register_user(client, user_id="settings-user", username="settingsuser", roles=["read_only"])
    return bearer_headers(client, username="settingsuser")


@pytest.fixture
def other_auth(client: TestClient) -> dict[str, str]:
    register_user(client, user_id="settings-other", username="settingsother", roles=["read_only"])
    return bearer_headers(client, username="settingsother")


@pytest.fixture
def admin_auth(client: TestClient) -> dict[str, str]:
    register_user(
        client, user_id="settings-admin", username="settingsadmin", roles=["administrator"]
    )
    return bearer_headers(client, username="settingsadmin")


# -- auth gates ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/api/v1/workspace/preferences", None),
        ("PUT", "/api/v1/workspace/preferences", {"dark_mode": True}),
        ("DELETE", "/api/v1/workspace/research/saved", None),
        ("GET", "/api/v1/advisor/clients", None),
        ("POST", "/api/v1/advisor/clients", {"name": "A", "risk_profile": "moderate"}),
        ("GET", "/api/v1/saas/coupons", None),
        ("GET", "/api/v1/admin/contact-messages", None),
    ],
)
def test_routes_require_auth(client: TestClient, method: str, path: str, body: dict | None) -> None:
    res = client.request(method, path, json=body)
    assert res.status_code == 401, res.text


def test_contact_inbox_is_admin_only(client: TestClient, auth: dict[str, str]) -> None:
    assert client.get("/api/v1/admin/contact-messages", headers=auth).status_code == 403


def test_coupon_upsert_is_admin_only(client: TestClient, auth: dict[str, str]) -> None:
    res = client.post("/api/v1/saas/coupon", json={"code": "X", "discount_pct": 5}, headers=auth)
    assert res.status_code == 403


# -- preferences (Control Center) --------------------------------------------


def test_preferences_defaults_and_partial_update(client: TestClient, auth: dict[str, str], other_auth: dict[str, str]) -> None:
    res = client.get("/api/v1/workspace/preferences", headers=auth)
    assert res.status_code == 200, res.text
    prefs = res.json()["preferences"]
    assert prefs["notifications"] is True and prefs["beta_features"] is False

    res = client.put("/api/v1/workspace/preferences", json={"beta_features": True}, headers=auth)
    assert res.status_code == 200, res.text
    updated = res.json()["preferences"]
    assert updated["beta_features"] is True and updated["notifications"] is True
    assert "updated_at" in updated

    # Other users are unaffected; unknown keys and non-booleans are rejected.
    assert client.get("/api/v1/workspace/preferences", headers=other_auth).json()["preferences"]["beta_features"] is False
    assert client.put("/api/v1/workspace/preferences", json={"theme": "x"}, headers=auth).status_code == 422
    assert client.put("/api/v1/workspace/preferences", json={"dark_mode": "yes"}, headers=auth).status_code == 422


def test_clear_research_history_is_user_scoped(client: TestClient, auth: dict[str, str], other_auth: dict[str, str]) -> None:
    for headers in (auth, other_auth):
        client.post("/api/v1/workspace/research/saved", json={"symbol": "TCS", "title": "t"}, headers=headers)
    res = client.delete("/api/v1/workspace/research/saved", headers=auth)
    assert res.status_code == 200 and res.json()["removed"] == 1
    assert client.get("/api/v1/workspace/research/saved", headers=auth).json()["count"] == 0
    assert client.get("/api/v1/workspace/research/saved", headers=other_auth).json()["count"] == 1


# -- advisor clients -----------------------------------------------------------


def test_advisor_client_book_crud_and_overview(client: TestClient, auth: dict[str, str], other_auth: dict[str, str]) -> None:
    res = client.post(
        "/api/v1/advisor/clients",
        json={"name": "Rajesh Kumar", "risk_profile": "Moderate", "email": "R@Example.com", "portfolio_value": 1250000},
        headers=auth,
    )
    assert res.status_code == 201, res.text
    item = res.json()["item"]
    assert item["risk_profile"] == "moderate" and item["email"] == "r@example.com"
    assert item["research_sessions"] == 0
    client_id = item["client_id"]

    # Second client without a portfolio value → null, excluded from the total.
    res = client.post("/api/v1/advisor/clients", json={"name": "Priya", "risk_profile": "aggressive"}, headers=auth)
    assert res.status_code == 201 and res.json()["item"]["portfolio_value"] is None

    listing = client.get("/api/v1/advisor/clients", headers=auth).json()
    assert listing["count"] == 2
    assert listing["overview"]["active_clients"] == 2
    assert listing["overview"]["total_portfolio_value"] == 1250000.0
    assert listing["overview"]["clients_with_portfolio_value"] == 1
    assert listing["overview"]["risk_profile_counts"] == {"conservative": 0, "moderate": 1, "aggressive": 1}

    # Sessions increment; other advisors cannot see or touch the book.
    res = client.post(f"/api/v1/advisor/clients/{client_id}/sessions", headers=auth)
    assert res.status_code == 200 and res.json()["item"]["research_sessions"] == 1
    assert client.get("/api/v1/advisor/clients", headers=other_auth).json()["count"] == 0
    assert client.get(f"/api/v1/advisor/clients/{client_id}", headers=other_auth).status_code == 404
    assert client.delete(f"/api/v1/advisor/clients/{client_id}", headers=other_auth).json()["removed"] is False

    res = client.put(
        f"/api/v1/advisor/clients/{client_id}",
        json={"name": "Rajesh K.", "risk_profile": "conservative"},
        headers=auth,
    )
    assert res.status_code == 200 and res.json()["item"]["name"] == "Rajesh K."
    assert res.json()["item"]["research_sessions"] == 1  # preserved across update

    assert client.delete(f"/api/v1/advisor/clients/{client_id}", headers=auth).json()["removed"] is True
    assert client.get("/api/v1/advisor/clients", headers=auth).json()["count"] == 1


def test_advisor_client_validation(client: TestClient, auth: dict[str, str]) -> None:
    assert client.post("/api/v1/advisor/clients", json={"name": "", "risk_profile": "moderate"}, headers=auth).status_code == 422
    assert client.post("/api/v1/advisor/clients", json={"name": "A", "risk_profile": "yolo"}, headers=auth).status_code == 422
    assert client.post("/api/v1/advisor/clients", json={"name": "A", "risk_profile": "moderate", "email": "nope"}, headers=auth).status_code == 422
    assert client.post("/api/v1/advisor/clients", json={"name": "A", "risk_profile": "moderate", "portfolio_value": -1}, headers=auth).status_code == 422
    assert client.post("/api/v1/advisor/clients", json={"name": "A", "risk_profile": "moderate", "rating": "A+"}, headers=auth).status_code == 422


# -- contact ------------------------------------------------------------------


def test_contact_form_is_public_and_admin_readable(client: TestClient, admin_auth: dict[str, str]) -> None:
    res = client.post(
        "/api/v1/contact",
        json={"name": "Asha", "email": "Asha@Example.com", "message": "I would like a demo of DSP.", "source": "contact-page"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["ok"] is True and body["message_id"] and body["received_at"]
    assert "message" not in body  # never echoed back to the public caller

    inbox = client.get("/api/v1/admin/contact-messages", headers=admin_auth).json()
    assert inbox["count"] == 1
    assert inbox["items"][0]["email"] == "asha@example.com"
    assert inbox["items"][0]["message"] == "I would like a demo of DSP."
    assert inbox["items"][0]["status"] == "new"


def test_contact_form_validation(client: TestClient) -> None:
    assert client.post("/api/v1/contact", json={"name": "A", "email": "a@b.c", "message": "short"}).status_code == 422
    assert client.post("/api/v1/contact", json={"name": "A", "email": "not-an-email", "message": "long enough message"}).status_code == 422
    assert client.post("/api/v1/contact", json={"name": "A", "email": "a@b.c", "message": "long enough message", "extra": 1}).status_code == 422


# -- coupons ------------------------------------------------------------------


def test_coupons_listing_returns_only_active(client: TestClient, auth: dict[str, str], admin_auth: dict[str, str]) -> None:
    assert client.get("/api/v1/saas/coupons", headers=auth).json()["result"]["coupons"] == []
    for payload in (
        {
            "code": "welcome20",
            "discount_pct": 20,
            "active": True,
            "title": "20% off Premium",
            "category": "premium",
            "applicable_to": ["Premium Monthly", ""],
            "featured": True,
        },
        {"code": "OLD10", "discount_pct": 10, "active": False},
        {"code": "EXPIRED", "discount_pct": 5, "active": True, "expires_at": "2000-01-01T00:00:00+00:00"},
    ):
        assert client.post("/api/v1/saas/coupon", json=payload, headers=admin_auth).status_code == 200

    bad = client.post("/api/v1/saas/coupon", json={"code": "BAD", "category": "vip"}, headers=admin_auth)
    assert bad.status_code == 400

    res = client.get("/api/v1/saas/coupons", headers=auth)
    assert res.status_code == 200, res.text
    coupons = res.json()["result"]["coupons"]
    assert [c["code"] for c in coupons] == ["WELCOME20"]
    assert coupons[0]["discount_pct"] == 20
    assert coupons[0]["title"] == "20% off Premium"
    assert coupons[0]["category"] == "premium" and coupons[0]["discount_type"] == "percent"
    assert coupons[0]["applicable_to"] == ["Premium Monthly"] and coupons[0]["featured"] is True


def test_referral_profile_is_personal_and_does_not_invent_savings(
    client: TestClient, auth: dict[str, str], admin_auth: dict[str, str]
) -> None:
    anonymous = client.get("/api/v1/saas/referral")
    assert anonymous.status_code in (401, 403)

    res = client.get("/api/v1/saas/referral", headers=auth)
    assert res.status_code == 200, res.text
    referral = res.json()["result"]["referral"]
    assert referral["code"].startswith("DSP")
    assert referral["path"] == f"/signup?ref={referral['code']}"
    assert referral["referred_count"] == 0
    assert referral["savings_status"] == "unavailable"
    assert referral["programme"] is None

    assert client.post(
        "/api/v1/saas/coupon",
        json={
            "code": "REFER20",
            "discount_pct": 20,
            "active": True,
            "title": "Give 20% off · Get 20% off",
            "description": "Both accounts receive the published referral discount.",
            "category": "referral",
        },
        headers=admin_auth,
    ).status_code == 200
    again = client.get("/api/v1/saas/referral", headers=auth).json()["result"]["referral"]
    assert again["programme"]["coupon_code"] == "REFER20"
    assert again["programme"]["discount_pct"] == 20
    assert again["savings_status"] == "unavailable"


def test_referral_attribution_is_server_authoritative(
    client: TestClient, auth: dict[str, str], other_auth: dict[str, str]
) -> None:
    from dsp_platform.saas_platform.store import SaasOverlayStore

    profile = client.get("/api/v1/saas/referral", headers=auth)
    assert profile.status_code == 200, profile.text
    code = profile.json()["result"]["referral"]["code"]

    anonymous = client.post("/api/v1/saas/referral/attribute", json={"code": code})
    assert anonymous.status_code in (401, 403)

    spoofed = client.post(
        "/api/v1/saas/referral/attribute",
        json={"code": code, "user_id": "settings-user", "actor_user_id": "settings-user"},
        headers=other_auth,
    )
    assert spoofed.status_code == 200, spoofed.text
    attributed = spoofed.json()["result"]["referral"]
    assert attributed["attributed"] is True
    assert attributed["reason"] == "recorded"
    assert attributed["credit_state"] == "unavailable"
    assert "referrer_user_id" not in attributed

    counted = client.get("/api/v1/saas/referral", headers=auth).json()["result"]["referral"]
    assert counted["referred_count"] == 1
    assert counted["savings_status"] == "unavailable"

    duplicate = client.post(
        "/api/v1/saas/referral/attribute",
        json={"code": code},
        headers=other_auth,
    )
    assert duplicate.status_code == 200, duplicate.text
    assert duplicate.json()["result"]["referral"]["reason"] == "duplicate"
    still = client.get("/api/v1/saas/referral", headers=auth).json()["result"]["referral"]
    assert still["referred_count"] == 1
    assert still["savings_status"] == "unavailable"

    own = client.get("/api/v1/saas/referral", headers=other_auth).json()["result"]["referral"]
    self_referral = client.post(
        "/api/v1/saas/referral/attribute",
        json={"code": own["code"]},
        headers=other_auth,
    )
    assert self_referral.json()["result"]["referral"]["reason"] == "self_referral"

    invalid = client.post(
        "/api/v1/saas/referral/attribute",
        json={"code": "NOTACODE"},
        headers=auth,
    )
    assert invalid.status_code == 200, invalid.text
    assert invalid.json()["result"]["referral"] == {
        "attributed": False,
        "reason": "invalid_code",
        "credit_state": "unavailable",
    }
    unchanged = client.get("/api/v1/saas/referral", headers=auth).json()["result"]["referral"]
    assert unchanged["referred_count"] == 1
    assert unchanged["savings_status"] == "unavailable"

    store = SaasOverlayStore()
    issued = store.referral_profile("referrer-1")
    assert store.attribute_referral(code="nope", referred_user_id="friend-1")["reason"] == "invalid_code"
    assert store.attribute_referral(code=issued["code"], referred_user_id="referrer-1")["reason"] == "self_referral"
    assert store.attribute_referral(code=issued["code"], referred_user_id="friend-1")["attributed"] is True
    assert store.attribute_referral(code=issued["code"], referred_user_id="friend-1")["reason"] == "duplicate"
    assert store.referral_profile("referrer-1")["referred_count"] == 1
    assert store.referral_profile("referrer-1")["savings_status"] == "unavailable"
    snapshot = store.export_referral_state()
    restored = SaasOverlayStore()
    restored.import_referral_state(snapshot)
    assert restored.referral_profile("referrer-1")["referred_count"] == 1
    legacy = SaasOverlayStore()
    legacy.import_referral_state({"referrals": {"referrer-1": ["friend-9"]}})
    assert legacy.referral_profile("referrer-1")["referred_count"] == 1
    assert legacy.attribute_referral(code=issued["code"], referred_user_id="friend-9")["reason"] == "duplicate"


# -- durability ---------------------------------------------------------------


def test_snapshot_roundtrip_includes_new_sections() -> None:
    store = InvestorWorkspaceStore()
    store.put_preferences("u1", {"compact_view": True})
    created = store.upsert_client("u1", name="C", risk_profile="moderate")
    store.add_contact_message(name="N", email="n@example.com", message="hello there world")
    payload = store.export_state()

    restored = InvestorWorkspaceStore()
    restored.import_state(payload)
    assert restored.get_preferences("u1")["compact_view"] is True
    assert restored.get_client("u1", created["client_id"])["name"] == "C"
    assert restored.list_contact_messages()[0]["email"] == "n@example.com"
    # Older snapshots without the new sections still import cleanly.
    legacy = InvestorWorkspaceStore()
    legacy.import_state({"watchlists": {}, "profiles": {}})
    assert legacy.get_preferences("u1")["notifications"] is True


# -- CSRF exemption for credential-establishing endpoints ---------------------


def test_enterprise_login_is_reachable_with_stale_access_cookie(
    platform: DSPPlatform, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A browser holding a stale `dsp_access` cookie (but no matching CSRF
    header) must still reach the login endpoint — the sign-in form is how the
    session gets re-established, so it cannot itself be CSRF-gated."""
    from api_platform.api import csrf_middleware
    from security_platform import ACCESS_COOKIE

    # The middleware reads its switches at construction — set before create_app.
    monkeypatch.setenv("DSP_COOKIE_AUTH", "true")
    monkeypatch.setenv("DSP_CSRF_ENABLED", "true")
    reset_investor_workspace_store_for_tests(InvestorWorkspaceStore())
    client = TestClient(create_app(platform=platform))
    for base in (
        "/auth/enterprise/login",
        "/auth/enterprise/otp/verify",
        "/auth/enterprise/oauth/callback",
        "/auth/enterprise/magic-link/consume",
    ):
        assert base in csrf_middleware._AUTH_EXEMPT
        assert f"/api/v1{base}" in csrf_middleware._AUTH_EXEMPT

    client.cookies.set(ACCESS_COOKIE, "stale-token")
    res = client.post(
        "/api/v1/auth/enterprise/login",
        json={"identifier": "nobody", "password": "WrongPass12!"},
    )
    # Reaches the auth handler (401 invalid credentials), not the CSRF 403.
    assert res.status_code == 401, res.text
    assert res.json().get("error") != "CSRFError"

    # Non-exempt mutating routes remain CSRF-gated for cookie sessions.
    gated = client.post("/api/v1/contact", json={
        "name": "N", "email": "n@example.com", "message": "hello there world",
    })
    assert gated.status_code == 403
    assert gated.json()["error"] == "CSRFError"
    reset_investor_workspace_store_for_tests(None)
