"""Unit tests for the shared single-use authentication token service."""

from __future__ import annotations

from datetime import timedelta

import pytest

from auth.audit import AuditLogger
from auth.single_use_tokens import SingleUseTokenError, SingleUseTokenService
from persistence import (
    InMemoryStorageProvider,
    PersistenceService,
    RepositoryRegistry,
)


@pytest.fixture
def persistence() -> PersistenceService:
    return PersistenceService(RepositoryRegistry(storage=InMemoryStorageProvider()))


@pytest.fixture
def audit(persistence: PersistenceService) -> AuditLogger:
    return AuditLogger(persistence)


@pytest.fixture
def tokens(persistence: PersistenceService, audit: AuditLogger) -> SingleUseTokenService:
    return SingleUseTokenService(persistence, audit=audit)


def test_issue_returns_high_entropy_opaque_token(tokens: SingleUseTokenService) -> None:
    token = tokens.issue(purpose="magic_link", ttl=timedelta(minutes=15), data={"email": "a@b.com"})
    assert isinstance(token, str)
    assert len(token) >= 32
    other = tokens.issue(purpose="magic_link", ttl=timedelta(minutes=15), data={"email": "a@b.com"})
    assert token != other


def test_consume_succeeds_exactly_once(tokens: SingleUseTokenService) -> None:
    token = tokens.issue(purpose="magic_link", ttl=timedelta(minutes=15), data={"email": "a@b.com"})
    record = tokens.consume(purpose="magic_link", token=token)
    assert record.data["email"] == "a@b.com"

    with pytest.raises(SingleUseTokenError):
        tokens.consume(purpose="magic_link", token=token)


def test_consume_rejects_unknown_token(tokens: SingleUseTokenService) -> None:
    with pytest.raises(SingleUseTokenError):
        tokens.consume(purpose="magic_link", token="not-a-real-token")


def test_consume_rejects_expired_token(tokens: SingleUseTokenService) -> None:
    token = tokens.issue(purpose="email_verify", ttl=timedelta(seconds=-1), user_id="u1")
    with pytest.raises(SingleUseTokenError):
        tokens.consume(purpose="email_verify", token=token)
    # Expired tokens are burned on first attempt — cannot be retried either.
    with pytest.raises(SingleUseTokenError):
        tokens.consume(purpose="email_verify", token=token)


def test_purpose_is_validated_and_namespaced(tokens: SingleUseTokenService) -> None:
    token = tokens.issue(purpose="password_reset", ttl=timedelta(hours=1), user_id="u1")
    # A token issued for one purpose cannot be redeemed under another.
    with pytest.raises(SingleUseTokenError):
        tokens.consume(purpose="email_verify", token=token)
    # The original purpose still works.
    record = tokens.consume(purpose="password_reset", token=token)
    assert record.user_id == "u1"


def test_issue_rejects_empty_purpose(tokens: SingleUseTokenService) -> None:
    with pytest.raises(ValueError):
        tokens.issue(purpose="", ttl=timedelta(minutes=5))


def test_user_binding_enforced(tokens: SingleUseTokenService) -> None:
    token = tokens.issue(purpose="password_reset", ttl=timedelta(hours=1), user_id="user-a")
    with pytest.raises(SingleUseTokenError):
        tokens.consume(purpose="password_reset", token=token, user_id="user-b")


def test_user_binding_matching_id_succeeds(tokens: SingleUseTokenService) -> None:
    token = tokens.issue(purpose="password_reset", ttl=timedelta(hours=1), user_id="user-a")
    record = tokens.consume(purpose="password_reset", token=token, user_id="user-a")
    assert record.user_id == "user-a"


def test_organization_binding_enforced(tokens: SingleUseTokenService) -> None:
    token = tokens.issue(
        purpose="invitation", ttl=timedelta(hours=72), organization_id="org-1", data={"role": "member"}
    )
    with pytest.raises(SingleUseTokenError):
        tokens.consume(purpose="invitation", token=token, organization_id="org-2")


def test_no_binding_required_when_not_supplied_at_issue(tokens: SingleUseTokenService) -> None:
    """Magic-link-style flows issue without a user_id (account may not exist yet)."""
    token = tokens.issue(purpose="magic_link", ttl=timedelta(minutes=15), data={"email": "x@y.com"})
    record = tokens.consume(purpose="magic_link", token=token, user_id="does-not-matter")
    assert record.data["email"] == "x@y.com"


def test_custom_error_class_and_message(tokens: SingleUseTokenService) -> None:
    class _CustomError(Exception):
        pass

    with pytest.raises(_CustomError, match="custom message"):
        tokens.consume(
            purpose="magic_link",
            token="bogus",
            error_cls=_CustomError,
            error_message="custom message",
        )


def test_revoke_before_use(tokens: SingleUseTokenService) -> None:
    token = tokens.issue(purpose="invitation", ttl=timedelta(hours=1), user_id="u1")
    assert tokens.revoke(purpose="invitation", token=token) is True
    assert tokens.revoke(purpose="invitation", token=token) is False
    with pytest.raises(SingleUseTokenError):
        tokens.consume(purpose="invitation", token=token)


def test_revoke_all_for_user(tokens: SingleUseTokenService) -> None:
    t1 = tokens.issue(purpose="password_reset", ttl=timedelta(hours=1), user_id="u1")
    t2 = tokens.issue(purpose="password_reset", ttl=timedelta(hours=1), user_id="u1")
    tokens.issue(purpose="password_reset", ttl=timedelta(hours=1), user_id="u2")

    revoked = tokens.revoke_all_for_user(purpose="password_reset", user_id="u1")
    assert revoked == 2

    with pytest.raises(SingleUseTokenError):
        tokens.consume(purpose="password_reset", token=t1)
    with pytest.raises(SingleUseTokenError):
        tokens.consume(purpose="password_reset", token=t2)


def test_peek_does_not_consume(tokens: SingleUseTokenService) -> None:
    token = tokens.issue(purpose="email_verify", ttl=timedelta(hours=24), user_id="u1")
    peeked = tokens.peek(purpose="email_verify", token=token)
    assert peeked is not None
    assert peeked.user_id == "u1"
    # Still consumable after peeking.
    record = tokens.consume(purpose="email_verify", token=token)
    assert record.user_id == "u1"


def test_peek_missing_token_returns_none(tokens: SingleUseTokenService) -> None:
    assert tokens.peek(purpose="email_verify", token="missing") is None


def test_raw_token_never_persisted_in_plaintext(
    tokens: SingleUseTokenService, persistence: PersistenceService
) -> None:
    token = tokens.issue(purpose="magic_link", ttl=timedelta(minutes=15), data={"email": "a@b.com"})
    for entity_id in persistence.list_ids("metadata"):
        row = persistence.get("metadata", entity_id)
        assert row is not None
        blob = str(row)
        assert token not in blob
        assert entity_id != token


def test_audit_events_recorded_for_issue_and_consume(
    tokens: SingleUseTokenService, audit: AuditLogger
) -> None:
    token = tokens.issue(purpose="password_reset", ttl=timedelta(hours=1), user_id="u1")
    tokens.consume(purpose="password_reset", token=token, user_id="u1")

    events = audit.list_events(user_id="u1")
    event_types = [e["event_type"] for e in events]
    assert "single_use_token.issued" in event_types
    assert "single_use_token.consumed" in event_types


def test_audit_event_recorded_on_failed_consume(
    tokens: SingleUseTokenService, audit: AuditLogger
) -> None:
    with pytest.raises(SingleUseTokenError):
        tokens.consume(purpose="password_reset", token="does-not-exist")
    events = audit.list_events(event_type="single_use_token.consume_failed")
    assert len(events) == 1


def test_key_rotation_invalidates_tokens_hashed_under_old_key(
    persistence: PersistenceService,
) -> None:
    service_v1 = SingleUseTokenService(persistence, key_version="v1")
    token = service_v1.issue(purpose="magic_link", ttl=timedelta(minutes=15), data={})

    service_v2 = SingleUseTokenService(persistence, key_version="v2")
    # A token minted under v1 cannot be redeemed by a service rotated to v2 —
    # it ages out naturally rather than colliding with the new key/version.
    with pytest.raises(SingleUseTokenError):
        service_v2.consume(purpose="magic_link", token=token)
    # But the original key version can still redeem it.
    record = service_v1.consume(purpose="magic_link", token=token)
    assert record.purpose == "magic_link"


def test_hmac_secret_changes_digest_but_not_behavior(persistence: PersistenceService) -> None:
    keyed = SingleUseTokenService(persistence, secret="super-secret-key")
    token = keyed.issue(purpose="email_verify", ttl=timedelta(hours=1), user_id="u1")
    record = keyed.consume(purpose="email_verify", token=token)
    assert record.user_id == "u1"

    # A service without the secret cannot redeem a token minted with one.
    unkeyed = SingleUseTokenService(persistence)
    token2 = keyed.issue(purpose="email_verify", ttl=timedelta(hours=1), user_id="u2")
    with pytest.raises(SingleUseTokenError):
        unkeyed.consume(purpose="email_verify", token=token2)


def test_concurrent_consume_only_one_winner(tokens: SingleUseTokenService) -> None:
    import threading

    token = tokens.issue(purpose="magic_link", ttl=timedelta(minutes=15), data={"email": "race@x.com"})
    results: list[bool] = []
    lock = threading.Lock()

    def _attempt() -> None:
        try:
            tokens.consume(purpose="magic_link", token=token)
            with lock:
                results.append(True)
        except SingleUseTokenError:
            with lock:
                results.append(False)

    threads = [threading.Thread(target=_attempt) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results.count(True) == 1
    assert results.count(False) == 15
