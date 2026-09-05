"""Advanced TOTP MFA coverage: encrypted secrets, recovery-code lifecycle,
trusted-device expiration, rate limiting, and audit trail.

Complements ``test_mfa_totp.py`` (basic enroll/confirm/verify/disable cycle)
without duplicating it.
"""

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
from auth.devices import DeviceRegistry
from auth.mfa_totp import TotpAdapter, totp_at
from auth.oauth_providers import OAuthProviderRegistry
from auth.otp import OtpService
from auth.secret_box import decrypt_secret, encrypt_secret, is_encrypted
from auth.sms import DevSmsAdapter
from persistence import (
    InMemoryStorageProvider,
    PersistenceService,
    RepositoryRegistry,
    reset_persistence_service_for_tests,
    reset_repository_registry_for_tests,
)


@pytest.fixture()
def platform(monkeypatch: pytest.MonkeyPatch):
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
    plat = EnterpriseAuthPlatform(
        auth,
        oauth=OAuthProviderRegistry({}),
        otp=OtpService(DevSmsAdapter()),
    )
    reset_enterprise_auth_platform_for_tests(plat)
    yield plat
    reset_enterprise_auth_platform_for_tests(None)
    reset_auth_service_for_tests(None)
    reset_role_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    reset_repository_registry_for_tests(None)


def _enroll_user(platform: EnterpriseAuthPlatform, suffix: str = "1") -> tuple[str, str, list[str]]:
    reg = platform.register_email(
        name=f"MFA User {suffix}",
        email=f"mfa{suffix}@example.com",
        password="StrongPass1!",
        confirm_password="StrongPass1!",
        username=f"mfauser{suffix}",
    )
    platform.verify_email(reg["verification_token"])
    user_id = reg["user"]["user_id"]
    begin = platform.mfa_totp_enroll_begin(user_id)
    code = totp_at(begin["secret"])
    confirmed = platform.mfa_totp_enroll_confirm(user_id, code)
    return user_id, begin["secret"], confirmed["recovery_codes"]


# -- Encrypted secret storage --------------------------------------------


def test_secret_box_roundtrip() -> None:
    stored = encrypt_secret("JBSWY3DPEHPK3PXP")
    assert decrypt_secret(stored) == "JBSWY3DPEHPK3PXP"


def test_secret_box_refuses_plaintext_when_cryptography_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import auth.secret_box as secret_box

    monkeypatch.setattr(secret_box, "secret_encryption_available", lambda: False)
    with pytest.raises(AuthenticationError, match="cryptography"):
        secret_box.encrypt_secret("MYSECRET")


def test_secret_box_rejects_tampered_ciphertext() -> None:
    stored = encrypt_secret("JBSWY3DPEHPK3PXP")
    tampered = stored[:-4] + "abcd"
    with pytest.raises(AuthenticationError):
        decrypt_secret(tampered)


def test_totp_secret_persisted_encrypted_at_rest(platform: EnterpriseAuthPlatform) -> None:
    user_id, secret, _ = _enroll_user(platform)
    raw = platform.auth.persistence.get("metadata", f"auth-mfa-totp-{user_id}")
    stored_secret = raw["payload"]["secret"]
    assert stored_secret != secret  # never stored in plaintext
    assert is_encrypted(stored_secret)
    assert raw["payload"]["secret_encrypted"] is True
    # And verification still works end-to-end via the encrypted round trip.
    # +30s == exactly one TOTP step (deterministic step-counter advance,
    # unlike a non-multiple offset which can straddle a step boundary).
    stepup_code = totp_at(secret, for_time=time.time() + 30)
    assert platform.mfa.totp.verify_challenge(user_id, {"code": stepup_code}) is True


# -- Recovery code lifecycle ----------------------------------------------


def test_recovery_codes_status_reports_counts(platform: EnterpriseAuthPlatform) -> None:
    user_id, _, codes = _enroll_user(platform)
    status = platform.mfa_recovery_codes_status(user_id)
    assert status["total"] == 10
    assert status["remaining"] == 10
    assert status["generated_at"]

    platform.mfa.totp.verify_challenge(user_id, {"recovery_code": codes[0]})
    status = platform.mfa_recovery_codes_status(user_id)
    assert status["remaining"] == 9


def test_recovery_codes_regenerate_invalidates_old_codes(platform: EnterpriseAuthPlatform) -> None:
    user_id, _, old_codes = _enroll_user(platform)
    result = platform.mfa_recovery_codes_regenerate(user_id, current_password="StrongPass1!")
    new_codes = result["recovery_codes"]
    assert len(new_codes) == 10
    assert set(new_codes).isdisjoint(old_codes)

    # Old codes no longer work.
    assert platform.mfa.totp.verify_challenge(user_id, {"recovery_code": old_codes[0]}) is False
    # New codes do.
    assert platform.mfa.totp.verify_challenge(user_id, {"recovery_code": new_codes[0]}) is True

    events = platform.audit.list_events(user_id=user_id, event_type="mfa.recovery.regenerated")
    assert events


def test_recovery_codes_regenerate_rejects_wrong_password(platform: EnterpriseAuthPlatform) -> None:
    user_id, _, _ = _enroll_user(platform)
    with pytest.raises(AuthenticationError):
        platform.mfa_recovery_codes_regenerate(user_id, current_password="wrong-password")


def test_recovery_codes_status_requires_enrollment(platform: EnterpriseAuthPlatform) -> None:
    reg = platform.register_email(
        name="No MFA",
        email="nomfa@example.com",
        password="StrongPass1!",
        confirm_password="StrongPass1!",
        username="nomfauser",
    )
    platform.verify_email(reg["verification_token"])
    with pytest.raises(ValidationError):
        platform.mfa_recovery_codes_status(reg["user"]["user_id"])


# -- Clock skew tolerance ---------------------------------------------------


def test_totp_accepts_one_step_of_clock_drift(platform: EnterpriseAuthPlatform) -> None:
    user_id, secret, _ = _enroll_user(platform)
    drifted_code = totp_at(secret, for_time=time.time() + 30)  # +1 step
    assert platform.mfa.totp.verify_challenge(user_id, {"code": drifted_code}) is True


def test_totp_rejects_far_future_code(platform: EnterpriseAuthPlatform) -> None:
    user_id, secret, _ = _enroll_user(platform)
    far_future_code = totp_at(secret, for_time=time.time() + 300)  # +10 steps
    assert platform.mfa.totp.verify_challenge(user_id, {"code": far_future_code}) is False


# -- Rate limiting / brute force protection --------------------------------


def test_mfa_verify_stepup_is_rate_limited(platform: EnterpriseAuthPlatform) -> None:
    user_id, secret, _ = _enroll_user(platform)
    login = platform.login_password(identifier=f"mfauser1", password="StrongPass1!")
    mfa_token = login["mfa_token"]
    for _ in range(8):
        try:
            platform.mfa_totp_verify_stepup(mfa_token=mfa_token, code="000000")
        except AuthenticationError:
            pass
    with pytest.raises(AuthenticationError, match="Rate limit"):
        platform.mfa_totp_verify_stepup(mfa_token=mfa_token, code="000000")


def test_mfa_enroll_begin_is_rate_limited(platform: EnterpriseAuthPlatform) -> None:
    reg = platform.register_email(
        name="Rate Test",
        email="rate@example.com",
        password="StrongPass1!",
        confirm_password="StrongPass1!",
        username="rateuser",
    )
    platform.verify_email(reg["verification_token"])
    user_id = reg["user"]["user_id"]
    for _ in range(5):
        platform.mfa_totp_enroll_begin(user_id)
    with pytest.raises(AuthenticationError, match="Rate limit"):
        platform.mfa_totp_enroll_begin(user_id)


# -- Audit trail -------------------------------------------------------------


def test_mfa_lifecycle_emits_expected_audit_events(platform: EnterpriseAuthPlatform) -> None:
    user_id, secret, codes = _enroll_user(platform)

    assert platform.audit.list_events(user_id=user_id, event_type="mfa.enroll.begin")
    assert platform.audit.list_events(user_id=user_id, event_type="mfa.enroll.success")
    assert platform.audit.list_events(user_id=user_id, event_type="mfa.enable")

    login = platform.login_password(identifier="mfauser1", password="StrongPass1!")
    mfa_token = login["mfa_token"]

    with pytest.raises(AuthenticationError):
        platform.mfa_totp_verify_stepup(mfa_token=mfa_token, code="000000")
    assert platform.audit.list_events(user_id=user_id, event_type="mfa.verify.failure")

    stepup_code = totp_at(secret, for_time=time.time() + 30)
    platform.mfa_totp_verify_stepup(mfa_token=mfa_token, code=stepup_code)
    assert platform.audit.list_events(user_id=user_id, event_type="mfa.verify.success")

    login2 = platform.login_password(identifier="mfauser1", password="StrongPass1!")
    mfa_token2 = login2["mfa_token"]
    platform.mfa_totp_verify_stepup(mfa_token=mfa_token2, recovery_code=codes[1])
    assert platform.audit.list_events(user_id=user_id, event_type="mfa.recovery.used")

    platform.mfa_totp_disable(user_id, current_password="StrongPass1!")
    assert platform.audit.list_events(user_id=user_id, event_type="mfa.disable")


# -- Re-enrollment after disable --------------------------------------------


def test_reenroll_after_disable(platform: EnterpriseAuthPlatform) -> None:
    user_id, secret, _ = _enroll_user(platform)
    platform.mfa_totp_disable(user_id, current_password="StrongPass1!")
    assert platform.mfa.totp.is_enrolled(user_id) is False

    begin = platform.mfa_totp_enroll_begin(user_id)
    assert begin["secret"] != secret
    code = totp_at(begin["secret"])
    confirmed = platform.mfa_totp_enroll_confirm(user_id, code)
    assert confirmed["ok"] is True
    assert platform.mfa.totp.is_enrolled(user_id) is True


# -- Trusted device expiration -----------------------------------------------


def test_trusted_device_expires_after_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_AUTH_TRUSTED_DEVICE_DAYS", "30")
    devices = DeviceRegistry()
    device = devices.register(user_id="u1", ip_hint="1.2.3.4", user_agent_hint="pytest-agent")
    devices.set_trusted(device.device_id, user_id="u1", trusted=True)
    assert devices.is_trusted("u1", ip_hint="1.2.3.4", user_agent_hint="pytest-agent") is True

    # Simulate the trust window having elapsed by back-dating trusted_until.
    from datetime import UTC, datetime, timedelta

    record = devices.get(device.device_id)
    assert record is not None
    record.trusted_until = (datetime.now(tz=UTC) - timedelta(days=1)).isoformat()
    devices._store.put_device(record.to_store_payload())  # noqa: SLF001

    assert devices.is_trusted("u1", ip_hint="1.2.3.4", user_agent_hint="pytest-agent") is False
    assert devices.is_record_trusted(record) is False


def test_trusted_device_set_untrusted_clears_expiry() -> None:
    devices = DeviceRegistry()
    device = devices.register(user_id="u1", ip_hint="9.9.9.9", user_agent_hint="pytest-agent")
    devices.set_trusted(device.device_id, user_id="u1", trusted=True)
    result = devices.set_trusted(device.device_id, user_id="u1", trusted=False)
    assert result["trusted"] is False
    assert result["trusted_until"] is None


def test_remembered_device_skips_mfa_on_next_login(platform: EnterpriseAuthPlatform) -> None:
    user_id, secret, _ = _enroll_user(platform)
    login = platform.login_password(
        identifier="mfauser1",
        password="StrongPass1!",
        ip_hint="10.0.0.5",
        user_agent_hint="pytest-agent",
    )
    mfa_token = login["mfa_token"]
    device_id = login["device"]["device_id"]
    stepup_code = totp_at(secret, for_time=time.time() + 30)
    result = platform.mfa_totp_verify_stepup(
        mfa_token=mfa_token,
        code=stepup_code,
        remember_device=True,
        device_id=device_id,
    )
    assert result["ok"] is True

    # Same fingerprint (ip + user-agent) on the next login is now trusted —
    # no further mfa_required challenge until the remembered-device TTL lapses.
    login2 = platform.login_password(
        identifier="mfauser1",
        password="StrongPass1!",
        ip_hint="10.0.0.5",
        user_agent_hint="pytest-agent",
    )
    assert login2.get("mfa_required") is not True
