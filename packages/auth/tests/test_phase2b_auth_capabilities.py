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


def _email_otp_code(platform: EnterpriseAuthPlatform) -> str:
    sent = getattr(platform.email, "_sent", [])
    assert sent, "expected console email delivery"
    body = sent[-1].get("body") or ""
    for line in body.splitlines():
        if line.startswith("OTP="):
            return line.split("=", 1)[1].strip()
    raise AssertionError("OTP= marker missing from console email body")


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


# --- Parts B/C: email OTP + unified OTP ------------------------------------


def test_email_otp_request_and_verify(platform: EnterpriseAuthPlatform) -> None:
    _register_verified(
        platform, email="otpmail@example.com", username="otpmail", password="StrongPass1!"
    )
    req = platform.request_login_otp("otpmail@example.com")
    assert req["challenge_id"]
    assert req["channel"] == "email"
    assert "email_hint" in req
    assert "debug_token" not in (req.get("email") or {})
    assert "OTP=" not in str(req)
    code = _email_otp_code(platform)
    assert len(code) == 6
    session = platform.verify_login_otp(challenge_id=req["challenge_id"], code=code)
    assert session["tokens"]["access_token"]
    assert session["provider"] == "EMAIL"


def test_mobile_otp_still_works_via_unified_api(platform: EnterpriseAuthPlatform) -> None:
    req = platform.request_login_otp("+919876543210")
    assert req["channel"] == "mobile"
    code = (req.get("sms") or {}).get("debug_code")
    assert code
    session = platform.verify_login_otp(challenge_id=req["challenge_id"], code=code)
    assert session["provider"] == "PHONE"
    assert session["tokens"]["access_token"]
    # Synthetic phone identity preserved (Phase 2F linking deferred).
    assert "@phone.dspai.local" in session["user"]["email"]


def test_otp_expires(platform: EnterpriseAuthPlatform) -> None:
    _register_verified(
        platform, email="exp@example.com", username="expuser", password="StrongPass1!"
    )
    req = platform.request_login_otp("exp@example.com")
    code = _email_otp_code(platform)
    past = datetime.now(tz=timezone.utc) + timedelta(minutes=10)
    with pytest.raises(AuthenticationError, match="expired"):
        platform.otp.verify_otp_result(
            challenge_id=req["challenge_id"], code=code, now=past
        )


def test_otp_cannot_be_reused(platform: EnterpriseAuthPlatform) -> None:
    _register_verified(
        platform, email="reuse@example.com", username="reuseu", password="StrongPass1!"
    )
    req = platform.request_login_otp("reuse@example.com")
    code = _email_otp_code(platform)
    platform.verify_login_otp(challenge_id=req["challenge_id"], code=code)
    with pytest.raises(AuthenticationError, match="already used"):
        platform.verify_login_otp(challenge_id=req["challenge_id"], code=code)


def test_otp_attempt_limit(platform: EnterpriseAuthPlatform) -> None:
    _register_verified(
        platform, email="tries@example.com", username="triesu", password="StrongPass1!"
    )
    req = platform.request_login_otp("tries@example.com")
    code = _email_otp_code(platform)
    for _ in range(5):
        with pytest.raises(AuthenticationError):
            platform.verify_login_otp(challenge_id=req["challenge_id"], code="000000")
    with pytest.raises(AuthenticationError):
        platform.verify_login_otp(challenge_id=req["challenge_id"], code=code)


def test_otp_resend_cooldown(platform: EnterpriseAuthPlatform) -> None:
    _register_verified(
        platform, email="cool@example.com", username="coolu", password="StrongPass1!"
    )
    platform.request_login_otp("cool@example.com")
    with pytest.raises(AuthenticationError, match="Resend available"):
        platform.request_login_otp("cool@example.com")


def test_unknown_email_does_not_reveal_existence(platform: EnterpriseAuthPlatform) -> None:
    unknown = platform.request_login_otp("nosuch@example.com")
    known_user = _register_verified(
        platform, email="known@example.com", username="knownu", password="StrongPass1!"
    )
    assert known_user
    known = platform.request_login_otp("known@example.com")
    # Same public shape; no OTP leaked.
    assert set(unknown.keys()) >= {"challenge_id", "channel", "expires_at", "email"}
    assert set(known.keys()) >= {"challenge_id", "channel", "expires_at", "email"}
    assert unknown["channel"] == known["channel"] == "email"
    assert unknown["email"] == known["email"] == {
        "ok": True,
        "detail": "If an account exists, a one-time code was sent.",
    }
    assert "provider" not in unknown["email"]
    assert "debug_token" not in (unknown.get("email") or {})
    # Blackhole challenge never accepts a 6-digit guess.
    with pytest.raises(AuthenticationError):
        platform.verify_login_otp(challenge_id=unknown["challenge_id"], code="123456")


def _public_email_otp_envelope(resp: dict) -> dict:
    """Comparable public fields (exclude per-request ids / address hint)."""
    email = dict(resp.get("email") or {})
    return {
        "channel": resp.get("channel"),
        "consumed": resp.get("consumed"),
        "email": email,
        "has_challenge_id": bool(resp.get("challenge_id")),
        "has_expires_at": bool(resp.get("expires_at")),
        "has_email_hint": "email_hint" in resp,
        "top_keys": sorted(k for k in resp if k not in {"challenge_id", "expires_at", "resend_available_at", "email_hint"}),
    }


def test_email_otp_request_enumeration_safe_across_delivery_outcomes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Public response must be identical for unknown / unverified / verified /
    provider-unavailable / delivery-failure paths."""
    from auth.email_delivery import EmailDeliveryResult, NullEmailAdapter

    class FailingEmailAdapter:
        def provider_name(self) -> str:
            return "failing"

        def is_available(self) -> bool:
            return True

        def send(self, **kwargs):  # noqa: ANN003
            _ = kwargs
            return EmailDeliveryResult(
                ok=False,
                provider="failing",
                detail="SMTP relay rejected recipient — DO NOT LEAK",
            )

    def _fresh(email_adapter) -> EnterpriseAuthPlatform:
        monkeypatch.setenv("DSP_ENVIRONMENT", "development")
        monkeypatch.setenv("DSP_PASSWORD_HASHER", "pbkdf2")
        store = InMemoryStorageProvider()
        registry = RepositoryRegistry(storage=store)
        reset_repository_registry_for_tests(registry)
        ps = PersistenceService(registry)
        reset_persistence_service_for_tests(ps)
        reset_role_registry_for_tests(RoleRegistry())
        auth = AuthService(ps, jwt_secret="phase2b-enum-secret")
        reset_auth_service_for_tests(auth)
        otp = OtpService(DevSmsAdapter(), email=email_adapter)
        plat = EnterpriseAuthPlatform(
            auth,
            oauth=OAuthProviderRegistry({}),
            otp=otp,
            email=email_adapter,
        )
        reset_enterprise_auth_platform_for_tests(plat)
        return plat

    # A — unknown email (console; no send)
    plat_a = _fresh(ConsoleEmailAdapter())
    resp_a = plat_a.request_login_otp("unknown-enum@example.com")

    # B — unverified email
    plat_b = _fresh(ConsoleEmailAdapter())
    plat_b.register_email(
        name="Unv",
        email="unv-enum@example.com",
        password="StrongPass1!",
        confirm_password="StrongPass1!",
        username="unvenum",
    )
    resp_b = plat_b.request_login_otp("unv-enum@example.com")
    login_otp_sends = [
        m for m in getattr(plat_b.email, "_sent", []) if m.get("purpose") == "login_otp"
    ]
    assert login_otp_sends == []

    # C — verified + successful delivery
    plat_c = _fresh(ConsoleEmailAdapter())
    _register_verified(
        plat_c, email="ok-enum@example.com", username="okenum", password="StrongPass1!"
    )
    resp_c = plat_c.request_login_otp("ok-enum@example.com")
    login_otp_sends = [
        m for m in getattr(plat_c.email, "_sent", []) if m.get("purpose") == "login_otp"
    ]
    assert len(login_otp_sends) == 1
    assert _email_otp_code(plat_c)

    # D — verified + provider unavailable
    plat_d = _fresh(NullEmailAdapter())
    _register_verified(
        plat_d, email="null-enum@example.com", username="nullenum", password="StrongPass1!"
    )
    resp_d = plat_d.request_login_otp("null-enum@example.com")

    # E — verified + delivery failure
    plat_e = _fresh(FailingEmailAdapter())
    _register_verified(
        plat_e, email="fail-enum@example.com", username="failenum", password="StrongPass1!"
    )
    resp_e = plat_e.request_login_otp("fail-enum@example.com")

    envelopes = [
        _public_email_otp_envelope(r)
        for r in (resp_a, resp_b, resp_c, resp_d, resp_e)
    ]
    assert all(e == envelopes[0] for e in envelopes), envelopes
    assert envelopes[0]["email"] == {
        "ok": True,
        "detail": "If an account exists, a one-time code was sent.",
    }
    for resp in (resp_a, resp_b, resp_c, resp_d, resp_e):
        blob = str(resp)
        assert "OTP=" not in blob
        assert "debug_token" not in blob
        assert "SMTP" not in blob
        assert "DO NOT LEAK" not in blob
        assert "provider" not in (resp.get("email") or {})
        assert "unavailable" not in blob.lower()

    reset_enterprise_auth_platform_for_tests(None)
    reset_auth_service_for_tests(None)
    reset_role_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    reset_repository_registry_for_tests(None)


def test_unknown_mobile_otp_still_opaque_and_provisions(platform: EnterpriseAuthPlatform) -> None:
    # Existing mobile OTP behavior: challenge is issued; verify may provision.
    # Existence is not disclosed via a distinct error on request.
    req = platform.request_login_otp("+919911122233")
    assert req["challenge_id"]
    assert req["channel"] == "mobile"
    assert "challenge_id" in req


def test_unverified_email_otp_opaque(platform: EnterpriseAuthPlatform) -> None:
    reg = platform.register_email(
        name="Unverified",
        email="unverified@example.com",
        password="StrongPass1!",
        confirm_password="StrongPass1!",
        username="unvemail",
    )
    assert reg["user"]
    # Do not verify email — OTP must not be deliverable.
    before = len(getattr(platform.email, "_sent", []))
    req = platform.request_login_otp("unverified@example.com")
    after = len(getattr(platform.email, "_sent", []))
    assert after == before
    assert req["challenge_id"]
    with pytest.raises(AuthenticationError):
        platform.verify_login_otp(challenge_id=req["challenge_id"], code="123456")


def test_otp_session_is_enterprise_jwt(platform: EnterpriseAuthPlatform) -> None:
    _register_verified(
        platform, email="sess@example.com", username="sessu", password="StrongPass1!"
    )
    req = platform.request_login_otp("sess@example.com")
    code = _email_otp_code(platform)
    session = platform.verify_login_otp(challenge_id=req["challenge_id"], code=code)
    assert "access_token" in session["tokens"]
    assert "refresh_token" in session["tokens"]
    me = platform.auth.current_user(session["tokens"]["access_token"])
    assert me["email"] == "sess@example.com"


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
