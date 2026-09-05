"""Stage 0N: durable MFA pending state across processes."""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path

import pytest

from auth.exceptions import AuthenticationError, InvalidTokenError, ValidationError
from auth.jwt import JwtService
from auth.mfa import MfaGateway, build_mfa_gateway
from auth.mfa_pending import MfaPendingStore
from auth.mfa_totp import TotpAdapter, totp_at
from auth.mfa_webauthn import WebAuthnAdapter
from persistence import (
    InMemoryStorageProvider,
    PersistenceService,
    RepositoryRegistry,
)


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_AUTH_JWT_SECRET", "test-secret")
    monkeypatch.setenv("DSP_ENVIRONMENT", "development")


def _persistence() -> PersistenceService:
    return PersistenceService(RepositoryRegistry(storage=InMemoryStorageProvider()))


def _jwt() -> JwtService:
    return JwtService("test-secret", issuer="dsp-auth-mfa")


def _webauthn_fixtures():
    path = Path(__file__).with_name("test_mfa_webauthn.py")
    spec = importlib.util.spec_from_file_location("_mfa_webauthn_fixtures", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _gateway(persistence: PersistenceService) -> MfaGateway:
    return MfaGateway(
        totp=TotpAdapter(persistence),
        jwt=_jwt(),
        enabled=True,
        persistence=persistence,
    )


# -- Isolated vs shared A008 (Cloud Run instance A vs B) ---------------------


def test_isolated_totp_adapters_cannot_confirm_each_others_enrollment() -> None:
    a = TotpAdapter(_persistence())
    b = TotpAdapter(_persistence())
    begin = a.begin_enroll("user-enroll-isolated")
    with pytest.raises(ValidationError, match="No pending TOTP enrollment"):
        b.confirm_enroll("user-enroll-isolated", {"code": totp_at(begin["secret"])})


def test_shared_store_totp_begin_on_a_confirm_on_b() -> None:
    persistence = _persistence()
    a = TotpAdapter(persistence)
    b = TotpAdapter(persistence)
    begin = a.begin_enroll("user-enroll-shared")
    confirmed = b.confirm_enroll("user-enroll-shared", {"code": totp_at(begin["secret"])})
    assert confirmed["ok"] is True
    assert a.is_enrolled("user-enroll-shared") is True
    assert b.is_enrolled("user-enroll-shared") is True


def test_wrong_totp_fails_and_pending_remains() -> None:
    adapter = TotpAdapter(_persistence())
    begin = adapter.begin_enroll("user-wrong-code")
    with pytest.raises(AuthenticationError, match="Invalid authenticator code"):
        adapter.confirm_enroll("user-wrong-code", {"code": "000000"})
    confirmed = adapter.confirm_enroll(
        "user-wrong-code", {"code": totp_at(begin["secret"])}
    )
    assert confirmed["ok"] is True


def test_expired_totp_pending_fails() -> None:
    adapter = TotpAdapter(_persistence())
    begin = adapter.begin_enroll("user-expired")
    adapter._pending_store.put_totp_pending(  # noqa: SLF001
        "user-expired", secret=begin["secret"], ttl_seconds=0
    )
    with pytest.raises(ValidationError, match="No pending TOTP enrollment"):
        adapter.confirm_enroll("user-expired", {"code": totp_at(begin["secret"])})


def test_concurrent_totp_confirm_one_success() -> None:
    persistence = _persistence()
    begin = TotpAdapter(persistence).begin_enroll("user-concurrent-enroll")
    code = totp_at(begin["secret"])
    barrier = threading.Barrier(2)

    def attempt() -> str:
        adapter = TotpAdapter(persistence)
        barrier.wait()
        try:
            adapter.confirm_enroll("user-concurrent-enroll", {"code": code})
            return "success"
        except (ValidationError, AuthenticationError):
            return "failure"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [fut.result() for fut in as_completed([pool.submit(attempt), pool.submit(attempt)])]
    assert results.count("success") == 1
    assert results.count("failure") == 1
    assert TotpAdapter(persistence).is_enrolled("user-concurrent-enroll") is True


def test_totp_pending_is_user_bound() -> None:
    persistence = _persistence()
    adapter = TotpAdapter(persistence)
    begin_a = adapter.begin_enroll("user-alice")
    adapter.begin_enroll("user-bob")
    with pytest.raises(AuthenticationError, match="Invalid authenticator code"):
        adapter.confirm_enroll("user-bob", {"code": totp_at(begin_a["secret"])})
    with pytest.raises(ValidationError, match="No pending TOTP enrollment"):
        TotpAdapter(_persistence()).confirm_enroll(
            "user-alice", {"code": totp_at(begin_a["secret"])}
        )
    confirmed = adapter.confirm_enroll("user-alice", {"code": totp_at(begin_a["secret"])})
    assert confirmed["ok"] is True
    assert adapter.is_enrolled("user-bob") is False


# -- Login step-up JWT + single-use jti --------------------------------------


def test_isolated_gateways_cannot_resolve_each_others_stepup() -> None:
    a = _gateway(_persistence())
    b = _gateway(_persistence())
    token = a.issue_mfa_token("user-stepup-isolated")
    with pytest.raises(AuthenticationError, match="Invalid or expired MFA challenge"):
        b.resolve_mfa_token(token)


def test_shared_store_issue_on_a_resolve_on_b() -> None:
    persistence = _persistence()
    a = _gateway(persistence)
    b = _gateway(persistence)
    token = a.issue_mfa_token("user-stepup-shared")
    assert b.resolve_mfa_token(token) == "user-stepup-shared"


def test_stepup_is_single_use_and_replay_fails() -> None:
    gw = _gateway(_persistence())
    token = gw.issue_mfa_token("user-stepup-replay")
    assert gw.resolve_mfa_token(token) == "user-stepup-replay"
    gw.consume_mfa_token(token)
    with pytest.raises(AuthenticationError, match="Invalid or expired MFA challenge"):
        gw.resolve_mfa_token(token)
    with pytest.raises(AuthenticationError, match="Invalid or expired MFA challenge"):
        gw.consume_mfa_token(token)


def test_expired_stepup_jti_fails() -> None:
    persistence = _persistence()
    gw = _gateway(persistence)
    token = gw.issue_mfa_token("user-stepup-expired")
    payload = gw._jwt.decode(token)  # noqa: SLF001
    jti = str(payload["jti"])
    persistence.delete("metadata", f"auth-mfa-stepup-{jti}")
    gw._pending_store.put_stepup(jti=jti, user_id="user-stepup-expired", ttl_seconds=0)  # noqa: SLF001
    with pytest.raises(AuthenticationError, match="Invalid or expired MFA challenge"):
        gw.resolve_mfa_token(token)


def test_expired_stepup_jwt_fails() -> None:
    gw = _gateway(_persistence())
    past = (datetime.now(tz=timezone.utc) - timedelta(seconds=10)).isoformat()
    token = gw._jwt.issue(  # noqa: SLF001
        subject="user-jwt-expired",
        expires_in=1,
        issued_at=past,
        token_use="mfa_stepup",
        token_id="expired-jti",
    )
    with pytest.raises(AuthenticationError, match="Invalid or expired MFA challenge"):
        gw.resolve_mfa_token(token)


def test_access_token_cannot_be_used_as_mfa_token() -> None:
    gw = _gateway(_persistence())
    access = JwtService("test-secret", issuer="dsp-auth-mfa").issue(
        subject="user-session-bind", token_use="access", token_id="not-mfa"
    )
    with pytest.raises(AuthenticationError, match="Invalid MFA challenge token"):
        gw.resolve_mfa_token(access)


def test_stepup_jti_is_user_bound() -> None:
    persistence = _persistence()
    gw = _gateway(persistence)
    token_a = gw.issue_mfa_token("user-a")
    token_b = gw.issue_mfa_token("user-b")
    assert gw.resolve_mfa_token(token_a) == "user-a"
    assert gw.resolve_mfa_token(token_b) == "user-b"
    gw.consume_mfa_token(token_a)
    assert gw.resolve_mfa_token(token_b) == "user-b"
    with pytest.raises(AuthenticationError, match="Invalid or expired MFA challenge"):
        gw.resolve_mfa_token(token_a)


def test_concurrent_stepup_consume_one_success() -> None:
    persistence = _persistence()
    token = _gateway(persistence).issue_mfa_token("user-stepup-concurrent")
    barrier = threading.Barrier(2)

    def attempt() -> str:
        gw = _gateway(persistence)
        barrier.wait()
        try:
            gw.consume_mfa_token(token)
            return "success"
        except AuthenticationError:
            return "failure"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [fut.result() for fut in as_completed([pool.submit(attempt), pool.submit(attempt)])]
    assert results.count("success") == 1
    assert results.count("failure") == 1


# -- WebAuthn ceremony pending -----------------------------------------------


def test_isolated_webauthn_cannot_consume_each_others_ceremony() -> None:
    store_a = MfaPendingStore(_persistence())
    store_b = MfaPendingStore(_persistence())
    store_a.put_webauthn_pending(
        "state-isolated",
        kind="authentication",
        challenge=b"challenge-bytes",
        ttl_seconds=300,
    )
    assert store_b.consume_webauthn_pending("state-isolated") is None
    assert store_a.consume_webauthn_pending("state-isolated") is not None


def test_shared_webauthn_begin_on_a_complete_on_b() -> None:
    persistence = _persistence()
    a = MfaPendingStore(persistence)
    b = MfaPendingStore(persistence)
    a.put_webauthn_pending(
        "state-shared",
        kind="registration",
        challenge=b"shared-challenge",
        ttl_seconds=300,
        user_id="user-webauthn-shared",
    )
    pending = b.consume_webauthn_pending("state-shared")
    assert pending is not None
    assert pending.kind == "registration"
    assert pending.challenge == b"shared-challenge"
    assert pending.user_id == "user-webauthn-shared"
    assert a.consume_webauthn_pending("state-shared") is None


def test_webauthn_wrong_kind_is_rejected() -> None:
    pytest.importorskip("webauthn")
    fx = _webauthn_fixtures()

    persistence = _persistence()
    users = fx._FakeUsers()
    users.add("user-1")
    adapter = WebAuthnAdapter(
        persistence, users, rp_id="localhost", origin="http://localhost:5000"
    )
    adapter.seed_pending(
        "reg-as-auth",
        {
            "kind": "authentication",
            "user_id": "user-1",
            "challenge": fx._b64url_decode(fx._REG_CHALLENGE_B64URL),
            "created_at": time.time(),
        },
    )
    with pytest.raises(AuthenticationError, match="Invalid or expired registration challenge"):
        adapter.complete_registration(
            "user-1", {"state": "reg-as-auth", "credential": fx._REG_CREDENTIAL}
        )


def test_webauthn_wrong_user_cannot_complete_registration() -> None:
    pytest.importorskip("webauthn")
    fx = _webauthn_fixtures()

    persistence = _persistence()
    users = fx._FakeUsers()
    users.add("user-1")
    users.add("user-2")
    adapter = WebAuthnAdapter(
        persistence, users, rp_id="localhost", origin="http://localhost:5000"
    )
    adapter.seed_pending(
        "reg-user-bound",
        {
            "kind": "registration",
            "user_id": "user-1",
            "challenge": fx._b64url_decode(fx._REG_CHALLENGE_B64URL),
            "created_at": time.time(),
        },
    )
    with pytest.raises(AuthenticationError, match="Invalid or expired registration challenge"):
        adapter.complete_registration(
            "user-2", {"state": "reg-user-bound", "credential": fx._REG_CREDENTIAL}
        )


def test_webauthn_expired_and_replay() -> None:
    store = MfaPendingStore(_persistence())
    past = datetime.now(tz=timezone.utc) - timedelta(seconds=10_000)
    store.put_webauthn_pending(
        "state-expired",
        kind="authentication",
        challenge=b"old",
        ttl_seconds=300,
        created_at=past,
    )
    assert store.consume_webauthn_pending("state-expired") is None
    store.put_webauthn_pending(
        "state-replay",
        kind="authentication",
        challenge=b"once",
        ttl_seconds=300,
    )
    assert store.consume_webauthn_pending("state-replay") is not None
    assert store.consume_webauthn_pending("state-replay") is None


def test_concurrent_webauthn_consume_one_success() -> None:
    persistence = _persistence()
    MfaPendingStore(persistence).put_webauthn_pending(
        "state-concurrent",
        kind="authentication",
        challenge=b"once",
        ttl_seconds=300,
    )
    barrier = threading.Barrier(2)

    def attempt() -> str:
        store = MfaPendingStore(persistence)
        barrier.wait()
        return "success" if store.consume_webauthn_pending("state-concurrent") else "failure"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [fut.result() for fut in as_completed([pool.submit(attempt), pool.submit(attempt)])]
    assert results.count("success") == 1
    assert results.count("failure") == 1


def test_shared_webauthn_adapter_seed_on_a_complete_on_b() -> None:
    pytest.importorskip("webauthn")
    fx = _webauthn_fixtures()

    persistence = _persistence()
    users = fx._FakeUsers()
    users.add("user-1")
    a = WebAuthnAdapter(persistence, users, rp_id="localhost", origin="http://localhost:5000")
    b = WebAuthnAdapter(persistence, users, rp_id="localhost", origin="http://localhost:5000")
    a.seed_pending(
        "reg-cross",
        {
            "kind": "registration",
            "user_id": "user-1",
            "challenge": fx._b64url_decode(fx._REG_CHALLENGE_B64URL),
            "created_at": time.time(),
        },
    )
    result = b.complete_registration(
        "user-1", {"state": "reg-cross", "credential": fx._REG_CREDENTIAL}
    )
    assert result["ok"] is True


# -- Persistence hygiene / enable-disable / no secrets in logs ---------------


def test_pending_entity_ids_are_hmac_not_raw_identifiers() -> None:
    persistence = _persistence()
    user_id = "user-visible-in-id-check"
    state = "plain-webauthn-state-token"
    totp = TotpAdapter(persistence)
    begin = totp.begin_enroll(user_id)
    MfaPendingStore(persistence).put_webauthn_pending(
        state, kind="authentication", challenge=b"x", ttl_seconds=300
    )
    _gateway(persistence).issue_mfa_token(user_id)
    ids = persistence.list_ids("metadata")
    assert user_id not in ids
    assert state not in ids
    assert not any(user_id in item for item in ids)
    assert not any(state in item for item in ids)
    assert any(item.startswith("auth-mfa-totp-pending-") for item in ids)
    assert any(item.startswith("auth-webauthn-pending-") for item in ids)
    assert any(item.startswith("auth-mfa-stepup-") for item in ids)
    totp_row = persistence.get(
        "metadata",
        next(item for item in ids if item.startswith("auth-mfa-totp-pending-")),
    )
    payload = str((totp_row or {}).get("payload") or {})
    assert begin["secret"] not in payload
    assert str((totp_row or {}).get("payload", {}).get("secret") or "").startswith("enc:v1:")


def test_pending_logs_do_not_contain_secrets(caplog: pytest.LogCaptureFixture) -> None:
    persistence = _persistence()
    caplog.set_level(logging.INFO)
    adapter = TotpAdapter(persistence)
    begin = adapter.begin_enroll("user-log-secret")
    adapter.confirm_enroll("user-log-secret", {"code": totp_at(begin["secret"])})
    gw = _gateway(persistence)
    token = gw.issue_mfa_token("user-log-secret")
    gw.consume_mfa_token(token)
    joined = " ".join(record.message for record in caplog.records)
    assert begin["secret"] not in joined
    assert token not in joined
    assert "mfa totp pending stored" in joined
    assert "mfa totp pending consumed" in joined
    assert "mfa stepup pending stored" in joined
    assert "mfa stepup pending consumed" in joined


def test_mfa_enable_does_not_reintroduce_process_local_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSP_AUTH_MFA", "true")
    src_dir = Path(__file__).resolve().parents[1] / "src" / "auth"
    for name in ("mfa_totp.py", "mfa_webauthn.py", "mfa.py", "mfa_pending.py"):
        text = (src_dir / name).read_text(encoding="utf-8")
        assert "self._pending =" not in text
        assert "_pending: dict" not in text
        assert "f\"mfa-pending:" not in text
    persistence = _persistence()
    gw = build_mfa_gateway(persistence=persistence, users=None, jwt=_jwt())
    assert gw._pending_store is not None  # noqa: SLF001
    assert not hasattr(gw.totp, "_pending")


def test_disable_clears_pending_enrollment() -> None:
    adapter = TotpAdapter(_persistence())
    begin = adapter.begin_enroll("user-disable")
    adapter.disable("user-disable")
    with pytest.raises(ValidationError, match="No pending TOTP enrollment"):
        adapter.confirm_enroll("user-disable", {"code": totp_at(begin["secret"])})


def test_build_mfa_gateway_disabled_has_no_authoritative_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_AUTH_MFA", "false")
    gw = build_mfa_gateway(persistence=_persistence(), jwt=_jwt())
    assert gw._pending_store is None  # noqa: SLF001
    assert gw.enabled() is False
    token = gw.issue_mfa_token("user-disabled")
    assert gw.resolve_mfa_token(token) == "user-disabled"


def test_wrong_session_jwt_issuer_cannot_consume_stepup() -> None:
    persistence = _persistence()
    gw = _gateway(persistence)
    token = gw.issue_mfa_token("user-issuer")
    other = MfaGateway(
        totp=TotpAdapter(persistence),
        jwt=JwtService("test-secret", issuer="dsp-auth"),
        enabled=True,
        persistence=persistence,
    )
    with pytest.raises((AuthenticationError, InvalidTokenError)):
        other.resolve_mfa_token(token)
    assert gw.resolve_mfa_token(token) == "user-issuer"
