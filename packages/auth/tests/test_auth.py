"""EPIC-A009 Authentication & RBAC unit tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from auth import (
    AuthenticationError,
    AuthorizationError,
    AuthService,
    DuplicateUserError,
    InvalidTokenError,
    JwtService,
    RoleRegistry,
    SessionError,
    ValidationError,
    get_auth_service,
    hash_password,
    reset_auth_service_for_tests,
    reset_role_registry_for_tests,
    verify_password,
)
from persistence import (
    InMemoryStorageProvider,
    PersistenceService,
    RepositoryRegistry,
    get_persistence_service,
    reset_persistence_service_for_tests,
    reset_repository_registry_for_tests,
)

FIXED = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
FIXED2 = (datetime.now(timezone.utc) + timedelta(hours=1)).replace(microsecond=0).isoformat()


@pytest.fixture(autouse=True)
def _reset() -> None:
    store = InMemoryStorageProvider()
    registry = RepositoryRegistry(storage=store)
    reset_repository_registry_for_tests(registry)
    ps = PersistenceService(registry)
    reset_persistence_service_for_tests(ps)
    reset_role_registry_for_tests(RoleRegistry())
    reset_auth_service_for_tests(AuthService(ps, jwt_secret="test-secret"))
    yield
    reset_auth_service_for_tests(None)
    reset_role_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    reset_repository_registry_for_tests(None)


def test_password_hashing_never_plaintext() -> None:
    h = hash_password("Secret123!", salt="aabbccddeeff0011")
    assert "Secret123!" not in h
    assert h.startswith("pbkdf2$")
    assert verify_password("Secret123!", h)
    assert not verify_password("wrong", h)
    # deterministic with fixed salt
    assert hash_password("Secret123!", salt="aabbccddeeff0011") == h


def test_login_logout_and_current_user() -> None:
    svc = get_auth_service()
    user = svc.create_user(
        username="analyst1",
        email="a1@example.com",
        password="Secret123!",
        roles=["research_analyst"],
        user_id="u-1",
        created_at=FIXED,
        password_salt="aabbccddeeff0011",
    )
    assert "password_hash" not in user
    login = svc.login(
        username="analyst1",
        password="Secret123!",
        created_at=FIXED,
        session_id="s-1",
        access_jti="a-1",
        refresh_jti="r-1",
    )
    tokens = login["tokens"]
    me = svc.current_user(tokens["access_token"])
    assert me["user_id"] == "u-1"
    assert me["roles"] == ["research_analyst"]
    out = svc.logout(session_id="s-1", updated_at=FIXED2)
    assert out["session"]["revoked"] is True
    with pytest.raises((InvalidTokenError, SessionError)):
        svc.current_user(tokens["access_token"])


def test_invalid_credentials() -> None:
    svc = get_auth_service()
    svc.create_user(
        username="analyst1",
        email="a1@example.com",
        password="Secret123!",
        user_id="u-1",
        created_at=FIXED,
        password_salt="aabbccddeeff0011",
    )
    with pytest.raises(AuthenticationError):
        svc.login(username="analyst1", password="wrong", created_at=FIXED)


def test_duplicate_user_and_email() -> None:
    svc = get_auth_service()
    svc.create_user(
        username="analyst1",
        email="a1@example.com",
        password="Secret123!",
        user_id="u-1",
        created_at=FIXED,
        password_salt="aabbccddeeff0011",
    )
    with pytest.raises(DuplicateUserError):
        svc.create_user(
            username="analyst1",
            email="other@example.com",
            password="Secret123!",
            user_id="u-2",
            created_at=FIXED,
            password_salt="aabbccddeeff0011",
        )
    with pytest.raises(DuplicateUserError):
        svc.create_user(
            username="analyst2",
            email="a1@example.com",
            password="Secret123!",
            user_id="u-3",
            created_at=FIXED,
            password_salt="aabbccddeeff0011",
        )


def test_token_lifecycle_refresh_deterministic() -> None:
    svc = get_auth_service()
    svc.create_user(
        username="admin1",
        email="admin@example.com",
        password="Secret123!",
        roles=["administrator"],
        user_id="u-admin",
        created_at=FIXED,
        password_salt="aabbccddeeff0011",
    )
    login = svc.login(
        username="admin1",
        password="Secret123!",
        created_at=FIXED,
        session_id="s-admin",
        access_jti="acc-1",
        refresh_jti="ref-1",
    )
    refreshed = svc.refresh(
        refresh_token=login["tokens"]["refresh_token"],
        created_at=FIXED2,
        access_jti="acc-2",
    )
    assert refreshed["tokens"]["access_token"] != login["tokens"]["access_token"]
    # same inputs => same JWT
    jwt = JwtService("test-secret")
    t1 = jwt.issue(
        subject="u",
        claims={"a": 1},
        expires_in=60,
        issued_at=FIXED,
        token_id="j1",
        token_use="access",
    )
    t2 = jwt.issue(
        subject="u",
        claims={"a": 1},
        expires_in=60,
        issued_at=FIXED,
        token_id="j1",
        token_use="access",
    )
    assert t1 == t2


def test_expired_token() -> None:
    jwt = JwtService("test-secret")
    token = jwt.issue(
        subject="u",
        expires_in=1,
        issued_at=FIXED,
        token_id="j",
        token_use="access",
    )
    later = datetime.fromisoformat(FIXED.replace("Z", "+00:00")) + timedelta(hours=2)
    with pytest.raises(InvalidTokenError):
        jwt.decode(token, now=later)


def test_role_assignment_and_permission_evaluation() -> None:
    svc = get_auth_service()
    svc.create_user(
        username="ro1",
        email="ro@example.com",
        password="Secret123!",
        roles=["read_only"],
        user_id="u-ro",
        created_at=FIXED,
        password_salt="aabbccddeeff0011",
    )
    eval_ro = svc.evaluate_permission("u-ro", "read_research")
    assert eval_ro["allowed"] is True
    eval_deny = svc.evaluate_permission("u-ro", "manage_users")
    assert eval_deny["allowed"] is False
    svc.set_user_roles("u-ro", ["administrator"])
    assert svc.evaluate_permission("u-ro", "manage_users")["allowed"] is True


def test_protect_requires_permission() -> None:
    svc = get_auth_service()
    svc.create_user(
        username="ro1",
        email="ro@example.com",
        password="Secret123!",
        roles=["read_only"],
        user_id="u-ro",
        created_at=FIXED,
        password_salt="aabbccddeeff0011",
    )
    login = svc.login(
        username="ro1",
        password="Secret123!",
        created_at=FIXED,
        session_id="s-ro",
        access_jti="a-ro",
        refresh_jti="r-ro",
    )
    token = login["tokens"]["access_token"]
    assert svc.protect(token, "read_research")["user_id"] == "u-ro"
    with pytest.raises(AuthorizationError):
        svc.protect(token, "manage_users")


def test_invalid_role_assignment() -> None:
    svc = get_auth_service()
    with pytest.raises(ValidationError):
        svc.create_user(
            username="bad1",
            email="bad@example.com",
            password="Secret123!",
            roles=["not_a_role"],
            user_id="u-bad",
            created_at=FIXED,
            password_salt="aabbccddeeff0011",
        )


def test_configurable_roles() -> None:
    svc = get_auth_service()
    role = svc.upsert_role(
        "custom_auditor",
        name="Custom Auditor",
        permissions=["view_audit", "read_research"],
    )
    assert role["role_id"] == "custom_auditor"
    assert "view_audit" in role["permissions"]
    svc.create_user(
        username="aud1",
        email="aud@example.com",
        password="Secret123!",
        roles=["custom_auditor"],
        user_id="u-aud",
        created_at=FIXED,
        password_salt="aabbccddeeff0011",
    )
    assert svc.evaluate_permission("u-aud", "view_audit")["allowed"] is True


def test_schema_and_persistence_integration() -> None:
    svc = get_auth_service()
    schema = svc.schema()
    assert schema["schema_version"] == "1.0.0"
    assert "read_research" in schema["permissions"]
    svc.create_user(
        username="ps1",
        email="ps@example.com",
        password="Secret123!",
        user_id="u-ps",
        created_at=FIXED,
        password_salt="aabbccddeeff0011",
    )
    row = get_persistence_service().get("metadata", "auth-user-u-ps")
    assert row is not None
    assert row["payload"]["username"] == "ps1"
    assert "password_hash" in row["payload"]
    assert "Secret123!" not in str(row["payload"]["password_hash"])


def test_concurrent_sessions_and_revocation() -> None:
    svc = get_auth_service()
    svc.create_user(
        username="pm1",
        email="pm@example.com",
        password="Secret123!",
        roles=["portfolio_manager"],
        user_id="u-pm",
        created_at=FIXED,
        password_salt="aabbccddeeff0011",
    )
    s1 = svc.login(
        username="pm1",
        password="Secret123!",
        created_at=FIXED,
        session_id="sess-a",
        access_jti="aa",
        refresh_jti="ra",
    )
    s2 = svc.login(
        username="pm1",
        password="Secret123!",
        created_at=FIXED,
        session_id="sess-b",
        access_jti="ab",
        refresh_jti="rb",
    )
    assert s1["session"]["session_id"] != s2["session"]["session_id"]
    svc.logout(session_id="sess-a", updated_at=FIXED2)
    with pytest.raises((InvalidTokenError, SessionError)):
        svc.current_user(s1["tokens"]["access_token"])
    assert svc.current_user(s2["tokens"]["access_token"])["user_id"] == "u-pm"


def test_platform_facade_wiring() -> None:
    from dsp_platform.platform import DSPPlatform

    platform = DSPPlatform()
    schema = platform.auth_schema()
    assert "permissions" in schema
    user = platform.create_auth_user(
        username="plat1",
        email="plat@example.com",
        password="Secret123!",
        roles=["reviewer"],
        user_id="u-plat",
        created_at=FIXED,
        password_salt="aabbccddeeff0011",
    )
    assert user["username"] == "plat1"
    login = platform.auth_login(
        username="plat1",
        password="Secret123!",
        created_at=FIXED,
        session_id="s-plat",
        access_jti="ap",
        refresh_jti="rp",
    )
    me = platform.auth_current_user(login["tokens"]["access_token"])
    assert me["roles"] == ["reviewer"]
