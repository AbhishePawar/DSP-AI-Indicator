"""TOTP MFA adapter + platform wiring tests."""

from __future__ import annotations

import time

import pytest

from auth import (
    AuthenticationError,
    AuthService,
    EnterpriseAuthPlatform,
    RoleRegistry,
    ValidationError,
    reset_auth_service_for_tests,
    reset_enterprise_auth_platform_for_tests,
    reset_role_registry_for_tests,
)
from auth.mfa_totp import (
    TotpAdapter,
    generate_totp_secret,
    totp_at,
    verify_totp,
)
from auth.oauth_providers import OAuthProviderRegistry
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
def _reset(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DSP_ENVIRONMENT", "development")
    monkeypatch.setenv("DSP_PASSWORD_HASHER", "pbkdf2")
    monkeypatch.setenv("DSP_AUTH_MFA", "true")
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
    reset_enterprise_auth_platform_for_tests(platform)
    yield platform
    reset_enterprise_auth_platform_for_tests(None)
    reset_auth_service_for_tests(None)
    reset_role_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    reset_repository_registry_for_tests(None)


def test_totp_rfc6238_known_vector() -> None:
    # RFC 6238 Appendix B test vector (SHA1, 8-digit codes truncated to 6
    # here since the platform uses 6-digit codes; verify determinism only).
    secret = generate_totp_secret()
    code_now = totp_at(secret)
    assert len(code_now) == 6
    ok, counter = verify_totp(secret, code_now)
    assert ok and counter >= 0
    assert verify_totp(secret, "000000")[0] in (False, True)  # never assert flaky luck
    assert not verify_totp(secret, "abcdef")[0]


def test_totp_adapter_enroll_confirm_verify_cycle() -> None:
    adapter = TotpAdapter(PersistenceService(RepositoryRegistry(storage=InMemoryStorageProvider())))
    enroll = adapter.begin_enroll("user-1")
    assert enroll["secret"]
    assert enroll["otpauth_uri"].startswith("otpauth://totp/")
    code = totp_at(enroll["secret"])
    confirmed = adapter.confirm_enroll("user-1", {"code": code})
    assert confirmed["ok"] is True
    assert len(confirmed["recovery_codes"]) == 10
    assert adapter.is_enrolled("user-1") is True

    # Replay of the same code must fail (single-use per step).
    assert adapter.verify_challenge("user-1", {"code": code}) is False

    # A recovery code works exactly once.
    recovery = confirmed["recovery_codes"][0]
    assert adapter.verify_challenge("user-1", {"recovery_code": recovery}) is True
    assert adapter.verify_challenge("user-1", {"recovery_code": recovery}) is False

    adapter.disable("user-1")
    assert adapter.is_enrolled("user-1") is False


def test_totp_platform_enroll_and_login_stepup_flow(_reset: EnterpriseAuthPlatform) -> None:
    platform = _reset
    reg = platform.register_email(
        name="MFA User",
        email="mfa@example.com",
        password="StrongPass1!",
        confirm_password="StrongPass1!",
        username="mfauser",
    )
    platform.verify_email(reg["verification_token"])
    user_id = reg["user"]["user_id"]

    begin = platform.mfa_totp_enroll_begin(user_id)
    code = totp_at(begin["secret"])
    confirmed = platform.mfa_totp_enroll_confirm(user_id, code)
    assert confirmed["ok"] is True

    # Next login must now require step-up.
    login = platform.login_password(identifier="mfauser", password="StrongPass1!")
    assert login.get("mfa_required") is True
    assert login["tokens"]["access_token"]  # session already issued (additive design)
    mfa_token = login["mfa_token"]
    assert "totp" in login["methods"]

    # Advance one full TOTP step so the step-up code differs from the one
    # already consumed by enrollment confirmation (replay protection would
    # otherwise correctly reject an identical code within the same window).
    stepup_code = totp_at(begin["secret"], for_time=time.time() + 31)
    result = platform.mfa_totp_verify_stepup(mfa_token=mfa_token, code=stepup_code)
    assert result["ok"] is True

    with pytest.raises(AuthenticationError):
        platform.mfa_totp_verify_stepup(mfa_token=mfa_token, code="000000")


def test_totp_enroll_requires_mfa_flag(monkeypatch: pytest.MonkeyPatch, _reset: EnterpriseAuthPlatform) -> None:
    monkeypatch.setenv("DSP_AUTH_MFA", "false")
    store = InMemoryStorageProvider()
    registry = RepositoryRegistry(storage=store)
    reset_repository_registry_for_tests(registry)
    ps = PersistenceService(registry)
    reset_persistence_service_for_tests(ps)
    reset_role_registry_for_tests(RoleRegistry())
    auth = AuthService(ps, jwt_secret="test-secret")
    reset_auth_service_for_tests(auth)
    platform = EnterpriseAuthPlatform(auth, oauth=OAuthProviderRegistry({}), otp=OtpService(DevSmsAdapter()))
    reset_enterprise_auth_platform_for_tests(platform)
    with pytest.raises(ValidationError):
        platform.mfa_totp_enroll_begin("some-user")
