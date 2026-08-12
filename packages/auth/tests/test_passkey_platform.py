"""Passkey (WebAuthn) primary sign-in — EnterpriseAuthPlatform-level tests.

Extends the adapter-level coverage in ``test_mfa_webauthn.py`` up to the
platform: full-session issuance for a *primary, passwordless* login
(``webauthn_authenticate_begin/complete`` — the same methods backing the
new ``/auth/passkey/login/*`` routes), the ``passkey.*`` audit trail, and
credential management (register/list/delete). Reuses the exact same
genuine FIDO2 test vectors as ``test_mfa_webauthn.py`` (Duo Labs
``py_webauthn`` test suite, BSD-3-Clause) so signature verification,
origin/RP-ID checks, and counter tracking are exercised for real — not
mocked.
"""

from __future__ import annotations

import time

import pytest

webauthn_lib = pytest.importorskip("webauthn", reason="optional 'webauthn' package not installed")

from auth import (  # noqa: E402
    AuthService,
    RoleRegistry,
    reset_auth_service_for_tests,
    reset_role_registry_for_tests,
)
from auth.enterprise_platform import (  # noqa: E402
    EnterpriseAuthPlatform,
    reset_enterprise_auth_platform_for_tests,
)
from auth.exceptions import AuthenticationError, ValidationError  # noqa: E402
from auth.mfa import MfaGateway  # noqa: E402
from auth.mfa_webauthn import WebAuthnAdapter, _b64url_decode  # noqa: E402
from auth.oauth_providers import OAuthProviderRegistry  # noqa: E402
from auth.otp import OtpService  # noqa: E402
from auth.sms import DevSmsAdapter  # noqa: E402
from persistence import (  # noqa: E402
    InMemoryStorageProvider,
    PersistenceService,
    RepositoryRegistry,
    reset_persistence_service_for_tests,
    reset_repository_registry_for_tests,
)

# --------------------------------------------------------------------- #
# Genuine captured FIDO2 ceremony fixtures (same source as
# test_mfa_webauthn.py — Duo Labs py_webauthn test suite).
# --------------------------------------------------------------------- #

_REG_CREDENTIAL = {
    "id": "9y1xA8Tmg1FEmT-c7_fvWZ_uoTuoih3OvR45_oAK-cwHWhAbXrl2q62iLVTjiyEZ7O7n-CROOY494k7Q3xrs_w",
    "rawId": "9y1xA8Tmg1FEmT-c7_fvWZ_uoTuoih3OvR45_oAK-cwHWhAbXrl2q62iLVTjiyEZ7O7n-CROOY494k7Q3xrs_w",
    "response": {
        "attestationObject": "o2NmbXRkbm9uZWdhdHRTdG10oGhhdXRoRGF0YVjESZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2NFAAAAFwAAAAAAAAAAAAAAAAAAAAAAQPctcQPE5oNRRJk_nO_371mf7qE7qIodzr0eOf6ACvnMB1oQG165dqutoi1U44shGezu5_gkTjmOPeJO0N8a7P-lAQIDJiABIVggSFbUJF-42Ug3pdM8rDRFu_N5oiVEysPDB6n66r_7dZAiWCDUVnB39FlGypL-qAoIO9xWHtJygo2jfDmHl-_eKFRLDA",
        "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIiwiY2hhbGxlbmdlIjoiVHdON240V1R5R0tMYzRaWS1xR3NGcUtuSE00bmdscXN5VjBJQ0psTjJUTzlYaVJ5RnRya2FEd1V2c3FsLWdrTEpYUDZmbkYxTWxyWjUzTW00UjdDdnciLCJvcmlnaW4iOiJodHRwOi8vbG9jYWxob3N0OjUwMDAiLCJjcm9zc09yaWdpbiI6ZmFsc2V9",
    },
    "type": "public-key",
    "clientExtensionResults": {},
    "transports": ["nfc", "usb"],
}
_REG_CHALLENGE_B64URL = (
    "TwN7n4WTyGKLc4ZY-qGsFqKnHM4nglqsyV0ICJlN2TO9XiRyFtrkaDwUvsql-gkLJXP6fnF1MlrZ53Mm4R7Cvw"
)

_AUTH_CREDENTIAL = {
    "id": "EDx9FfAbp4obx6oll2oC4-CZuDidRVV4gZhxC529ytlnqHyqCStDUwfNdm1SNHAe3X5KvueWQdAX3x9R1a2b9Q",
    "rawId": "EDx9FfAbp4obx6oll2oC4-CZuDidRVV4gZhxC529ytlnqHyqCStDUwfNdm1SNHAe3X5KvueWQdAX3x9R1a2b9Q",
    "response": {
        "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MBAAAATg",
        "clientDataJSON": "eyJjaGFsbGVuZ2UiOiJ4aTMwR1BHQUZZUnhWRHBZMXNNMTBEYUx6VlFHNjZudi1fN1JVYXpIMHZJMll2RzhMWWdERW52TjVmWlpOVnV2RUR1TWk5dGUzVkxxYjQyTjBma0xHQSIsImNsaWVudEV4dGVuc2lvbnMiOnt9LCJoYXNoQWxnb3JpdGhtIjoiU0hBLTI1NiIsIm9yaWdpbiI6Imh0dHA6Ly9sb2NhbGhvc3Q6NTAwMCIsInR5cGUiOiJ3ZWJhdXRobi5nZXQifQ",
        "signature": "MEUCIGisVZOBapCWbnJJvjelIzwpixxIwkjCCb5aCHafQu68AiEA88v-2pJNNApPFwAKFiNuf82-2hBxYW5kGwVweeoxCwo",
    },
    "type": "public-key",
    "clientExtensionResults": {},
}
_AUTH_CHALLENGE_B64URL = (
    "xi30GPGAFYRxVDpY1sM10DaLzVQG66nv-_7RUazH0vI2YvG8LYgDEnvN5fZZNVuvEDuMi9te3VLqb42N0fkLGA"
)
_AUTH_PUBLIC_KEY_B64URL = (
    "pQECAyYgASFYIIeDTe-gN8A-zQclHoRnGFWN8ehM1b7yAsa8I8KIvmplIlgg4nFGT5px8o6gpPZZhO01wdy9crDSA_Ngtkx0vGpvPHI"
)


def _stored_credential(cred_id: str, *, sign_count: int = 77) -> dict:
    return {
        "credential_id": cred_id,
        "public_key": _AUTH_PUBLIC_KEY_B64URL,
        "sign_count": sign_count,
        "device_type": "single_device",
        "backed_up": False,
        "transports": [],
        "label": "Test key",
        "created_at": time.time(),
    }


def _index_credential(persistence, cred_id: str, user_id: str) -> None:
    persistence.put(
        kind="metadata",
        entity_id=f"auth-webauthn-cred-index-{cred_id}",
        payload={"auth_entity": "webauthn_cred_index", "user_id": user_id, "credential_id": cred_id},
        refs={"auth_entity": "webauthn_cred_index"},
        created_at=None,
        allow_update=True,
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
    webauthn = WebAuthnAdapter(
        auth.persistence, auth.users, rp_id="localhost", rp_name="Test RP", origin="http://localhost:5000"
    )
    mfa = MfaGateway(webauthn=webauthn, enabled=True)
    plat = EnterpriseAuthPlatform(
        auth, oauth=OAuthProviderRegistry({}), otp=OtpService(DevSmsAdapter()), mfa=mfa
    )
    reset_enterprise_auth_platform_for_tests(plat)
    yield plat
    reset_enterprise_auth_platform_for_tests(None)
    reset_auth_service_for_tests(None)
    reset_role_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    reset_repository_registry_for_tests(None)


def _make_user(platform: EnterpriseAuthPlatform, suffix: str = "1") -> str:
    reg = platform.register_email(
        name=f"Passkey User {suffix}",
        email=f"passkey{suffix}@example.com",
        password="StrongPass1!",
        confirm_password="StrongPass1!",
        username=f"passkeyuser{suffix}",
    )
    platform.verify_email(reg["verification_token"])
    return str(reg["user"]["user_id"])


# --------------------------------------------------------------------- #
# Registration (adding a passkey to an authenticated account)
# --------------------------------------------------------------------- #


def test_register_begin_returns_resident_key_required_options_and_audits(
    platform: EnterpriseAuthPlatform,
) -> None:
    user_id = _make_user(platform)
    begin = platform.webauthn_register_begin(user_id, ip_hint="203.0.113.9")
    assert begin["state"]
    assert begin["authenticatorSelection"]["residentKey"] == "required"
    assert begin["rp"]["id"] == "localhost"
    events = platform.audit.list_events(user_id=user_id, event_type="passkey.register.begin")
    assert len(events) == 1
    assert events[0]["ip_hint"] == "203.0.113.9"


def test_register_complete_with_real_attestation_records_success(platform: EnterpriseAuthPlatform) -> None:
    user_id = _make_user(platform)
    state = "reg-state-1"
    platform.mfa.webauthn._pending[state] = {  # noqa: SLF001 — deterministic ceremony seeding
        "kind": "registration",
        "user_id": user_id,
        "challenge": _b64url_decode(_REG_CHALLENGE_B64URL),
        "created_at": time.time(),
    }
    result = platform.webauthn_register_complete(
        user_id, {"state": state, "credential": _REG_CREDENTIAL}, ip_hint="203.0.113.9"
    )
    assert result["ok"] is True
    assert result["credential_id"] == _REG_CREDENTIAL["id"]

    creds = platform.webauthn_list_credentials(user_id)
    assert len(creds) == 1
    assert "public_key" not in creds[0]  # never exposed

    events = platform.audit.list_events(user_id=user_id, event_type="passkey.register.success")
    assert len(events) == 1


def test_register_complete_invalid_state_records_failure(platform: EnterpriseAuthPlatform) -> None:
    user_id = _make_user(platform)
    with pytest.raises(Exception):
        platform.webauthn_register_complete(
            user_id, {"state": "does-not-exist", "credential": _REG_CREDENTIAL}
        )
    events = platform.audit.list_events(user_id=user_id, event_type="passkey.register.failure")
    assert len(events) == 1


def test_register_requires_mfa_flag_enabled() -> None:
    store = InMemoryStorageProvider()
    registry = RepositoryRegistry(storage=store)
    reset_repository_registry_for_tests(registry)
    ps = PersistenceService(registry)
    reset_persistence_service_for_tests(ps)
    reset_role_registry_for_tests(RoleRegistry())
    auth = AuthService(ps, jwt_secret="test-secret")
    reset_auth_service_for_tests(auth)
    plat = EnterpriseAuthPlatform(auth, oauth=OAuthProviderRegistry({}), otp=OtpService(DevSmsAdapter()))
    try:
        with pytest.raises(ValidationError):
            plat.webauthn_register_begin("some-user")
    finally:
        reset_auth_service_for_tests(None)
        reset_role_registry_for_tests(None)
        reset_persistence_service_for_tests(None)
        reset_repository_registry_for_tests(None)


# --------------------------------------------------------------------- #
# Primary, passwordless login (discoverable / usernameless)
# --------------------------------------------------------------------- #


def test_passkey_login_issues_full_session_and_audits_success(platform: EnterpriseAuthPlatform) -> None:
    user_id = _make_user(platform)
    cred_id = _AUTH_CREDENTIAL["id"]
    platform.mfa.webauthn._save_credentials(user_id, [_stored_credential(cred_id)])  # noqa: SLF001
    _index_credential(platform.auth.persistence, cred_id, user_id)

    state = "auth-state-1"
    platform.mfa.webauthn._pending[state] = {  # noqa: SLF001
        "kind": "authentication",
        "challenge": _b64url_decode(_AUTH_CHALLENGE_B64URL),
        "created_at": time.time(),
    }
    result = platform.webauthn_authenticate_complete(
        {"state": state, "credential": _AUTH_CREDENTIAL},
        remember_me=True,
        ip_hint="203.0.113.5",
        user_agent_hint="pytest-agent",
    )
    assert result["tokens"]["access_token"]
    assert result["tokens"]["refresh_token"]
    assert result["user"]["user_id"] == user_id

    creds = platform.webauthn_list_credentials(user_id)
    assert creds[0]["sign_count"] == 78  # rotated per verification.new_sign_count

    events = platform.audit.list_events(user_id=user_id, event_type="passkey.login.success")
    assert len(events) == 1
    assert events[0]["ip_hint"] == "203.0.113.5"


def test_passkey_login_begin_reports_discoverable_shape(platform: EnterpriseAuthPlatform) -> None:
    begin = platform.webauthn_authenticate_begin(None)
    assert begin["state"]
    assert begin["rpId"] == "localhost"
    assert begin["userVerification"] == "preferred"


def test_passkey_login_unknown_credential_records_failure_no_session(
    platform: EnterpriseAuthPlatform,
) -> None:
    state = "auth-state-2"
    platform.mfa.webauthn._pending[state] = {  # noqa: SLF001
        "kind": "authentication",
        "challenge": _b64url_decode(_AUTH_CHALLENGE_B64URL),
        "created_at": time.time(),
    }
    with pytest.raises(AuthenticationError, match="Unknown passkey credential"):
        platform.webauthn_authenticate_complete({"state": state, "credential": _AUTH_CREDENTIAL})
    events = platform.audit.list_events(event_type="passkey.login.failure")
    assert len(events) == 1


def test_passkey_login_expired_challenge_rejected(platform: EnterpriseAuthPlatform) -> None:
    user_id = _make_user(platform)
    cred_id = _AUTH_CREDENTIAL["id"]
    platform.mfa.webauthn._save_credentials(user_id, [_stored_credential(cred_id)])  # noqa: SLF001
    _index_credential(platform.auth.persistence, cred_id, user_id)

    state = "auth-state-expired"
    platform.mfa.webauthn._pending[state] = {  # noqa: SLF001
        "kind": "authentication",
        "challenge": _b64url_decode(_AUTH_CHALLENGE_B64URL),
        "created_at": time.time() - 10_000,  # far beyond the 300s TTL
    }
    with pytest.raises(AuthenticationError, match="expired"):
        platform.webauthn_authenticate_complete({"state": state, "credential": _AUTH_CREDENTIAL})
    assert platform.audit.list_events(event_type="passkey.login.failure")


def test_passkey_login_replay_of_same_state_rejected(platform: EnterpriseAuthPlatform) -> None:
    """Challenges are single-use — the state is popped on first use, so a
    replayed assertion (same state, same or different credential blob)
    cannot be redeemed twice."""
    user_id = _make_user(platform)
    cred_id = _AUTH_CREDENTIAL["id"]
    platform.mfa.webauthn._save_credentials(user_id, [_stored_credential(cred_id)])  # noqa: SLF001
    _index_credential(platform.auth.persistence, cred_id, user_id)

    state = "auth-state-replay"
    platform.mfa.webauthn._pending[state] = {  # noqa: SLF001
        "kind": "authentication",
        "challenge": _b64url_decode(_AUTH_CHALLENGE_B64URL),
        "created_at": time.time(),
    }
    platform.webauthn_authenticate_complete({"state": state, "credential": _AUTH_CREDENTIAL})
    with pytest.raises(AuthenticationError, match="Invalid or expired authentication challenge"):
        platform.webauthn_authenticate_complete({"state": state, "credential": _AUTH_CREDENTIAL})


def test_passkey_login_counter_replay_rejected(platform: EnterpriseAuthPlatform) -> None:
    """A stored sign_count greater than or equal to the assertion's own
    counter means the authenticator/credential may have been cloned — the
    library must reject the assertion rather than accept a replayed or
    forked authenticator state."""
    user_id = _make_user(platform)
    cred_id = _AUTH_CREDENTIAL["id"]
    # The real vector's own new sign count is 78; pre-seed an equal-or-higher
    # stored counter to force the monotonic-counter check to fail.
    platform.mfa.webauthn._save_credentials(  # noqa: SLF001
        user_id, [_stored_credential(cred_id, sign_count=999)]
    )
    _index_credential(platform.auth.persistence, cred_id, user_id)

    state = "auth-state-counter"
    platform.mfa.webauthn._pending[state] = {  # noqa: SLF001
        "kind": "authentication",
        "challenge": _b64url_decode(_AUTH_CHALLENGE_B64URL),
        "created_at": time.time(),
    }
    with pytest.raises(AuthenticationError, match="Passkey verification failed"):
        platform.webauthn_authenticate_complete({"state": state, "credential": _AUTH_CREDENTIAL})
    assert platform.audit.list_events(event_type="passkey.login.failure")


def test_passkey_login_signature_failure_rejected(platform: EnterpriseAuthPlatform) -> None:
    """A tampered signature must fail verification, not merely be ignored."""
    user_id = _make_user(platform)
    cred_id = _AUTH_CREDENTIAL["id"]
    platform.mfa.webauthn._save_credentials(user_id, [_stored_credential(cred_id)])  # noqa: SLF001
    _index_credential(platform.auth.persistence, cred_id, user_id)

    tampered = {
        "id": _AUTH_CREDENTIAL["id"],
        "rawId": _AUTH_CREDENTIAL["rawId"],
        "response": {
            **_AUTH_CREDENTIAL["response"],
            "signature": _AUTH_CREDENTIAL["response"]["signature"][:-4] + "AAAA",
        },
        "type": "public-key",
        "clientExtensionResults": {},
    }
    state = "auth-state-badsig"
    platform.mfa.webauthn._pending[state] = {  # noqa: SLF001
        "kind": "authentication",
        "challenge": _b64url_decode(_AUTH_CHALLENGE_B64URL),
        "created_at": time.time(),
    }
    with pytest.raises(AuthenticationError, match="Passkey verification failed"):
        platform.webauthn_authenticate_complete({"state": state, "credential": tampered})


def test_passkey_login_invalid_origin_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """An adapter configured for a different deployment origin must reject
    an assertion produced for the fixture's origin (http://localhost:5000)."""
    store = InMemoryStorageProvider()
    registry = RepositoryRegistry(storage=store)
    reset_repository_registry_for_tests(registry)
    ps = PersistenceService(registry)
    reset_persistence_service_for_tests(ps)
    reset_role_registry_for_tests(RoleRegistry())
    auth = AuthService(ps, jwt_secret="test-secret")
    reset_auth_service_for_tests(auth)
    webauthn = WebAuthnAdapter(
        auth.persistence, auth.users, rp_id="localhost", origin="https://app.dspai.example"
    )
    mfa = MfaGateway(webauthn=webauthn, enabled=True)
    plat = EnterpriseAuthPlatform(auth, oauth=OAuthProviderRegistry({}), otp=OtpService(DevSmsAdapter()), mfa=mfa)
    try:
        user_id = _make_user(plat)
        cred_id = _AUTH_CREDENTIAL["id"]
        webauthn._save_credentials(user_id, [_stored_credential(cred_id)])  # noqa: SLF001
        _index_credential(auth.persistence, cred_id, user_id)
        state = "auth-state-origin"
        webauthn._pending[state] = {  # noqa: SLF001
            "kind": "authentication",
            "challenge": _b64url_decode(_AUTH_CHALLENGE_B64URL),
            "created_at": time.time(),
        }
        with pytest.raises(AuthenticationError, match="Passkey verification failed"):
            plat.webauthn_authenticate_complete({"state": state, "credential": _AUTH_CREDENTIAL})
    finally:
        reset_auth_service_for_tests(None)
        reset_role_registry_for_tests(None)
        reset_persistence_service_for_tests(None)
        reset_repository_registry_for_tests(None)


def test_passkey_login_invalid_rp_id_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """A mismatched RP ID must be rejected (rpIdHash in authenticatorData
    won't match SHA-256(rp_id))."""
    store = InMemoryStorageProvider()
    registry = RepositoryRegistry(storage=store)
    reset_repository_registry_for_tests(registry)
    ps = PersistenceService(registry)
    reset_persistence_service_for_tests(ps)
    reset_role_registry_for_tests(RoleRegistry())
    auth = AuthService(ps, jwt_secret="test-secret")
    reset_auth_service_for_tests(auth)
    webauthn = WebAuthnAdapter(
        auth.persistence, auth.users, rp_id="dspai.example", origin="http://localhost:5000"
    )
    mfa = MfaGateway(webauthn=webauthn, enabled=True)
    plat = EnterpriseAuthPlatform(auth, oauth=OAuthProviderRegistry({}), otp=OtpService(DevSmsAdapter()), mfa=mfa)
    try:
        user_id = _make_user(plat)
        cred_id = _AUTH_CREDENTIAL["id"]
        webauthn._save_credentials(user_id, [_stored_credential(cred_id)])  # noqa: SLF001
        _index_credential(auth.persistence, cred_id, user_id)
        state = "auth-state-rpid"
        webauthn._pending[state] = {  # noqa: SLF001
            "kind": "authentication",
            "challenge": _b64url_decode(_AUTH_CHALLENGE_B64URL),
            "created_at": time.time(),
        }
        with pytest.raises(AuthenticationError, match="Passkey verification failed"):
            plat.webauthn_authenticate_complete({"state": state, "credential": _AUTH_CREDENTIAL})
    finally:
        reset_auth_service_for_tests(None)
        reset_role_registry_for_tests(None)
        reset_persistence_service_for_tests(None)
        reset_repository_registry_for_tests(None)


# --------------------------------------------------------------------- #
# Credential management: multiple credentials, device migration, removal
# --------------------------------------------------------------------- #


def test_multiple_passkeys_per_user_are_all_listed(platform: EnterpriseAuthPlatform) -> None:
    user_id = _make_user(platform)
    platform.mfa.webauthn._save_credentials(  # noqa: SLF001
        user_id,
        [
            _stored_credential("cred-phone", sign_count=1),
            _stored_credential("cred-laptop", sign_count=5),
            _stored_credential("cred-yubikey", sign_count=42),
        ],
    )
    creds = platform.webauthn_list_credentials(user_id)
    assert {c["credential_id"] for c in creds} == {"cred-phone", "cred-laptop", "cred-yubikey"}


def test_device_migration_remove_old_device_keep_new_one(platform: EnterpriseAuthPlatform) -> None:
    """Simulates replacing a lost/retired device: the old credential is
    deleted while a newer one remains fully usable."""
    user_id = _make_user(platform)
    platform.mfa.webauthn._save_credentials(  # noqa: SLF001
        user_id,
        [_stored_credential("cred-old-phone"), _stored_credential("cred-new-phone")],
    )
    out = platform.webauthn_remove_credential(user_id, "cred-old-phone", ip_hint="203.0.113.7")
    assert out["ok"] is True

    remaining = platform.webauthn_list_credentials(user_id)
    assert len(remaining) == 1
    assert remaining[0]["credential_id"] == "cred-new-phone"

    events = platform.audit.list_events(user_id=user_id, event_type="passkey.deleted")
    assert len(events) == 1
    assert events[0]["detail"] == "cred-old-phone"


def test_remove_nonexistent_credential_raises_validation_error(platform: EnterpriseAuthPlatform) -> None:
    user_id = _make_user(platform)
    with pytest.raises(ValidationError):
        platform.webauthn_remove_credential(user_id, "does-not-exist")
    assert not platform.audit.list_events(user_id=user_id, event_type="passkey.deleted")


# --------------------------------------------------------------------- #
# Provider discovery
# --------------------------------------------------------------------- #


def test_provider_discovery_reports_passkey_available_when_mfa_enabled(
    platform: EnterpriseAuthPlatform,
) -> None:
    status = platform.provider_status()
    assert status["passkey"]["available"] is True
    assert status["passkey"]["message"] is None
    # Existing frontend contract (`providers.mfa.webauthn_available`) is
    # additive-preserved alongside the new dedicated `passkey` block.
    assert status["mfa"]["webauthn_available"] is True


def test_provider_discovery_reports_passkey_unavailable_when_mfa_disabled() -> None:
    store = InMemoryStorageProvider()
    registry = RepositoryRegistry(storage=store)
    reset_repository_registry_for_tests(registry)
    ps = PersistenceService(registry)
    reset_persistence_service_for_tests(ps)
    reset_role_registry_for_tests(RoleRegistry())
    auth = AuthService(ps, jwt_secret="test-secret")
    reset_auth_service_for_tests(auth)
    plat = EnterpriseAuthPlatform(auth, oauth=OAuthProviderRegistry({}), otp=OtpService(DevSmsAdapter()))
    try:
        status = plat.provider_status()
        assert status["passkey"]["available"] is False
        assert "DSP_AUTH_MFA=true" in (status["passkey"]["message"] or "")
    finally:
        reset_auth_service_for_tests(None)
        reset_role_registry_for_tests(None)
        reset_persistence_service_for_tests(None)
        reset_repository_registry_for_tests(None)
