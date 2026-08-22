"""Phase 2B — backend auth capabilities (mobile password, email OTP, unified OTP).

Does not touch frontend, Phase 1 boot decoupling, or investment connectors.
"""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from auth import (
    AuthenticationError,
    AuthService,
    EnterpriseAuthPlatform,
    ValidationError,
    reset_auth_service_for_tests,
    reset_enterprise_auth_platform_for_tests,
    reset_role_registry_for_tests,
    RoleRegistry,
)
from auth.email_delivery import ConsoleEmailAdapter
from auth.models import AuthUser, utc_now
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
    auth = AuthService(ps, jwt_secret="phase2b-secret")
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
        name="Phase2B User",
        email=email,
        password=password,
        confirm_password=password,
        username=username,
    )
    platform.verify_email(reg["verification_token"])
    return platform._get_by_email(email)


def _attach_verified_mobile(platform: EnterpriseAuthPlatform, user: AuthUser, mobile: str) -> AuthUser:
    return platform._persist_meta(
        user,
        {"mobile": normalize_india_mobile(mobile), "phone_verified": True},
    )


def _attach_unverified_mobile(platform: EnterpriseAuthPlatform, user: AuthUser, mobile: str) -> AuthUser:
    return platform._persist_meta(
        user,
        {"mobile": normalize_india_mobile(mobile), "phone_verified": False},
    )


# --- Parts B/C follow after password tests --------------------------------


# --- Part A: password login (username / email / mobile) --------------------


def test_password_username_still_works(platform: EnterpriseAuthPlatform) -> None:
    _register_verified(
        platform, email="user1@example.com", username="user1", password="StrongPass1!"
    )
    session = platform.login_password(identifier="user1", password="StrongPass1!")
    assert session["tokens"]["access_token"]
    assert session["provider"] == "USERNAME"


def test_password_email_still_works(platform: EnterpriseAuthPlatform) -> None:
    _register_verified(
        platform, email="user2@example.com", username="user2", password="StrongPass1!"
    )
    session = platform.login_password(identifier="user2@example.com", password="StrongPass1!")
    assert session["tokens"]["access_token"]
    assert session["provider"] == "EMAIL"


def test_password_mobile_works(platform: EnterpriseAuthPlatform) -> None:
    user = _register_verified(
        platform, email="mobilepw@example.com", username="mobilepw", password="StrongPass1!"
    )
    assert user
    _attach_verified_mobile(platform, user, "+919876543210")
    session = platform.login_password(identifier="+919876543210", password="StrongPass1!")
    assert session["tokens"]["access_token"]
    assert session["provider"] == "PHONE"
    # 10-digit form also accepted
    session2 = platform.login_password(identifier="9876543210", password="StrongPass1!")
    assert session2["tokens"]["access_token"]


def test_password_invalid_password(platform: EnterpriseAuthPlatform) -> None:
    _register_verified(
        platform, email="badpw@example.com", username="badpw", password="StrongPass1!"
    )
    with pytest.raises(AuthenticationError, match="invalid credentials"):
        platform.login_password(identifier="badpw", password="WrongPass99!")


def test_password_unknown_identifier(platform: EnterpriseAuthPlatform) -> None:
    with pytest.raises(AuthenticationError, match="invalid credentials"):
        platform.login_password(identifier="nobody@example.com", password="StrongPass1!")
    with pytest.raises(AuthenticationError, match="invalid credentials"):
        platform.login_password(identifier="+919900011122", password="StrongPass1!")


def test_password_locked_account(platform: EnterpriseAuthPlatform) -> None:
    user = _register_verified(
        platform, email="locked@example.com", username="lockedu", password="StrongPass1!"
    )
    assert user
    platform.auth.users.save(
        AuthUser(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            password_hash=user.password_hash,
            status="locked",
            created_at=user.created_at,
            updated_at=utc_now().isoformat(),
            last_login=user.last_login,
            roles=user.roles,
            metadata=user.metadata,
        )
    )
    with pytest.raises(AuthenticationError, match="locked"):
        platform.login_password(identifier="lockedu", password="StrongPass1!")


def test_password_unverified_mobile_rejected(platform: EnterpriseAuthPlatform) -> None:
    user = _register_verified(
        platform, email="unv@example.com", username="unvmob", password="StrongPass1!"
    )
    assert user
    _attach_unverified_mobile(platform, user, "+919812345678")
    with pytest.raises(AuthenticationError, match="invalid credentials"):
        platform.login_password(identifier="+919812345678", password="StrongPass1!")
    # Username path still works for the same account.
    assert platform.login_password(identifier="unvmob", password="StrongPass1!")["tokens"]


def test_password_ambiguous_mobile_fails_safe(platform: EnterpriseAuthPlatform) -> None:
    u1 = _register_verified(
        platform, email="a1@example.com", username="a1user", password="StrongPass1!"
    )
    u2 = _register_verified(
        platform, email="a2@example.com", username="a2user", password="StrongPass1!"
    )
    assert u1 and u2
    mobile = "+919700011122"
    _attach_verified_mobile(platform, u1, mobile)
    _attach_verified_mobile(platform, u2, mobile)
    with pytest.raises(AuthenticationError, match="invalid credentials"):
        platform.login_password(identifier=mobile, password="StrongPass1!")


def test_password_mobile_remember_me(platform: EnterpriseAuthPlatform) -> None:
    user = _register_verified(
        platform, email="remmob@example.com", username="remmob", password="StrongPass1!"
    )
    assert user
    _attach_verified_mobile(platform, user, "+919811122233")
    session = platform.login_password(
        identifier="+919811122233",
        password="StrongPass1!",
        remember_me=True,
    )
    assert session["tokens"]["access_token"]
    assert session["tokens"]["refresh_token"]
    # remember_me extends refresh TTL; session metadata records the flag.
    sess = platform.auth.sessions.get(session["session"]["session_id"])
    assert sess is not None
    assert dict(sess.metadata or {}).get("remember_me") is True


def test_password_disabled_user_rejected(platform: EnterpriseAuthPlatform) -> None:
    user = _register_verified(
        platform, email="disabled@example.com", username="disabledu", password="StrongPass1!"
    )
    assert user
    user = _attach_verified_mobile(platform, user, "+919822233344")
    platform.auth.users.save(
        AuthUser(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            password_hash=user.password_hash,
            status="disabled",
            created_at=user.created_at,
            updated_at=utc_now().isoformat(),
            last_login=user.last_login,
            roles=user.roles,
            metadata=user.metadata,
        )
    )
    with pytest.raises(AuthenticationError, match="disabled"):
        platform.login_password(identifier="disabledu", password="StrongPass1!")
    with pytest.raises(AuthenticationError, match="disabled"):
        platform.login_password(identifier="+919822233344", password="StrongPass1!")


# --- Parts B/C: email OTP removed; mobile OTP retained --------------------


def test_email_otp_request_rejected(platform: EnterpriseAuthPlatform) -> None:
    _register_verified(
        platform, email="otpmail@example.com", username="otpmail", password="StrongPass1!"
    )
    with pytest.raises(ValidationError, match="Email OTP is no longer supported"):
        platform.request_login_otp("otpmail@example.com")


def test_mobile_otp_still_works_via_unified_api(platform: EnterpriseAuthPlatform) -> None:
    req = platform.request_login_otp("+919876543210")
    assert req["channel"] == "mobile"
    code = (req.get("sms") or {}).get("debug_code")
    assert code
    session = platform.verify_login_otp(challenge_id=req["challenge_id"], code=code)
    assert session["provider"] == "PHONE"
    assert session["tokens"]["access_token"]
    # Synthetic phone identity preserved; public email is redacted.
    assert session["user"].get("phoneVerified") is True
    assert "@phone.dspai.local" not in str(session["user"].get("email") or "")
    assert session["user"].get("email") in ("", None)


def test_mobile_otp_expires(platform: EnterpriseAuthPlatform) -> None:
    req = platform.request_login_otp("+919812345678")
    code = (req.get("sms") or {}).get("debug_code")
    assert code
    past = datetime.now(tz=timezone.utc) + timedelta(minutes=10)
    with pytest.raises(AuthenticationError, match="expired"):
        platform.otp.verify_otp_result(
            challenge_id=req["challenge_id"], code=code, now=past
        )


def test_mobile_otp_cannot_be_reused(platform: EnterpriseAuthPlatform) -> None:
    req = platform.request_login_otp("+919823456789")
    code = (req.get("sms") or {}).get("debug_code")
    assert code
    platform.verify_login_otp(challenge_id=req["challenge_id"], code=code)
    with pytest.raises(AuthenticationError, match="already used"):
        platform.verify_login_otp(challenge_id=req["challenge_id"], code=code)


def test_mobile_otp_attempt_limit(platform: EnterpriseAuthPlatform) -> None:
    req = platform.request_login_otp("+919834567890")
    code = (req.get("sms") or {}).get("debug_code")
    assert code
    for _ in range(5):
        with pytest.raises(AuthenticationError):
            platform.verify_login_otp(challenge_id=req["challenge_id"], code="000000")
    with pytest.raises(AuthenticationError):
        platform.verify_login_otp(challenge_id=req["challenge_id"], code=code)


def test_mobile_otp_resend_cooldown(platform: EnterpriseAuthPlatform) -> None:
    platform.request_login_otp("+919845678901")
    with pytest.raises(AuthenticationError, match="Resend available"):
        platform.request_login_otp("+919845678901")


def test_unknown_mobile_otp_still_opaque_and_provisions(platform: EnterpriseAuthPlatform) -> None:
    # Existing mobile OTP behavior: challenge is issued; verify may provision.
    # Existence is not disclosed via a distinct error on request.
    req = platform.request_login_otp("+919911122233")
    assert req["challenge_id"]
    assert req["channel"] == "mobile"
    assert "challenge_id" in req


def test_otp_session_is_enterprise_jwt(platform: EnterpriseAuthPlatform) -> None:
    req = platform.request_login_otp("+919856789012")
    code = (req.get("sms") or {}).get("debug_code")
    assert code
    session = platform.verify_login_otp(challenge_id=req["challenge_id"], code=code)
    assert "access_token" in session["tokens"]
    assert "refresh_token" in session["tokens"]
    me = platform.auth.current_user(session["tokens"]["access_token"])
    assert me["email"].endswith("@phone.dspai.local")


def test_schema_disables_email_otp_feature(platform: EnterpriseAuthPlatform) -> None:
    features = platform.schema()["features"]
    assert features["email_otp"] is False
    assert features["unified_otp"] is False
    assert features["mobile_otp"] is True
    assert features["google_oauth"] is True


def test_google_oauth_begin_still_gated_without_credentials(
    platform: EnterpriseAuthPlatform,
) -> None:
    with pytest.raises(ValidationError):
        platform.oauth_begin("GOOGLE", redirect_uri="http://localhost/oauth/callback")


def test_auth_package_does_not_import_upstox_or_investment() -> None:
    auth_root = Path(__file__).resolve().parents[1] / "src" / "auth"
    forbidden = ("upstox", "investment", "data_engine.adapters")
    offenders: list[str] = []
    for path in auth_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                lowered = (name or "").lower()
                if any(f in lowered for f in forbidden):
                    offenders.append(f"{path.name}:{name}")
    assert not offenders, f"auth must not import investment adapters: {offenders}"
