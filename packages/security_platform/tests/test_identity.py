"""PEP-001 identity / security contract tests."""

from __future__ import annotations

import pytest

from production_platform import InfrastructureBundle
from security_platform import (
    AuthenticationError,
    IdentityService,
    PasswordPolicy,
    Role,
    SecurityBundle,
    SecuritySettings,
    SqlUserRepository,
    build_password_hasher,
)


class TestPasswordPolicy:
    def test_rejects_short(self) -> None:
        with pytest.raises(Exception):
            PasswordPolicy().validate("Short1")

    def test_accepts_strong(self) -> None:
        PasswordPolicy().validate("StrongPass12")


class TestPasswordHasher:
    def test_roundtrip(self) -> None:
        hasher = build_password_hasher(prefer_argon2=False)
        digest = hasher.hash("StrongPass12")
        assert hasher.verify("StrongPass12", digest) is True
        assert hasher.verify("wrong", digest) is False


class TestIdentityLifecycle:
    def test_provision_activate_deactivate(self) -> None:
        bundle = SecurityBundle.create(
            SecuritySettings(jwt_secret="unit-test-secret", allow_passwordless=False),
            seed_admin=False,
        )
        user = bundle.identity.provision(
            username="alice",
            role=Role.ADVISOR,
            password="StrongPass12",
            email="alice@example.com",
        )
        assert user.active is True
        bundle.identity.deactivate(user.user_id)
        with pytest.raises(AuthenticationError):
            bundle.identity.authenticate("alice", "StrongPass12")
        bundle.identity.activate(user.user_id)
        pair = bundle.identity.authenticate("alice", "StrongPass12")
        assert pair.access_token
        assert pair.refresh_token


class TestAuthTokens:
    def test_password_login_and_refresh_rotation(self) -> None:
        bundle = SecurityBundle.create(
            SecuritySettings(jwt_secret="unit-test-secret"),
            seed_admin=False,
        )
        bundle.identity.provision(
            username="bob", role=Role.RESEARCHER, password="StrongPass12"
        )
        pair = bundle.identity.authenticate("bob", "StrongPass12")
        rotated = bundle.identity.refresh(pair.refresh_token)
        assert rotated.access_token != pair.access_token
        with pytest.raises(AuthenticationError):
            bundle.identity.refresh(pair.refresh_token)

    def test_passwordless_compat_when_no_hash(self) -> None:
        bundle = SecurityBundle.create(
            SecuritySettings(jwt_secret="unit-test-secret", allow_passwordless=True)
        )
        pair = bundle.identity.authenticate("admin", None)
        assert pair.access_token

    def test_password_required_when_hash_set(self) -> None:
        bundle = SecurityBundle.create(
            SecuritySettings(jwt_secret="unit-test-secret"),
            seed_admin=False,
        )
        bundle.identity.provision(
            username="carol", role=Role.CLIENT, password="StrongPass12"
        )
        with pytest.raises(AuthenticationError):
            bundle.identity.authenticate("carol", None)


class TestLockout:
    def test_lockout_after_failures(self) -> None:
        bundle = SecurityBundle.create(
            SecuritySettings(jwt_secret="unit-test-secret"),
            seed_admin=False,
        )
        bundle.identity.provision(
            username="dave", role=Role.CLIENT, password="StrongPass12"
        )
        for _ in range(5):
            with pytest.raises(AuthenticationError):
                bundle.identity.authenticate("dave", "WrongPass999")
        with pytest.raises(AuthenticationError, match="locked"):
            bundle.identity.authenticate("dave", "StrongPass12")


class TestPasswordReset:
    def test_reset_flow(self) -> None:
        bundle = SecurityBundle.create(
            SecuritySettings(jwt_secret="unit-test-secret"),
            seed_admin=False,
        )
        bundle.identity.provision(
            username="erin", role=Role.CLIENT, password="StrongPass12"
        )
        token = bundle.identity.request_password_reset("erin")
        bundle.identity.confirm_password_reset(token, "NewStrongPass9")
        pair = bundle.identity.authenticate("erin", "NewStrongPass9")
        assert pair.access_token


class TestConsentAndIndiaPorts:
    def test_consent_record(self) -> None:
        bundle = SecurityBundle.create(SecuritySettings(jwt_secret="x" * 16))
        rec = bundle.identity.record_consent(
            subject_id="usr_admin", purpose="research_analytics", granted=True
        )
        assert rec.granted is True

    def test_aadhaar_port_blocked(self) -> None:
        bundle = SecurityBundle.create(SecuritySettings(jwt_secret="x" * 16))
        with pytest.raises(Exception):
            bundle.aadhaar.verify_offline("ref")


class TestPep002Wiring:
    def test_create_with_infrastructure(self) -> None:
        infra = InfrastructureBundle.create_offline()
        bundle = SecurityBundle.create_with_infrastructure(
            infra,
            SecuritySettings(jwt_secret="unit-test-secret"),
            seed_admin=True,
            seed_admin_password="StrongPass12",
        )
        assert isinstance(bundle.users.repository, SqlUserRepository)
        assert infra.database.ping() is True
        pair = bundle.identity.authenticate("admin", "StrongPass12")
        assert pair.session_id
        # Session stored via SessionPort
        assert infra.session.get(pair.session_id) is not None

    def test_sql_user_migration_roundtrip(self) -> None:
        infra = InfrastructureBundle.create_offline()
        repo = SqlUserRepository(infra.database)
        from security_platform import UserRecord

        user = UserRecord(
            user_id="usr_x",
            username="xray",
            role=Role.API,
            password_hash=build_password_hasher(prefer_argon2=False).hash(
                "StrongPass12"
            ),
        )
        repo.upsert(user)
        loaded = repo.get_by_username("xray")
        assert loaded is not None
        assert loaded.user_id == "usr_x"


class TestRbacUnchanged:
    def test_admin_still_has_manage_users(self) -> None:
        from security_platform import Permission

        bundle = SecurityBundle.create(SecuritySettings(jwt_secret="x" * 16))
        assert bundle.roles.has_permission(Role.ADMIN, Permission.MANAGE_USERS)
