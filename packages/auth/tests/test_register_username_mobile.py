"""Username and mobile registration flows (password login after OTP proof)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from auth import (
    AuthenticationError,
    AuthService,
    DuplicateUserError,
    EnterpriseAuthPlatform,
    ValidationError,
    reset_auth_service_for_tests,
    reset_enterprise_auth_platform_for_tests,
    reset_role_registry_for_tests,
    RoleRegistry,
)
from auth.email_delivery import ConsoleEmailAdapter
from auth.models import AuthUser
from auth.oauth_providers import OAuthProviderRegistry
from auth.otp import OtpService, normalize_india_mobile
from auth.sms import DevSmsAdapter
from persistence import (
    InMemoryStorageProvider,
    PersistenceService,
    RepositoryRegistry,
    reset_persistence_service_for_tests,
    reset_repository_registry_for_tests,
)


@pytest.fixture()
def platform(monkeypatch: pytest.MonkeyPatch) -> EnterpriseAuthPlatform:
    monkeypatch.setenv("DSP_ENVIRONMENT", "development")
    monkeypatch.setenv("DSP_PASSWORD_HASHER", "pbkdf2")
    monkeypatch.delenv("DSP_AUTH_PROVIDER_OTP", raising=False)
    store = InMemoryStorageProvider()
    registry = RepositoryRegistry(storage=store)
    reset_repository_registry_for_tests(registry)
    ps = PersistenceService(registry)
    reset_persistence_service_for_tests(ps)
    reset_role_registry_for_tests(RoleRegistry())
    auth = AuthService(ps, jwt_secret="register-secret")
    reset_auth_service_for_tests(auth)
    email = ConsoleEmailAdapter()
    otp = OtpService(DevSmsAdapter(), email=email)
    plat = EnterpriseAuthPlatform(
        auth,
        oauth=OAuthProviderRegistry({}),
        otp=otp,
        email=email,
    )
    reset_enterprise_auth_platform_for_tests(plat)
    yield plat
    reset_enterprise_auth_platform_for_tests(None)
    reset_auth_service_for_tests(None)
    reset_role_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    reset_repository_registry_for_tests(None)


def _register_verified(platform: EnterpriseAuthPlatform, *, email: str, username: str, password: str):
    reg = platform.register_email(
        name="User",
        email=email,
        password=password,
        confirm_password=password,
        username=username,
    )
    platform.verify_email(reg["verification_token"])
    return platform._get_by_email(email)


def _attach_unverified_mobile(platform: EnterpriseAuthPlatform, user: AuthUser, mobile: str) -> AuthUser:
    return platform._persist_meta(
        user,
        {"mobile": normalize_india_mobile(mobile), "phone_verified": False},
    )


def test_register_username_then_password_login(platform: EnterpriseAuthPlatform) -> None:
    result = platform.register_username(
        username="newuser1",
        password="StrongPass1!",
        confirm_password="StrongPass1!",
        name="New User",
    )
    assert result["ok"] is True
    assert result["user"]["username"] == "newuser1"
    assert result["user"].get("email") in ("", None)
    session = platform.login_password(identifier="newuser1", password="StrongPass1!")
    assert session["tokens"]["access_token"]
    assert session["provider"] == "USERNAME"


def test_register_username_duplicate_rejected(platform: EnterpriseAuthPlatform) -> None:
    platform.register_username(
        username="dupeuser",
        password="StrongPass1!",
        confirm_password="StrongPass1!",
    )
    with pytest.raises(DuplicateUserError):
        platform.register_username(
            username="dupeuser",
            password="StrongPass1!",
            confirm_password="StrongPass1!",
        )


def test_register_username_weak_password_rejected(platform: EnterpriseAuthPlatform) -> None:
    with pytest.raises(ValidationError, match="too weak"):
        platform.register_username(
            username="weakuser",
            password="short",
            confirm_password="short",
        )


def test_register_mobile_otp_then_password_login(platform: EnterpriseAuthPlatform) -> None:
    mobile = "+919876501122"
    req = platform.register_mobile_request(mobile)
    code = (req.get("sms") or {}).get("debug_code")
    assert code
    completed = platform.register_mobile_complete(
        challenge_id=req["challenge_id"],
        code=code,
        password="StrongPass1!",
        confirm_password="StrongPass1!",
        name="Mobile User",
    )
    assert completed["ok"] is True
    assert completed["user"].get("phoneVerified") is True
    assert completed["user"].get("mobile") == normalize_india_mobile(mobile)
    assert completed["user"].get("email") in ("", None)

    session = platform.login_password(identifier="9876501122", password="StrongPass1!")
    assert session["tokens"]["access_token"]
    assert session["provider"] == "PHONE"


def test_register_mobile_wrong_password_rejected_after(platform: EnterpriseAuthPlatform) -> None:
    mobile = "+919876501133"
    req = platform.register_mobile_request(mobile)
    code = (req.get("sms") or {}).get("debug_code")
    platform.register_mobile_complete(
        challenge_id=req["challenge_id"],
        code=code,
        password="StrongPass1!",
        confirm_password="StrongPass1!",
    )
    with pytest.raises(AuthenticationError, match="invalid credentials"):
        platform.login_password(identifier=mobile, password="WrongPass99!")


def test_unverified_mobile_still_cannot_password_login(platform: EnterpriseAuthPlatform) -> None:
    user = _register_verified(
        platform, email="unvreg@example.com", username="unvreg", password="StrongPass1!"
    )
    assert user
    _attach_unverified_mobile(platform, user, "+919876501144")
    with pytest.raises(AuthenticationError, match="invalid credentials"):
        platform.login_password(identifier="+919876501144", password="StrongPass1!")


def test_register_mobile_existing_updates_password(platform: EnterpriseAuthPlatform) -> None:
    mobile = "+919876501155"
    req1 = platform.register_mobile_request(mobile)
    code1 = (req1.get("sms") or {}).get("debug_code")
    platform.register_mobile_complete(
        challenge_id=req1["challenge_id"],
        code=code1,
        password="StrongPass1!",
        confirm_password="StrongPass1!",
    )
    future = datetime.now(tz=timezone.utc) + timedelta(seconds=31)
    req2 = platform.otp.request_otp(mobile, now=future)
    code2 = (req2.get("sms") or {}).get("debug_code")
    completed = platform.register_mobile_complete(
        challenge_id=req2["challenge_id"],
        code=code2,
        password="AnotherStrong1!",
        confirm_password="AnotherStrong1!",
    )
    assert completed["ok"] is True
    session = platform.login_password(identifier=mobile, password="AnotherStrong1!")
    assert session["tokens"]["access_token"]
    with pytest.raises(AuthenticationError):
        platform.login_password(identifier=mobile, password="StrongPass1!")


def test_register_mobile_duplicate_username_rejected(platform: EnterpriseAuthPlatform) -> None:
    platform.register_username(
        username="takenname",
        password="StrongPass1!",
        confirm_password="StrongPass1!",
    )
    mobile = "+919876501166"
    req = platform.register_mobile_request(mobile)
    code = (req.get("sms") or {}).get("debug_code")
    with pytest.raises(DuplicateUserError, match="username"):
        platform.register_mobile_complete(
            challenge_id=req["challenge_id"],
            code=code,
            password="StrongPass1!",
            confirm_password="StrongPass1!",
            username="takenname",
        )


def test_email_registration_still_works(platform: EnterpriseAuthPlatform) -> None:
    reg = platform.register_email(
        name="Email User",
        email="emailreg@example.com",
        password="StrongPass1!",
        confirm_password="StrongPass1!",
        username="emailreg",
    )
    assert reg["verification_required"] is True
    platform.verify_email(reg["verification_token"])
    session = platform.login_password(
        identifier="emailreg@example.com", password="StrongPass1!"
    )
    assert session["tokens"]["access_token"]


def test_mobile_otp_login_still_works(platform: EnterpriseAuthPlatform) -> None:
    req = platform.request_login_otp("+919876501177")
    code = (req.get("sms") or {}).get("debug_code")
    session = platform.verify_login_otp(challenge_id=req["challenge_id"], code=code)
    assert session["provider"] == "PHONE"
    assert session["tokens"]["access_token"]


def test_password_reset_skips_synthetic_mailbox(platform: EnterpriseAuthPlatform) -> None:
    platform.register_username(
        username="resetskip",
        password="StrongPass1!",
        confirm_password="StrongPass1!",
    )
    before = len(getattr(platform.email, "_sent", []))
    out = platform.request_password_reset("resetskip@username.dspai.local")
    after = len(getattr(platform.email, "_sent", []))
    assert out["ok"] is True
    assert after == before
    assert "reset_token" not in out
