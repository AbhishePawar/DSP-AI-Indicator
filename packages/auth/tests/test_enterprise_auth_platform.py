"""Enterprise multi-provider authentication platform tests."""

from __future__ import annotations

import os

import pytest

from auth import (
    AuthenticationError,
    AuthService,
    DuplicateUserError,
    EnterpriseAuthPlatform,
    ValidationError,
    get_auth_service,
    reset_auth_service_for_tests,
    reset_enterprise_auth_platform_for_tests,
    reset_role_registry_for_tests,
    RoleRegistry,
)
from auth.oauth_providers import OAuthProfile, OAuthProviderRegistry
from auth.otp import OtpService
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
    monkeypatch.setenv("DSP_PASSWORD_HASHER", "pbkdf2")
    monkeypatch.delenv("DSP_GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("DSP_GOOGLE_CLIENT_SECRET", raising=False)
    store = InMemoryStorageProvider()
    registry = RepositoryRegistry(storage=store)
    reset_repository_registry_for_tests(registry)
    ps = PersistenceService(registry)
    reset_persistence_service_for_tests(ps)
    reset_role_registry_for_tests(RoleRegistry())
    auth = AuthService(ps, jwt_secret="test-secret")
    reset_auth_service_for_tests(auth)
    platform = EnterpriseAuthPlatform(
        auth,
        oauth=OAuthProviderRegistry({}),
        otp=OtpService(DevSmsAdapter()),
    )
    # Prevent auto-seed racing tests that expect empty admin set — re-seed explicitly in tests.
    reset_enterprise_auth_platform_for_tests(platform)
    yield
    reset_enterprise_auth_platform_for_tests(None)
    reset_auth_service_for_tests(None)
    reset_role_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    reset_repository_registry_for_tests(None)


def _platform() -> EnterpriseAuthPlatform:
    from auth.enterprise_platform import get_enterprise_auth_platform

    return get_enterprise_auth_platform()


def test_admin_seed_only_when_missing() -> None:
    platform = _platform()
    users = platform.admin_list_users()
    admins = [u for u in users if "administrator" in (u.get("roles") or [])]
    assert len(admins) >= 1
    assert any(u.get("email") == "admin@dspai.local" for u in admins)
    # Second construction must not duplicate
    platform.ensure_dev_admin_seed()
    again = [u for u in platform.admin_list_users() if u.get("email") == "admin@dspai.local"]
    assert len(again) == 1


def test_registration_verify_and_login() -> None:
    platform = _platform()
    reg = platform.register_email(
        name="Ada Lovelace",
        email="ada@example.com",
        password="StrongPass1!",
        confirm_password="StrongPass1!",
        username="ada",
    )
    assert reg["verification_required"] is True
    token = reg["verification_token"]
    # Login blocked until verify
    with pytest.raises(AuthenticationError):
        platform.login_password(identifier="ada", password="StrongPass1!")
    platform.verify_email(token)
    # Activate may leave status active — login by username and email
    session = platform.login_password(identifier="ada@example.com", password="StrongPass1!")
    assert session["tokens"]["access_token"]
    assert session["user"]["email"] == "ada@example.com"


def test_otp_flow_with_dev_sms() -> None:
    platform = _platform()
    start = platform.register_mobile_request("+919876543210")
    debug = (start.get("sms") or {}).get("debug_code")
    platform.register_mobile_complete(
        challenge_id=start["challenge_id"],
        code=debug,
        password="StrongPass1!",
        confirm_password="StrongPass1!",
    )
    challenge = platform.request_mobile_otp("+919876543210")
    assert challenge["challenge_id"]
    debug = (challenge.get("sms") or {}).get("debug_code")
    assert debug and len(debug) == 6
    result = platform.verify_mobile_otp(
        challenge_id=challenge["challenge_id"],
        code=debug,
    )
    assert result["tokens"]["access_token"]
    assert result["provider"] == "PHONE"


def test_otp_rate_limit_and_bruteforce() -> None:
    platform = _platform()
    start = platform.register_mobile_request("+919811122233")
    debug = (start.get("sms") or {}).get("debug_code")
    platform.register_mobile_complete(
        challenge_id=start["challenge_id"],
        code=debug,
        password="StrongPass1!",
        confirm_password="StrongPass1!",
    )
    first = platform.request_mobile_otp("+919811122233")
    code = (first.get("sms") or {}).get("debug_code")
    # Wrong codes until lock
    for _ in range(5):
        with pytest.raises(AuthenticationError):
            platform.verify_mobile_otp(challenge_id=first["challenge_id"], code="000000")
    with pytest.raises(AuthenticationError):
        platform.verify_mobile_otp(challenge_id=first["challenge_id"], code=code)


def test_account_linking_by_email() -> None:
    platform = _platform()
    reg = platform.register_email(
        name="Link User",
        email="link@example.com",
        password="StrongPass1!",
        confirm_password="StrongPass1!",
        username="linkuser",
    )
    platform.verify_email(reg["verification_token"])
    profile = OAuthProfile(
        provider="GOOGLE",
        subject="google-sub-1",
        email="link@example.com",
        email_verified=True,
        name="Link User",
        avatar="https://example.com/a.png",
        raw_claims={},
    )
    result = platform._login_from_oauth_profile(profile)
    assert result["user"]["email"] == "link@example.com"
    links = result["user"].get("linkedProviders") or []
    assert any(l.get("provider") == "GOOGLE" for l in links)
    # No duplicate user
    emails = [u["email"] for u in platform.admin_list_users() if u["email"] == "link@example.com"]
    assert len(emails) == 1


def test_oauth_unavailable_without_credentials() -> None:
    platform = _platform()
    # Empty registry — unknown provider
    with pytest.raises(ValidationError):
        platform.oauth_begin("GOOGLE", redirect_uri="http://localhost/oauth/callback")


def test_request_access_admin_invite_flow() -> None:
    platform = _platform()
    submitted = platform.submit_access_request(
        name="Ent Client",
        email="ent@corp.example",
        organization="Corp",
        reason="Research access",
    )
    request_id = submitted["request"]["request_id"]
    admin = next(u for u in platform.admin_list_users() if "administrator" in u["roles"])
    decided = platform.decide_access_request(
        request_id,
        approve=True,
        actor_user_id=admin["user_id"],
        role="enterprise_client",
    )
    assert decided["request"]["status"] == "invited"
    token = decided["invitation_token"]
    accepted = platform.accept_invitation(
        token=token,
        password="StrongPass1!",
        confirm_password="StrongPass1!",
        username="entclient",
    )
    assert accepted["ok"] is True
    login = platform.login_password(identifier="entclient", password="StrongPass1!")
    assert "enterprise_client" in login["user"]["roles"]


def test_duplicate_access_request_rejected() -> None:
    platform = _platform()
    platform.submit_access_request(name="A", email="dup@example.com")
    with pytest.raises(DuplicateUserError):
        platform.submit_access_request(name="A", email="dup@example.com")


def test_password_reset_and_login_history() -> None:
    platform = _platform()
    reg = platform.register_email(
        name="Reset Me",
        email="reset@example.com",
        password="StrongPass1!",
        confirm_password="StrongPass1!",
        username="resetme",
    )
    platform.verify_email(reg["verification_token"])
    forgot = platform.request_password_reset("reset@example.com")
    token = forgot["reset_token"]
    platform.confirm_password_reset(token, "AnotherStrong1!")
    with pytest.raises(AuthenticationError):
        platform.login_password(identifier="resetme", password="StrongPass1!")
    platform.login_password(identifier="resetme", password="AnotherStrong1!")
    history = platform.login_history(user_id=reg["user"]["user_id"])
    assert any(h.get("success") for h in history)
