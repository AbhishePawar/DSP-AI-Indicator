"""Simple public auth: combined register, username OTP, mobile password recovery."""

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
from auth.otp import OtpService, normalize_india_mobile
from auth.oauth_providers import OAuthProviderRegistry
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
    auth = AuthService(ps, jwt_secret="simple-auth-secret")
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


def _register_combined(
    platform: EnterpriseAuthPlatform,
    *,
    name: str = "Abhishek",
    username: str = "abhishek",
    mobile: str = "+919826912345",
    email: str = "abhishek@gmail.com",
    password: str = "StrongPass1!",
) -> dict:
    req = platform.register_mobile_request(mobile)
    code = (req.get("sms") or {}).get("debug_code")
    assert code
    return platform.register_mobile_complete(
        challenge_id=req["challenge_id"],
        code=code,
        password=password,
        confirm_password=password,
        name=name,
        username=username,
        email=email,
    )


def test_combined_register_username_mobile_email_password(
    platform: EnterpriseAuthPlatform,
) -> None:
    result = _register_combined(platform, username="abhishek123")
    user = result["user"]
    assert result["ok"] is True
    assert user["username"] == "abhishek123"
    assert user["name"] == "Abhishek"
    assert user["email"] == "abhishek@gmail.com"
    assert user["mobile"] == normalize_india_mobile("9826912345")
    assert user.get("phoneVerified") is True
    session = platform.login_password(identifier="abhishek123", password="StrongPass1!")
    assert session["tokens"]["access_token"]


def test_combined_register_username_can_differ_from_mobile(
    platform: EnterpriseAuthPlatform,
) -> None:
    result = _register_combined(platform, username="myusername", mobile="+919811100001")
    assert result["user"]["username"] == "myusername"
    assert result["user"]["mobile"] == "+919811100001"


def test_combined_register_keeps_mobile_digits_as_username_if_chosen(
    platform: EnterpriseAuthPlatform,
) -> None:
    result = _register_combined(
        platform, username="9826912399", mobile="+919826912399", email="keep@example.com"
    )
    assert result["user"]["username"] == "9826912399"
    assert result["user"]["mobile"] == "+919826912399"


def test_combined_register_duplicate_username(platform: EnterpriseAuthPlatform) -> None:
    _register_combined(platform, username="taken", email="one@example.com", mobile="+919800000001")
    req = platform.register_mobile_request("+919800000002")
    code = (req.get("sms") or {}).get("debug_code")
    with pytest.raises(DuplicateUserError, match="username"):
        platform.register_mobile_complete(
            challenge_id=req["challenge_id"],
            code=code,
            password="StrongPass1!",
            confirm_password="StrongPass1!",
            name="Other",
            username="taken",
            email="two@example.com",
        )


def test_combined_register_duplicate_email(platform: EnterpriseAuthPlatform) -> None:
    _register_combined(platform, username="usr1", email="same@example.com", mobile="+919800000011")
    req = platform.register_mobile_request("+919800000012")
    code = (req.get("sms") or {}).get("debug_code")
    with pytest.raises(DuplicateUserError):
        platform.register_mobile_complete(
            challenge_id=req["challenge_id"],
            code=code,
            password="StrongPass1!",
            confirm_password="StrongPass1!",
            name="Other",
            username="user2",
            email="same@example.com",
        )


def test_combined_register_duplicate_mobile(platform: EnterpriseAuthPlatform) -> None:
    _register_combined(platform, username="usr1", email="a@example.com", mobile="+919800000021")
    req = platform.register_mobile_request("+919800000021")
    code = (req.get("sms") or {}).get("debug_code")
    with pytest.raises(DuplicateUserError):
        platform.register_mobile_complete(
            challenge_id=req["challenge_id"],
            code=code,
            password="StrongPass1!",
            confirm_password="StrongPass1!",
            name="Other",
            username="usr2",
            email="b@example.com",
        )


def test_combined_register_invalid_password(platform: EnterpriseAuthPlatform) -> None:
    req = platform.register_mobile_request("+919800000031")
    code = (req.get("sms") or {}).get("debug_code")
    with pytest.raises(ValidationError, match="too weak"):
        platform.register_mobile_complete(
            challenge_id=req["challenge_id"],
            code=code,
            password="short",
            confirm_password="short",
            name="User",
            username="weakuser",
            email="weak@example.com",
        )


def test_combined_register_invalid_otp(platform: EnterpriseAuthPlatform) -> None:
    req = platform.register_mobile_request("+919800000041")
    with pytest.raises(AuthenticationError):
        platform.register_mobile_complete(
            challenge_id=req["challenge_id"],
            code="000000",
            password="StrongPass1!",
            confirm_password="StrongPass1!",
            name="User",
            username="badotp",
            email="badotp@example.com",
        )


def test_combined_register_expired_otp(platform: EnterpriseAuthPlatform) -> None:
    req = platform.register_mobile_request("+919800000051")
    code = (req.get("sms") or {}).get("debug_code")
    past = datetime.now(tz=timezone.utc) + timedelta(minutes=10)
    with pytest.raises(AuthenticationError, match="expired"):
        platform.otp.verify_otp_result(
            challenge_id=req["challenge_id"], code=code, now=past
        )


def test_combined_register_reused_otp(platform: EnterpriseAuthPlatform) -> None:
    req = platform.register_mobile_request("+919800000061")
    code = (req.get("sms") or {}).get("debug_code")
    platform.register_mobile_complete(
        challenge_id=req["challenge_id"],
        code=code,
        password="StrongPass1!",
        confirm_password="StrongPass1!",
        name="User",
        username="reuseotp",
        email="reuseotp@example.com",
    )
    with pytest.raises(AuthenticationError, match="already used"):
        platform.register_mobile_complete(
            challenge_id=req["challenge_id"],
            code=code,
            password="StrongPass1!",
            confirm_password="StrongPass1!",
            name="User",
            username="reuseotp2",
            email="reuseotp2@example.com",
        )


def test_username_password_login(platform: EnterpriseAuthPlatform) -> None:
    _register_combined(platform, username="loginuser", email="loginuser@example.com")
    session = platform.login_password(identifier="loginuser", password="StrongPass1!")
    assert session["tokens"]["access_token"]
    with pytest.raises(AuthenticationError, match="invalid credentials"):
        platform.login_password(identifier="loginuser", password="WrongPass99!")


def test_mobile_otp_login(platform: EnterpriseAuthPlatform) -> None:
    _register_combined(
        platform, username="mobotp", email="mobotp@example.com", mobile="+919800000071"
    )
    req = platform.request_login_otp("+919800000071")
    assert "mobile" not in req
    code = (req.get("sms") or {}).get("debug_code")
    session = platform.verify_login_otp(challenge_id=req["challenge_id"], code=code)
    assert session["tokens"]["access_token"]
    assert session["user"]["username"] == "mobotp"


def test_username_otp_login_sends_to_stored_mobile(
    platform: EnterpriseAuthPlatform,
) -> None:
    _register_combined(
        platform, username="nameotp", email="nameotp@example.com", mobile="+919800000081"
    )
    req = platform.request_login_otp("nameotp")
    assert "mobile" not in req
    assert req["challenge_id"]
    code = (req.get("sms") or {}).get("debug_code")
    assert code
    session = platform.verify_login_otp(challenge_id=req["challenge_id"], code=code)
    assert session["user"]["username"] == "nameotp"


def test_username_otp_unknown_is_opaque(platform: EnterpriseAuthPlatform) -> None:
    req = platform.request_login_otp("nobodyhere")
    assert req["challenge_id"]
    assert "mobile" not in req
    assert not (req.get("sms") or {}).get("debug_code")
    with pytest.raises(AuthenticationError):
        platform.verify_login_otp(challenge_id=req["challenge_id"], code="123456")


def test_unverified_mobile_otp_login_opaque(platform: EnterpriseAuthPlatform) -> None:
    platform.register_username(
        username="nomobile", password="StrongPass1!", confirm_password="StrongPass1!"
    )
    req = platform.request_login_otp("nomobile")
    assert not (req.get("sms") or {}).get("debug_code")


def test_password_reset_by_username_uses_stored_mobile(
    platform: EnterpriseAuthPlatform,
) -> None:
    _register_combined(
        platform, username="resetu", email="resetu@example.com", mobile="+919800000091"
    )
    session = platform.login_password(identifier="resetu", password="StrongPass1!")
    sid = session["session"]["session_id"]
    out = platform.request_password_reset_otp("resetu")
    assert out["ok"] is True
    assert out["challenge_id"]
    assert "mobile" not in out
    code = (out.get("sms") or {}).get("debug_code")
    assert code
    platform.confirm_password_reset_otp(
        challenge_id=out["challenge_id"],
        code=code,
        new_password="NewStrong1!",
        confirm_password="NewStrong1!",
    )
    with pytest.raises(AuthenticationError):
        platform.login_password(identifier="resetu", password="StrongPass1!")
    refreshed = platform.login_password(identifier="resetu", password="NewStrong1!")
    assert refreshed["tokens"]["access_token"]
    stored = platform.auth.sessions.get(sid)
    assert stored is not None and stored.revoked is True


def test_password_reset_by_mobile(platform: EnterpriseAuthPlatform) -> None:
    _register_combined(
        platform, username="resetm", email="resetm@example.com", mobile="+919800000101"
    )
    out = platform.request_password_reset_otp("9800000101")
    code = (out.get("sms") or {}).get("debug_code")
    platform.confirm_password_reset_otp(
        challenge_id=out["challenge_id"],
        code=code,
        new_password="NewStrong1!",
        confirm_password="NewStrong1!",
    )
    session = platform.login_password(identifier="resetm", password="NewStrong1!")
    assert session["tokens"]["access_token"]


def test_password_reset_wrong_otp(platform: EnterpriseAuthPlatform) -> None:
    _register_combined(
        platform, username="resetw", email="resetw@example.com", mobile="+919800000111"
    )
    out = platform.request_password_reset_otp("resetw")
    with pytest.raises(AuthenticationError):
        platform.confirm_password_reset_otp(
            challenge_id=out["challenge_id"],
            code="000000",
            new_password="NewStrong1!",
            confirm_password="NewStrong1!",
        )


def test_password_reset_expired_otp(platform: EnterpriseAuthPlatform) -> None:
    _register_combined(
        platform, username="resete", email="resete@example.com", mobile="+919800000121"
    )
    out = platform.request_password_reset_otp("resete")
    code = (out.get("sms") or {}).get("debug_code")
    past = datetime.now(tz=timezone.utc) + timedelta(minutes=10)
    with pytest.raises(AuthenticationError, match="expired"):
        platform.otp.verify_otp_result(
            challenge_id=out["challenge_id"], code=code, now=past
        )


def test_password_reset_reused_otp(platform: EnterpriseAuthPlatform) -> None:
    _register_combined(
        platform, username="resetr", email="resetr@example.com", mobile="+919800000131"
    )
    out = platform.request_password_reset_otp("resetr")
    code = (out.get("sms") or {}).get("debug_code")
    platform.confirm_password_reset_otp(
        challenge_id=out["challenge_id"],
        code=code,
        new_password="NewStrong1!",
        confirm_password="NewStrong1!",
    )
    with pytest.raises(AuthenticationError, match="already used"):
        platform.confirm_password_reset_otp(
            challenge_id=out["challenge_id"],
            code=code,
            new_password="AnotherStrong1!",
            confirm_password="AnotherStrong1!",
        )


def test_password_reset_unknown_identifier_opaque(
    platform: EnterpriseAuthPlatform,
) -> None:
    out = platform.request_password_reset_otp("ghostuser")
    assert out["ok"] is True
    assert out["challenge_id"]
    assert "mobile" not in out
    with pytest.raises(AuthenticationError):
        platform.confirm_password_reset_otp(
            challenge_id=out["challenge_id"],
            code="123456",
            new_password="NewStrong1!",
            confirm_password="NewStrong1!",
        )


def test_password_reset_otp_rate_limited(platform: EnterpriseAuthPlatform) -> None:
    for i in range(5):
        platform.request_password_reset_otp(f"ratelimituser{i}", ip_hint="1.2.3.4")
    with pytest.raises(AuthenticationError, match="Rate limit"):
        platform.request_password_reset_otp("ratelimituser5", ip_hint="1.2.3.4")


def test_existing_email_password_login_still_works(
    platform: EnterpriseAuthPlatform,
) -> None:
    reg = platform.register_email(
        name="Email User",
        email="legacy@example.com",
        password="StrongPass1!",
        confirm_password="StrongPass1!",
        username="legacyemail",
    )
    platform.verify_email(reg["verification_token"])
    session = platform.login_password(
        identifier="legacy@example.com", password="StrongPass1!"
    )
    assert session["tokens"]["access_token"]


def test_existing_email_reset_still_works(platform: EnterpriseAuthPlatform) -> None:
    reg = platform.register_email(
        name="Email Reset",
        email="legacyreset@example.com",
        password="StrongPass1!",
        confirm_password="StrongPass1!",
        username="legacyreset",
    )
    platform.verify_email(reg["verification_token"])
    out = platform.request_password_reset("legacyreset@example.com")
    assert out["ok"] is True
    token = out["reset_token"]
    platform.confirm_password_reset(token, "NewStrong1!")
    session = platform.login_password(
        identifier="legacyreset@example.com", password="NewStrong1!"
    )
    assert session["tokens"]["access_token"]
