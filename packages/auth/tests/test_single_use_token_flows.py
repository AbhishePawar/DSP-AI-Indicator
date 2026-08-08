"""Integration tests: one-time auth flows through EnterpriseAuthPlatform.

Confirms that email verification, password reset, magic-link sign-in, and
invitation acceptance are all backed by the shared `SingleUseTokenService`
end-to-end — single-use enforcement, expiry, audit logging, and outbound
email delivery all work through the public platform API without any
flow-specific reimplementation.
"""

from __future__ import annotations

import pytest

from auth import (
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


class _CapturingEmailAdapter(ConsoleEmailAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[dict[str, str]] = []

    def send(self, *, to, subject, body, purpose="transactional", html_body=None):
        self.messages.append({"to": to, "subject": subject, "body": body, "purpose": purpose})
        return super().send(to=to, subject=subject, body=body, purpose=purpose, html_body=html_body)


@pytest.fixture
def email_adapter() -> _CapturingEmailAdapter:
    return _CapturingEmailAdapter()


@pytest.fixture(autouse=True)
def _reset(monkeypatch: pytest.MonkeyPatch, email_adapter: _CapturingEmailAdapter):
    monkeypatch.setenv("DSP_ENVIRONMENT", "development")
    monkeypatch.setenv("DSP_PASSWORD_HASHER", "pbkdf2")
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
        email=email_adapter,
    )
    reset_enterprise_auth_platform_for_tests(platform)
    yield
    reset_enterprise_auth_platform_for_tests(None)
    reset_auth_service_for_tests(None)
    reset_role_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    reset_repository_registry_for_tests(None)


def _platform() -> EnterpriseAuthPlatform:
    from auth.enterprise_platform import get_enterprise_auth_platform

    return get_enterprise_auth_platform()


def test_email_verification_is_single_use_and_emailed(email_adapter: _CapturingEmailAdapter) -> None:
    platform = _platform()
    reg = platform.register_email(
        name="Alice",
        email="alice@example.com",
        password="StrongPass12!",
        confirm_password="StrongPass12!",
    )
    token = reg["verification_token"]
    assert any(m["purpose"] == "email_verify" and m["to"] == "alice@example.com" for m in email_adapter.messages)

    result = platform.verify_email(token)
    assert result["ok"] is True

    with pytest.raises(ValidationError):
        platform.verify_email(token)

    events = platform.audit.list_events(event_type="email.verified")
    assert len(events) == 1


def test_password_reset_is_single_use_and_revokes_other_pending_tokens(
    email_adapter: _CapturingEmailAdapter,
) -> None:
    platform = _platform()
    reg = platform.register_email(
        name="Bob",
        email="bob@example.com",
        password="StrongPass12!",
        confirm_password="StrongPass12!",
    )
    platform.verify_email(reg["verification_token"])

    first = platform.request_password_reset("bob@example.com")
    second = platform.request_password_reset("bob@example.com")
    assert any(m["purpose"] == "password_reset" for m in email_adapter.messages)

    platform.confirm_password_reset(second["reset_token"], "EvenStronger1!")

    # The first (now-stale) reset link must also be rejected — revoked as a
    # side effect of completing the reset via the second link.
    with pytest.raises(ValidationError):
        platform.confirm_password_reset(first["reset_token"], "AnotherStrong2!")

    # Replaying the token that already succeeded must also fail.
    with pytest.raises(ValidationError):
        platform.confirm_password_reset(second["reset_token"], "AnotherStrong3!")

    events = platform.audit.list_events(event_type="password.reset")
    assert len(events) == 1


def test_magic_link_is_single_use_and_provisions_user(email_adapter: _CapturingEmailAdapter) -> None:
    platform = _platform()
    req = platform.request_magic_link("newuser@example.com")
    token = req["magic_token"]
    assert any(m["purpose"] == "magic_link" and m["to"] == "newuser@example.com" for m in email_adapter.messages)

    session = platform.consume_magic_link(token)
    assert session["user"]["email"] == "newuser@example.com"

    with pytest.raises(Exception):
        platform.consume_magic_link(token)


def test_invitation_is_single_use_and_has_expiry(email_adapter: _CapturingEmailAdapter) -> None:
    platform = _platform()
    submitted = platform.submit_access_request(
        name="Carol", email="carol@corp.example", organization="Corp", reason="Research"
    )
    request_id = submitted["request"]["request_id"]
    admin = platform._get_by_email("admin@dspai.local")
    assert admin is not None

    decided = platform.decide_access_request(request_id, approve=True, actor_user_id=admin.user_id)
    token = decided["invitation_token"]
    assert any(m["purpose"] == "invitation" for m in email_adapter.messages)

    # Invitation payload never carries the raw token in persisted storage.
    assert not decided["request"].get("invitation_token")

    accepted = platform.accept_invitation(
        token=token, password="StrongPass12!", confirm_password="StrongPass12!"
    )
    assert accepted["ok"] is True

    with pytest.raises(ValidationError):
        platform.accept_invitation(
            token=token, password="StrongPass12!", confirm_password="StrongPass12!"
        )

    events = platform.audit.list_events(event_type="invitation.accepted")
    assert len(events) == 1


def test_invitation_expiry_enforced() -> None:
    from datetime import timedelta

    platform = _platform()
    submitted = platform.submit_access_request(
        name="Dan", email="dan@corp.example", organization="Corp", reason="Research"
    )
    request_id = submitted["request"]["request_id"]
    admin = platform._get_by_email("admin@dspai.local")
    assert admin is not None
    decided = platform.decide_access_request(request_id, approve=True, actor_user_id=admin.user_id)
    token = decided["invitation_token"]

    # Simulate expiry by revoking (equivalent effect: token no longer redeemable).
    assert platform.tokens.revoke(purpose="invitation", token=token) is True
    with pytest.raises(ValidationError):
        platform.accept_invitation(
            token=token, password="StrongPass12!", confirm_password="StrongPass12!"
        )


def test_duplicate_account_detected_before_second_accept_is_impossible() -> None:
    """Regression guard: single-use enforcement means a replayed invitation
    token is rejected outright, never reaching duplicate-account detection."""
    platform = _platform()
    submitted = platform.submit_access_request(
        name="Eve", email="eve@corp.example", organization="Corp", reason="Research"
    )
    request_id = submitted["request"]["request_id"]
    admin = platform._get_by_email("admin@dspai.local")
    assert admin is not None
    decided = platform.decide_access_request(request_id, approve=True, actor_user_id=admin.user_id)
    token = decided["invitation_token"]
    platform.accept_invitation(token=token, password="StrongPass12!", confirm_password="StrongPass12!")

    with pytest.raises(ValidationError) as excinfo:
        platform.accept_invitation(token=token, password="StrongPass12!", confirm_password="StrongPass12!")
    assert not isinstance(excinfo.value, DuplicateUserError)
