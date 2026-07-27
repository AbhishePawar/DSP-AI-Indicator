"""Security platform unit tests (K1.2)."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from dsp_platform import (
    PlatformBuilder,
    PlatformConfiguration,
)
from security_platform import (
    AuthenticationError,
    AuthorizationError,
    Permission,
    RateLimitConfig,
    RateLimitError,
    RateLimiter,
    Role,
    SecurityBundle,
    SecuritySettings,
    TokenError,
    UserRecord,
    __version__,
)


def test_version() -> None:
    assert __version__ == "0.1.0"


class TestRolesAndPermissions:
    def test_admin_has_all(self) -> None:
        bundle = SecurityBundle.create()
        assert bundle.roles.has_permission(Role.ADMIN, Permission.MANAGE_USERS)
        assert bundle.roles.has_permission(Role.ADMIN, Permission.ANALYZE_COMPANY)

    def test_client_cannot_analyze(self) -> None:
        bundle = SecurityBundle.create()
        assert not bundle.roles.has_permission(
            Role.CLIENT, Permission.ANALYZE_COMPANY
        )
        assert bundle.roles.has_permission(Role.CLIENT, Permission.VIEW_REPORTS)


class TestJWT:
    def test_issue_and_verify(self) -> None:
        bundle = SecurityBundle.create(
            SecuritySettings(jwt_secret="unit-test-secret")
        )
        token = bundle.jwt.issue(
            subject="usr_admin", role=Role.ADMIN, username="admin"
        )
        claims = bundle.jwt.verify(token)
        assert claims.subject == "usr_admin"
        assert claims.role is Role.ADMIN

    def test_tampered_token_rejected(self) -> None:
        bundle = SecurityBundle.create(
            SecuritySettings(jwt_secret="unit-test-secret")
        )
        token = bundle.jwt.issue(subject="usr_admin", role=Role.ADMIN)
        bad = token[:-4] + "xxxx"
        with pytest.raises(TokenError):
            bundle.jwt.verify(bad)

    def test_expired_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        bundle = SecurityBundle.create(
            SecuritySettings(jwt_secret="unit-test-secret")
        )
        now = time.time()
        monkeypatch.setattr(time, "time", lambda: now)
        token = bundle.jwt.issue(
            subject="usr_admin", role=Role.ADMIN, ttl_seconds=10
        )
        monkeypatch.setattr(time, "time", lambda: now + 11)
        with pytest.raises(TokenError, match="expired"):
            bundle.jwt.verify(token)


class TestApiKeys:
    def test_issue_and_verify(self) -> None:
        bundle = SecurityBundle.create()
        record, secret = bundle.api_keys.issue(name="ci", role=Role.API)
        principal = bundle.authentication.authenticate_api_key(
            record.key_id, secret
        )
        assert principal.role is Role.API
        assert principal.auth_method == "api_key"

    def test_bad_secret(self) -> None:
        bundle = SecurityBundle.create()
        record, _secret = bundle.api_keys.issue(name="ci", role=Role.API)
        with pytest.raises(AuthenticationError):
            bundle.authentication.authenticate_api_key(record.key_id, "wrong")


class TestAuthzAndContext:
    def test_jwt_auth_and_permission(self) -> None:
        bundle = SecurityBundle.create(
            SecuritySettings(jwt_secret="unit-test-secret")
        )
        token = bundle.jwt.issue(subject="usr_admin", role=Role.ADMIN)
        principal = bundle.authentication.authenticate_jwt(token)
        bundle.authorization.check(principal, Permission.MANAGE_PLATFORM)
        ctx = bundle.authentication.build_context(principal)
        assert ctx.authenticated is True
        ctx.require(Permission.ANALYZE_COMPANY)

    def test_client_denied_manage(self) -> None:
        bundle = SecurityBundle.create(
            SecuritySettings(jwt_secret="unit-test-secret")
        )
        bundle.users.add(
            UserRecord(user_id="usr_client", username="client", role=Role.CLIENT)
        )
        token = bundle.jwt.issue(subject="usr_client", role=Role.CLIENT)
        principal = bundle.authentication.authenticate_jwt(token)
        with pytest.raises(AuthorizationError):
            bundle.authorization.check(principal, Permission.MANAGE_USERS)

    def test_guest_mode(self) -> None:
        bundle = SecurityBundle.create(
            SecuritySettings(allow_guest=True, jwt_secret="secret")
        )
        guest = bundle.authentication.guest_principal()
        assert guest.role is Role.GUEST
        with pytest.raises(AuthorizationError):
            bundle.authorization.check(guest, Permission.ANALYZE_COMPANY)


class TestRateLimitAndAudit:
    def test_rate_limit(self) -> None:
        limiter = RateLimiter(
            RateLimitConfig(max_requests=2, window_seconds=60.0)
        )
        limiter.check("u1")
        limiter.check("u1")
        with pytest.raises(RateLimitError):
            limiter.check("u1")

    def test_audit_logger(self) -> None:
        bundle = SecurityBundle.create()
        bundle.audit.log(
            action="login", subject="admin", success=True, detail="ok"
        )
        events = bundle.audit.list_events()
        assert len(events) == 1
        assert events[0].action == "login"


class TestApiIntegration:
    def test_protected_analyze_requires_auth(self) -> None:
        platform = (
            PlatformBuilder()
            .with_configuration(
                PlatformConfiguration(require_analysis_service=False)
            )
            .build()
        )
        bundle = SecurityBundle.create(
            SecuritySettings(
                jwt_secret="api-test-secret",
                allow_guest=False,
                require_auth=True,
            )
        )
        client = TestClient(create_app(platform=platform, security=bundle))
        denied = client.post(
            "/analyze/company",
            json={
                "symbol": "AAPL",
                "start": "2024-01-01",
                "end": "2024-06-01",
                "as_decision_pack": False,
            },
        )
        assert denied.status_code == 401

        token = bundle.jwt.issue(subject="usr_admin", role=Role.ADMIN)
        # Still fails platform-side without analysis service, but auth passes.
        authed = client.post(
            "/analyze/company",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "symbol": "AAPL",
                "start": "2024-01-01",
                "end": "2024-06-01",
                "as_decision_pack": False,
            },
        )
        assert authed.status_code != 401
        assert authed.status_code != 403

    def test_health_remains_public(self) -> None:
        platform = (
            PlatformBuilder()
            .with_configuration(
                PlatformConfiguration(require_analysis_service=False)
            )
            .build()
        )
        bundle = SecurityBundle.create(
            SecuritySettings(jwt_secret="api-test-secret", require_auth=True)
        )
        client = TestClient(create_app(platform=platform, security=bundle))
        assert client.get("/health").status_code == 200
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").status_code == 200
        assert client.get("/api/v1/health/live").status_code == 200
        assert client.get("/metrics").status_code == 200

    def test_dsp_platform_has_no_security_import(self) -> None:
        import dsp_platform

        source = open(
            dsp_platform.__file__, encoding="utf-8"
        ).read()
        assert "security_platform" not in source
