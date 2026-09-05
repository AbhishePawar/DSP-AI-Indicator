"""Stage 0I: durable OAuth challenge store + A008 production fail-closed tests."""

from __future__ import annotations

import json
import logging
import threading
from urllib.parse import parse_qs, urlparse

import pytest

from auth.enterprise_models import AuthProvider
from auth.exceptions import OAuthChallengeError
from auth.oauth_challenges import OAuthChallengeStore, challenge_id_for_state
from auth.oauth_providers import OAuthProviderAdapter
from auth.service import AuthService, get_auth_service, reset_auth_service_for_tests
from persistence import (
    InMemoryStorageProvider,
    PersistenceService,
    PersistenceError,
    RepositoryRegistry,
    get_persistence_service,
    get_repository_registry,
    reset_persistence_service_for_tests,
    reset_repository_registry_for_tests,
)
from persistence.registry import build_default_storage


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def _google_adapter(store: OAuthChallengeStore | None = None) -> OAuthProviderAdapter:
    return OAuthProviderAdapter(
        provider=AuthProvider.GOOGLE,
        client_id="client-123",
        client_secret="secret",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
        scopes=("openid", "email", "profile"),
        flag_env="DSP_AUTH_PROVIDER_GOOGLE",
        oidc_jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
        oidc_issuers=("https://accounts.google.com", "accounts.google.com"),
        challenge_store=store,
    )


def _shared_persistence() -> PersistenceService:
    return PersistenceService(RepositoryRegistry(storage=InMemoryStorageProvider()))


def _userinfo_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=20: _FakeResponse(
            {
                "sub": "google-sub-1",
                "email": "user@example.com",
                "email_verified": True,
                "name": "Test User",
                "picture": "https://example.com/pic.png",
            }
        ),
    )


def test_begin_callback_success(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _google_adapter(OAuthChallengeStore(_shared_persistence()))
    begin = adapter.begin_login(redirect_uri="http://localhost/callback")
    monkeypatch.setattr(
        adapter,
        "_exchange_code",
        lambda code, redirect_uri, verifier: {"access_token": "at-1"},
    )
    _userinfo_ok(monkeypatch)
    profile = adapter.complete_login(
        code="auth-code", state=begin["state"], redirect_uri="http://localhost/callback"
    )
    assert profile.subject == "google-sub-1"


def test_cross_instance_begin_then_callback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two independent adapters sharing one A008 store: begin on A, callback on B."""
    persistence = _shared_persistence()
    store = OAuthChallengeStore(persistence)
    instance_a = _google_adapter(store)
    instance_b = _google_adapter(store)
    begin = instance_a.begin_login(redirect_uri="http://localhost/callback")
    exchanged: list[str] = []

    def _exchange(code: str, redirect_uri: str, verifier: str) -> dict[str, str]:
        exchanged.append(code)
        assert verifier
        return {"access_token": "at-1"}

    monkeypatch.setattr(instance_b, "_exchange_code", _exchange)
    _userinfo_ok(monkeypatch)
    profile = instance_b.complete_login(
        code="auth-code", state=begin["state"], redirect_uri="http://localhost/callback"
    )
    assert profile.subject == "google-sub-1"
    assert exchanged == ["auth-code"]


def test_replay_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _google_adapter(OAuthChallengeStore(_shared_persistence()))
    begin = adapter.begin_login(redirect_uri="http://localhost/callback")
    monkeypatch.setattr(
        adapter, "_exchange_code", lambda code, redirect_uri, verifier: {"access_token": "at-1"}
    )
    _userinfo_ok(monkeypatch)
    adapter.complete_login(
        code="auth-code", state=begin["state"], redirect_uri="http://localhost/callback"
    )
    with pytest.raises(OAuthChallengeError) as excinfo:
        adapter.complete_login(
            code="auth-code-2", state=begin["state"], redirect_uri="http://localhost/callback"
        )
    assert excinfo.value.reason == "replayed"
    assert "Invalid or expired OAuth state" not in str(excinfo.value)


def test_unknown_state_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _google_adapter(OAuthChallengeStore(_shared_persistence()))
    called = []
    monkeypatch.setattr(
        adapter,
        "_exchange_code",
        lambda code, redirect_uri, verifier: called.append("exchange") or {"access_token": "at-1"},
    )
    with pytest.raises(OAuthChallengeError) as excinfo:
        adapter.complete_login(
            code="auth-code",
            state="never-issued-state",
            redirect_uri="http://localhost/callback",
        )
    assert excinfo.value.reason == "unknown"
    assert called == []


def test_expired_challenge_rejected_without_token_exchange(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    persistence = _shared_persistence()
    adapter = _google_adapter(OAuthChallengeStore(persistence))
    begin = adapter.begin_login(redirect_uri="http://localhost/callback")
    entity_id = f"auth-oauth-google-{challenge_id_for_state(begin['state'])}"
    row = persistence.get("metadata", entity_id)
    assert row is not None
    payload = dict(row["payload"])
    payload["expires_at"] = "2000-01-01T00:00:00+00:00"
    persistence.put(
        kind="metadata",
        entity_id=entity_id,
        payload=payload,
        refs=row.get("refs") or {},
        allow_update=True,
    )
    called = []
    monkeypatch.setattr(
        adapter,
        "_exchange_code",
        lambda code, redirect_uri, verifier: called.append("exchange") or {"access_token": "at-1"},
    )
    with pytest.raises(OAuthChallengeError) as excinfo:
        adapter.complete_login(
            code="auth-code", state=begin["state"], redirect_uri="http://localhost/callback"
        )
    assert excinfo.value.reason == "expired"
    assert called == []


def test_concurrent_consume_exactly_one_success(monkeypatch: pytest.MonkeyPatch) -> None:
    persistence = _shared_persistence()
    store = OAuthChallengeStore(persistence)
    adapter = _google_adapter(store)
    begin = adapter.begin_login(redirect_uri="http://localhost/callback")
    monkeypatch.setattr(
        adapter, "_exchange_code", lambda code, redirect_uri, verifier: {"access_token": "at-1"}
    )
    _userinfo_ok(monkeypatch)
    barrier = threading.Barrier(2)
    outcomes: list[str] = []
    lock = threading.Lock()

    def _worker() -> None:
        barrier.wait()
        try:
            adapter.complete_login(
                code="auth-code",
                state=begin["state"],
                redirect_uri="http://localhost/callback",
            )
            result = "ok"
        except OAuthChallengeError as exc:
            result = exc.reason
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=_worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert outcomes.count("ok") == 1
    assert outcomes.count("replayed") == 1


def test_pkce_verifier_not_in_begin_payload_url_or_logs(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    known_verifier = "test-pkce-verifier-value-not-for-prod"
    monkeypatch.setattr(
        "auth.oauth_providers._pkce_pair",
        lambda: (known_verifier, "fixed-challenge"),
    )
    persistence = _shared_persistence()
    store = OAuthChallengeStore(persistence)
    adapter = _google_adapter(store)
    with caplog.at_level(logging.DEBUG):
        begin = adapter.begin_login(redirect_uri="http://localhost/callback")
    blob = json.dumps(begin)
    assert known_verifier not in blob
    assert "code_verifier" not in blob
    query = parse_qs(urlparse(begin["authorization_url"]).query)
    assert "code_verifier" not in query
    assert query.get("code_challenge") == ["fixed-challenge"]
    entity_id = f"auth-oauth-google-{challenge_id_for_state(begin['state'])}"
    row = persistence.get("metadata", entity_id)
    assert row is not None
    payload = dict(row["payload"])
    assert known_verifier not in json.dumps(payload)
    assert payload.get("verifier_ciphertext")
    assert payload["challenge_id"] != begin["state"]
    joined_logs = "\n".join(record.getMessage() for record in caplog.records)
    assert known_verifier not in joined_logs
    assert "code_verifier" not in joined_logs
    monkeypatch.setattr(
        adapter, "_exchange_code", lambda code, redirect_uri, verifier: {"access_token": "at-1"}
    )
    _userinfo_ok(monkeypatch)
    profile = adapter.complete_login(
        code="auth-code", state=begin["state"], redirect_uri="http://localhost/callback"
    )
    assert known_verifier not in json.dumps(profile.to_dict())


def test_challenge_id_is_hmac_not_raw_state() -> None:
    state = "raw-oauth-state-value"
    derived = challenge_id_for_state(state)
    assert derived != state
    assert len(derived) == 64
    assert challenge_id_for_state(state) == derived


def test_production_missing_postgres_does_not_use_in_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.delenv("DSP_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DSP_AUTH_JWT_SECRET", "unit-test-production-secret-not-default")
    reset_repository_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    reset_auth_service_for_tests(None)
    with pytest.raises(PersistenceError, match="DSP_DATABASE_URL"):
        build_default_storage()
    with pytest.raises(PersistenceError, match="DSP_DATABASE_URL"):
        get_repository_registry()
    with pytest.raises(PersistenceError, match="DSP_DATABASE_URL"):
        get_persistence_service()
    with pytest.raises(PersistenceError, match="DSP_DATABASE_URL"):
        get_auth_service()


def test_production_postgres_connect_failure_does_not_fall_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_DATABASE_URL", "postgresql://dsp:secret@localhost/dsp")
    monkeypatch.setenv("DSP_AUTH_JWT_SECRET", "unit-test-production-secret-not-default")
    reset_repository_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    reset_auth_service_for_tests(None)

    def _boom(dsn: str, **kwargs: object) -> None:
        raise PersistenceError("postgres A008 connect failed")

    monkeypatch.setattr("persistence.postgres_storage.build_postgres_storage", _boom)
    with pytest.raises(PersistenceError, match="connect failed"):
        get_repository_registry()
    storage = None
    try:
        storage = build_default_storage()
    except PersistenceError:
        storage = None
    assert storage is None or getattr(storage, "provider_id", None) != "in_memory"


def test_production_auth_uses_postgres_backed_a008(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakePostgres(InMemoryStorageProvider):
        provider_id = "postgres"

    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_DATABASE_URL", "postgresql://dsp:secret@localhost/dsp")
    monkeypatch.setenv("DSP_AUTH_JWT_SECRET", "unit-test-production-secret-not-default")
    reset_repository_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    reset_auth_service_for_tests(None)
    monkeypatch.setattr(
        "persistence.postgres_storage.build_postgres_storage",
        lambda dsn, **kwargs: _FakePostgres(),
    )
    registry = get_repository_registry()
    assert registry.storage.provider_id == "postgres"
    auth = get_auth_service()
    assert auth.persistence.registry.storage.provider_id == "postgres"
    assert auth.users._persistence.registry.storage.provider_id == "postgres"
    assert auth.sessions._persistence.registry.storage.provider_id == "postgres"


def test_auth_users_sessions_audits_share_injected_store() -> None:
    from datetime import timedelta

    from auth.audit import AuditLogger
    from auth.single_use_tokens import SingleUseTokenService

    store = InMemoryStorageProvider()
    persistence = PersistenceService(RepositoryRegistry(storage=store))
    auth = AuthService(persistence, jwt_secret="test-secret")
    user = auth.users.create(
        username="durable_user",
        email="durable@example.com",
        password="StrongPass12!",
    )
    session = auth.sessions.create(user_id=user.user_id)
    AuditLogger(persistence).record("login", user_id=user.user_id, detail="ok")
    SingleUseTokenService(persistence).issue(
        purpose="email_verify",
        ttl=timedelta(minutes=10),
        user_id=user.user_id,
    )
    assert store.get("entities:metadata", f"auth-user-{user.user_id}") is not None
    assert store.get("entities:metadata", f"auth-session-{session.session_id}") is not None
    audit_ids = [
        key
        for key in store.list_keys("entities:audit_record")
        if str(key).startswith("auth-audit-")
    ]
    assert audit_ids
    token_ids = [
        key
        for key in store.list_keys("entities:metadata")
        if str(key).startswith("auth-token-")
    ]
    assert token_ids
