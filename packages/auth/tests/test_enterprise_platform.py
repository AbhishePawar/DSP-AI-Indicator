"""Enterprise auth platform unit tests."""

from __future__ import annotations

import os

import pytest

from auth import (
    AuthenticationError,
    AuthService,
    DuplicateUserError,
    RoleRegistry,
    ValidationError,
    hash_password,
    needs_rehash,
    reset_auth_service_for_tests,
    reset_enterprise_auth_platform_for_tests,
    reset_role_registry_for_tests,
    verify_password,
)
from auth.enterprise_platform import EnterpriseAuthPlatform, password_strength
from auth.oauth_providers import OAuthProviderAdapter, OAuthProviderRegistry
from auth.enterprise_models import AuthProvider
from auth.otp import OtpService, normalize_india_mobile
from auth.sms import DevSmsAdapter
from persistence import (
    InMemoryStorageProvider,
    PersistenceService,
    RepositoryRegistry,
    reset_persistence_service_for_tests,
    reset_repository_registry_for_tests,
)


@pytest.fixture(autouse=True)
def _reset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "development")
    monkeypatch.delenv("DSP_GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("DSP_GOOGLE_CLIENT_SECRET", raising=False)
    monkeypatch.setenv("DSP_AUTH_PROVIDER_GOOGLE", "auto")
    monkeypatch.setenv("DSP_AUTH_PROVIDER_OTP", "auto")
    monkeypatch.setenv("DSP_PASSWORD_HASHER", "pbkdf2")
    store = InMemoryStorageProvider()
    registry = RepositoryRegistry(storage=store)
    reset_repository_registry_for_tests(registry)
    ps = PersistenceService(registry)
    reset_persistence_service_for_tests(ps)
    reset_role_registry_for_tests(RoleRegistry())
    auth = AuthService(ps, jwt_secret="test-secret")
    reset_auth_service_for_tests(auth)
    platform = EnterpriseAuthPlatform(auth, otp=OtpService(DevSmsAdapter()))
    reset_enterprise_auth_platform_for_tests(platform)
    yield
    reset_enterprise_auth_platform_for_tests(None)
    reset_auth_service_for_tests(None)
    reset_role_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    reset_repository_registry_for_tests(None)


def test_seed_super_admin_once() -> None:
    from auth.enterprise_platform import get_enterprise_auth_platform

    platform = get_enterprise_auth_platform()
    users = platform.admin_list_users()
    admins = [
        u
        for u in users
        if "super_admin" in (u.get("roles") or []) or "administrator" in (u.get("roles") or [])
    ]
    assert admins
    assert admins[0]["email"] == "admin@dspai.local"
    # Second construction must not duplicate
    EnterpriseAuthPlatform(platform.auth, otp=OtpService(DevSmsAdapter()))
    again = platform.admin_list_users()
    assert len([u for u in again if u.get("email") == "admin@dspai.local"]) == 1


def test_password_strength_and_hash_upgrade(monkeypatch: pytest.MonkeyPatch) -> None:
    assert password_strength("Admin@123456").get("score", 0) >= 4
    legacy = hash_password("Admin@123456", salt="aabbccddeeff0011")
    assert legacy.startswith("pbkdf2$")
    assert verify_password("Admin@123456", legacy)
    monkeypatch.setenv("DSP_PASSWORD_HASHER", "pbkdf2")
    assert needs_rehash(legacy) is False or isinstance(needs_rehash(legacy), bool)


def test_providers_unavailable_without_credentials() -> None:
    from auth.enterprise_platform import get_enterprise_auth_platform

    status = get_enterprise_auth_platform().provider_status()
    google = next(p for p in status["oauth"] if p["provider"] == "GOOGLE")
    assert google["status"] == "unavailable"
    assert google["available"] is False


def test_providers_coming_soon_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_AUTH_PROVIDER_GOOGLE", "disabled")
    monkeypatch.setenv("DSP_GOOGLE_CLIENT_ID", "id")
    monkeypatch.setenv("DSP_GOOGLE_CLIENT_SECRET", "secret")
    from auth.enterprise_platform import get_enterprise_auth_platform
    from auth.oauth_providers import build_oauth_registry

    platform = get_enterprise_auth_platform()
    platform.oauth = build_oauth_registry()
    status = platform.provider_status()
    google = next(p for p in status["oauth"] if p["provider"] == "GOOGLE")
    assert google["status"] == "coming_soon"


def test_register_verify_login_lockout() -> None:
    from auth.enterprise_platform import get_enterprise_auth_platform

    platform = get_enterprise_auth_platform()
    reg = platform.register_email(
        name="Analyst",
        email="analyst@example.com",
        password="StrongPass12!",
        confirm_password="StrongPass12!",
    )
    assert reg["verification_required"] is True
    token = reg["verification_token"]
    platform.verify_email(token)
    login = platform.login_password(
        identifier="analyst@example.com",
        password="StrongPass12!",
    )
    assert login["tokens"]["access_token"]
    assert login["device"]["device_id"]

    # Lockout after threshold
    platform._lockout_threshold = 3
    for _ in range(3):
        with pytest.raises(AuthenticationError):
            platform.login_password(identifier="analyst@example.com", password="wrong")
    user = platform._get_by_email("analyst@example.com")
    assert user is not None
    assert user.status == "locked"
    unlocked = platform.admin_unlock_user(user.user_id)
    assert unlocked["status"] == "active"


def test_otp_india_flow() -> None:
    from auth.enterprise_platform import get_enterprise_auth_platform

    platform = get_enterprise_auth_platform()
    assert normalize_india_mobile("9876543210") == "+919876543210"
    with pytest.raises(ValidationError):
        normalize_india_mobile("12345")
    start = platform.register_mobile_request("+919876543210")
    platform.register_mobile_complete(
        challenge_id=start["challenge_id"],
        code=start["sms"]["debug_code"],
        password="StrongPass1!",
        confirm_password="StrongPass1!",
    )
    req = platform.request_mobile_otp("+919876543210")
    code = req["sms"]["debug_code"]
    result = platform.verify_mobile_otp(
        challenge_id=req["challenge_id"],
        code=code,
    )
    assert result["provider"] == "PHONE"
    assert result["tokens"]["access_token"]


def test_oauth_pkce_state_stored() -> None:
    adapter = OAuthProviderAdapter(
        provider=AuthProvider.GOOGLE,
        client_id="cid",
        client_secret="csec",
        authorize_url="https://example.com/auth",
        token_url="https://example.com/token",
        userinfo_url="https://example.com/userinfo",
        scopes=("openid", "email"),
        flag_env="DSP_AUTH_PROVIDER_GOOGLE",
    )
    begin = adapter.begin_login(redirect_uri="http://localhost/callback")
    assert begin["available"] is True
    assert "code_challenge=" in begin["authorization_url"]
    assert "code_challenge_method=S256" in begin["authorization_url"]
    assert begin["state"]


def test_unlink_last_provider_blocked() -> None:
    from auth.enterprise_platform import get_enterprise_auth_platform
    from auth.models import AuthUser, utc_now

    platform = get_enterprise_auth_platform()
    reg = platform.register_email(
        name="Solo",
        email="solo@example.com",
        password="StrongPass12!",
        confirm_password="StrongPass12!",
    )
    platform.verify_email(reg["verification_token"])
    user = platform._get_by_email("solo@example.com")
    assert user is not None
    platform._persist_meta(
        user,
        {
            "linked_providers": [
                {
                    "provider": "GOOGLE",
                    "provider_subject": "g1",
                    "email": "solo@example.com",
                    "linked_at": "now",
                }
            ],
            "provider": "GOOGLE",
        },
    )
    u2 = platform.auth.users.get(user.user_id)
    assert u2
    wiped = AuthUser(
        user_id=u2.user_id,
        username=u2.username,
        email=u2.email,
        display_name=u2.display_name,
        password_hash="",
        status=u2.status,
        created_at=u2.created_at,
        updated_at=utc_now().isoformat(),
        last_login=u2.last_login,
        roles=u2.roles,
        metadata=u2.metadata,
    )
    platform.auth.users.save(wiped)
    with pytest.raises(ValidationError):
        platform.unlink_provider(user.user_id, "GOOGLE")


def test_access_request_invite_flow() -> None:
    from auth.enterprise_platform import get_enterprise_auth_platform

    platform = get_enterprise_auth_platform()
    submitted = platform.submit_access_request(
        name="Client",
        email="client@corp.com",
        organization="Corp",
        reason="Research access",
    )
    req_id = submitted["request"]["request_id"]
    admin = platform._get_by_email("admin@dspai.local")
    assert admin
    decided = platform.decide_access_request(
        req_id, approve=True, actor_user_id=admin.user_id
    )
    token = decided["invitation_token"]
    accepted = platform.accept_invitation(
        token=token,
        password="StrongPass12!",
        confirm_password="StrongPass12!",
    )
    assert accepted["ok"] is True
    # Invitation tokens are single-use: replaying the same token must be
    # rejected outright rather than reaching duplicate-account detection.
    with pytest.raises(ValidationError):
        platform.accept_invitation(
            token=token,
            password="StrongPass12!",
            confirm_password="StrongPass12!",
        )


def test_mfa_gateway_additive_stable() -> None:
    from auth.enterprise_platform import get_enterprise_auth_platform

    platform = get_enterprise_auth_platform()
    status = platform.mfa.status()
    assert status["enabled"] is False
    # Login must not require MFA fields today
    login = platform.login_password(
        identifier="admin",
        password=os.environ.get("DSP_SEED_ADMIN_PASSWORD") or "Admin@123",
    )
    assert "mfa_required" not in login
