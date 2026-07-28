"""Identity service — lifecycle, auth, lockout, recovery architecture (PEP-001)."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any

from security_platform.security.audit import AuditLogger
from security_platform.security.exceptions import AuthenticationError, SecurityError
from security_platform.security.identity.password import (
    PasswordPolicy,
    build_password_hasher,
)
from security_platform.security.identity.ports import (
    AuditStorePort,
    ConsentRecord,
    ConsentRecordPort,
    PasswordHasherPort,
    UserRepositoryPort,
)
from security_platform.security.identity.tokens import TokenPair, TokenService
from security_platform.security.roles import Role
from security_platform.security.users import PermissionManager, UserRecord, UserStore

__all__ = [
    "IdentityService",
    "InMemoryAuditStore",
    "InMemoryConsentStore",
    "LockoutPolicy",
    "CompositeAudit",
]


@dataclass(frozen=True, slots=True)
class LockoutPolicy:
    max_failures: int = 5
    lock_seconds: int = 900


class InMemoryAuditStore:
    def __init__(self) -> None:
        self._events: list = []
        self._lock = Lock()

    def append(self, event) -> None:  # noqa: ANN001
        with self._lock:
            self._events.append(event)

    def list_events(self, *, limit: int = 100):
        with self._lock:
            return tuple(self._events[-limit:])


class CompositeAudit:
    """Fan-out to legacy AuditLogger + AuditStorePort."""

    def __init__(self, logger: AuditLogger, store: AuditStorePort) -> None:
        self._logger = logger
        self._store = store

    def log(self, **kwargs):  # noqa: ANN003
        event = self._logger.log(**kwargs)
        self._store.append(event)
        return event

    def list_events(self):
        return self._logger.list_events()


class InMemoryConsentStore:
    def __init__(self) -> None:
        self._items: dict[str, list[ConsentRecord]] = {}
        self._lock = Lock()

    def record(self, consent: ConsentRecord) -> None:
        with self._lock:
            self._items.setdefault(consent.subject_id, []).append(consent)

    def list_for_subject(self, subject_id: str):
        with self._lock:
            return tuple(self._items.get(subject_id, []))


class IdentityService:
    """User lifecycle + password auth + recovery token architecture."""

    def __init__(
        self,
        *,
        users: UserStore,
        tokens: TokenService,
        hasher: PasswordHasherPort | None = None,
        policy: PasswordPolicy | None = None,
        lockout: LockoutPolicy | None = None,
        audit: Any | None = None,
        rate_limit_port: Any | None = None,
        consents: ConsentRecordPort | None = None,
        allow_passwordless: bool = True,
    ) -> None:
        self._users = users
        self._tokens = tokens
        self._hasher = hasher or build_password_hasher()
        self._policy = policy or PasswordPolicy()
        self._lockout = lockout or LockoutPolicy()
        self._audit = audit
        self._rate = rate_limit_port
        self._consents = consents or InMemoryConsentStore()
        self._allow_passwordless = allow_passwordless
        self._reset_tokens: dict[str, tuple[str, datetime]] = {}
        self._verify_tokens: dict[str, tuple[str, datetime]] = {}
        self._lock = Lock()
        self._permissions = PermissionManager()

    @property
    def users(self) -> UserStore:
        return self._users

    @property
    def repository(self) -> UserRepositoryPort:
        return self._users.repository

    def provision(
        self,
        *,
        user_id: str | None = None,
        username: str,
        role: Role | str,
        password: str | None = None,
        email: str | None = None,
        display_name: str | None = None,
        org_id: str | None = None,
        active: bool = True,
    ) -> UserRecord:
        password_hash = None
        if password is not None:
            self._policy.validate(password)
            password_hash = self._hasher.hash(password)
        user = UserRecord(
            user_id=user_id or f"usr_{uuid.uuid4().hex[:12]}",
            username=username,
            role=role if isinstance(role, Role) else Role(role),
            active=active,
            display_name=display_name,
            email=email,
            password_hash=password_hash,
            org_id=org_id,
        )
        return self._users.add(user, replace=False)

    def activate(self, user_id: str) -> UserRecord:
        user = self._users.repository.set_active(user_id, active=True)
        self._emit("user_activated", user_id, True)
        return user

    def deactivate(self, user_id: str) -> UserRecord:
        user = self._users.repository.set_active(user_id, active=False)
        self._tokens.revoke_user(user_id)
        self._emit("user_deactivated", user_id, True)
        return user

    def set_password(self, user_id: str, password: str) -> UserRecord:
        self._policy.validate(password)
        user = self._users.get(user_id)
        updated = UserRecord(
            user_id=user.user_id,
            username=user.username,
            role=user.role,
            active=user.active,
            display_name=user.display_name,
            extra_permissions=user.extra_permissions,
            email=user.email,
            password_hash=self._hasher.hash(password),
            email_verified=user.email_verified,
            org_id=user.org_id,
            failed_login_count=0,
            locked_until=None,
        )
        self._users.repository.upsert(updated)
        self._tokens.revoke_user(user_id)
        self._emit("password_change", user_id, True)
        return updated

    def authenticate(
        self,
        username: str,
        password: str | None = None,
        *,
        remember_me: bool = False,
        client_fingerprint: str | None = None,
    ) -> TokenPair:
        self._check_rate(f"login:{username.strip().lower()}")
        try:
            user = self._users.get_by_username(username)
        except SecurityError as exc:
            self._emit("login_failed", username, False, detail="unknown_user")
            raise AuthenticationError("invalid credentials") from exc

        if not user.active:
            self._emit("login_failed", user.user_id, False, detail="inactive")
            raise AuthenticationError("user inactive")

        if self._is_locked(user):
            self._emit("login_failed", user.user_id, False, detail="locked")
            raise AuthenticationError("account locked")

        if user.password_hash:
            if not password:
                self._emit("login_failed", user.user_id, False, detail="password_required")
                raise AuthenticationError("password required")
            if not self._hasher.verify(password, user.password_hash):
                self._register_failure(user)
                self._emit("login_failed", user.user_id, False, detail="bad_password")
                raise AuthenticationError("invalid credentials")
        else:
            if not self._allow_passwordless:
                raise AuthenticationError("passwordless login disabled")
            if password:
                # Unexpected password for passwordless account — reject.
                raise AuthenticationError("invalid credentials")

        cleared = UserRecord(
            user_id=user.user_id,
            username=user.username,
            role=user.role,
            active=user.active,
            display_name=user.display_name,
            extra_permissions=user.extra_permissions,
            email=user.email,
            password_hash=user.password_hash,
            email_verified=user.email_verified,
            org_id=user.org_id,
            failed_login_count=0,
            locked_until=None,
        )
        self._users.repository.upsert(cleared)
        pair = self._tokens.issue_pair(
            cleared, remember_me=remember_me, client_fingerprint=client_fingerprint
        )
        self._emit("login_success", cleared.user_id, True)
        return pair

    def refresh(self, refresh_token: str) -> TokenPair:
        self._check_rate("refresh")
        # Peek user from refresh store via rotate path
        from security_platform.security.identity.tokens import hash_token

        rec = self._tokens._refresh.get(hash_token(refresh_token))  # noqa: SLF001
        if rec is None:
            raise AuthenticationError("invalid refresh token")
        user = self._users.get(rec.user_id)
        if not user.active:
            raise AuthenticationError("user inactive")
        pair = self._tokens.rotate(refresh_token, user=user)
        self._emit("token_refresh", user.user_id, True)
        return pair

    def logout(self, refresh_token: str | None = None, *, user_id: str | None = None) -> None:
        if refresh_token:
            self._tokens.revoke_refresh(refresh_token)
        if user_id:
            self._tokens.revoke_user(user_id)
        self._emit("logout", user_id or "unknown", True)

    def request_password_reset(self, username: str) -> str:
        """Return opaque reset token (caller delivers out-of-band)."""
        self._check_rate(f"reset:{username.strip().lower()}")
        try:
            user = self._users.get_by_username(username)
        except SecurityError:
            # Do not leak existence
            return secrets.token_urlsafe(32)
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._reset_tokens[token] = (
                user.user_id,
                datetime.now(tz=UTC) + timedelta(hours=1),
            )
        self._emit("password_reset_request", user.user_id, True)
        return token

    def confirm_password_reset(self, token: str, new_password: str) -> UserRecord:
        with self._lock:
            item = self._reset_tokens.pop(token, None)
        if item is None:
            raise AuthenticationError("invalid reset token")
        user_id, expires = item
        if expires <= datetime.now(tz=UTC):
            raise AuthenticationError("reset token expired")
        user = self.set_password(user_id, new_password)
        self._emit("password_reset_confirm", user_id, True)
        return user

    def issue_email_verification(self, user_id: str) -> str:
        token = secrets.token_urlsafe(24)
        with self._lock:
            self._verify_tokens[token] = (
                user_id,
                datetime.now(tz=UTC) + timedelta(days=2),
            )
        return token

    def confirm_email_verification(self, token: str) -> UserRecord:
        with self._lock:
            item = self._verify_tokens.pop(token, None)
        if item is None:
            raise AuthenticationError("invalid verification token")
        user_id, expires = item
        if expires <= datetime.now(tz=UTC):
            raise AuthenticationError("verification token expired")
        user = self._users.get(user_id)
        updated = UserRecord(
            user_id=user.user_id,
            username=user.username,
            role=user.role,
            active=user.active,
            display_name=user.display_name,
            extra_permissions=user.extra_permissions,
            email=user.email,
            password_hash=user.password_hash,
            email_verified=True,
            org_id=user.org_id,
            failed_login_count=user.failed_login_count,
            locked_until=user.locked_until,
        )
        self._users.repository.upsert(updated)
        return updated

    def record_consent(
        self, *, subject_id: str, purpose: str, granted: bool, policy_version: str = "1"
    ) -> ConsentRecord:
        consent = ConsentRecord(
            consent_id=str(uuid.uuid4()),
            subject_id=subject_id,
            purpose=purpose,
            granted=granted,
            policy_version=policy_version,
        )
        self._consents.record(consent)
        self._emit("consent_recorded", subject_id, True, detail=purpose)
        return consent

    def _is_locked(self, user: UserRecord) -> bool:
        if user.locked_until is None:
            return False
        return user.locked_until > datetime.now(tz=UTC)

    def _register_failure(self, user: UserRecord) -> None:
        failures = user.failed_login_count + 1
        locked_until = user.locked_until
        if failures >= self._lockout.max_failures:
            locked_until = datetime.now(tz=UTC) + timedelta(
                seconds=self._lockout.lock_seconds
            )
            self._emit("account_locked", user.user_id, True)
            failures = 0
        updated = UserRecord(
            user_id=user.user_id,
            username=user.username,
            role=user.role,
            active=user.active,
            display_name=user.display_name,
            extra_permissions=user.extra_permissions,
            email=user.email,
            password_hash=user.password_hash,
            email_verified=user.email_verified,
            org_id=user.org_id,
            failed_login_count=failures,
            locked_until=locked_until,
        )
        self._users.repository.upsert(updated)

    def _check_rate(self, key: str) -> None:
        if self._rate is None:
            return
        allowed = self._rate.allow(key, limit=20, window_seconds=60.0)
        if not allowed:
            from security_platform.security.exceptions import RateLimitError

            raise RateLimitError(f"rate limit exceeded for {key!r}")

    def _emit(
        self,
        action: str,
        subject: str,
        success: bool,
        *,
        detail: str = "",
    ) -> None:
        if self._audit is None:
            return
        self._audit.log(action=action, subject=subject, success=success, detail=detail)
