"""User repository — in-memory reference + SQL via DatabasePort (PEP-001/002)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from threading import Lock
from typing import Any

from security_platform.security.exceptions import SecurityError
from security_platform.security.identity.ports import UserRepositoryPort
from security_platform.security.permissions import assert_permission
from security_platform.security.roles import assert_role
from security_platform.security.users import UserRecord

__all__ = [
    "InMemoryUserRepository",
    "SqlUserRepository",
    "IDENTITY_MIGRATIONS_SQL",
    "user_record_from_row",
    "user_record_to_row",
]


IDENTITY_MIGRATIONS_SQL = (
    """
    CREATE TABLE IF NOT EXISTS identity_users (
        user_id TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        role TEXT NOT NULL,
        active INTEGER NOT NULL,
        display_name TEXT,
        email TEXT,
        password_hash TEXT,
        email_verified INTEGER NOT NULL,
        org_id TEXT,
        extra_permissions TEXT,
        failed_login_count INTEGER NOT NULL,
        locked_until TEXT
    )
    """,
)


class InMemoryUserRepository:
    """Process-local durable-shaped user store — reference adapter."""

    def __init__(self) -> None:
        self._by_id: dict[str, UserRecord] = {}
        self._by_username: dict[str, str] = {}
        self._lock = Lock()

    def upsert(self, user: UserRecord) -> UserRecord:
        key = user.user_id.strip().lower()
        uname = user.username.strip().lower()
        with self._lock:
            existing_uname = self._by_username.get(uname)
            if existing_uname is not None and existing_uname != key:
                raise SecurityError(f"duplicate username: {user.username!r}")
            old = self._by_id.get(key)
            if old is not None and old.username.strip().lower() != uname:
                self._by_username.pop(old.username.strip().lower(), None)
            self._by_id[key] = user
            self._by_username[uname] = key
        return user

    def get(self, user_id: str) -> UserRecord | None:
        with self._lock:
            return self._by_id.get(user_id.strip().lower())

    def get_by_username(self, username: str) -> UserRecord | None:
        with self._lock:
            key = self._by_username.get(username.strip().lower())
            if key is None:
                return None
            return self._by_id.get(key)

    def list_users(self) -> Sequence[UserRecord]:
        with self._lock:
            return tuple(self._by_id[k] for k in sorted(self._by_id))

    def set_active(self, user_id: str, *, active: bool) -> UserRecord:
        user = self.get(user_id)
        if user is None:
            raise SecurityError(f"unknown user: {user_id!r}")
        updated = UserRecord(
            user_id=user.user_id,
            username=user.username,
            role=user.role,
            active=active,
            display_name=user.display_name,
            extra_permissions=user.extra_permissions,
            email=user.email,
            password_hash=user.password_hash,
            email_verified=user.email_verified,
            org_id=user.org_id,
            failed_login_count=user.failed_login_count,
            locked_until=user.locked_until,
        )
        return self.upsert(updated)


class SqlUserRepository:
    """UserRepositoryPort backed by PEP-002 DatabasePort."""

    def __init__(self, database: Any) -> None:
        self._db = database
        self.ensure_schema()

    def ensure_schema(self) -> None:
        for stmt in IDENTITY_MIGRATIONS_SQL:
            self._db.execute(stmt.strip())

    def upsert(self, user: UserRecord) -> UserRecord:
        row = user_record_to_row(user)
        existing = self.get(user.user_id)
        if existing is None:
            cols = ", ".join(row.keys())
            vals = ", ".join(_sql_literal(v) for v in row.values())
            self._db.execute(f"INSERT INTO identity_users ({cols}) VALUES ({vals})")
        else:
            # Replace via delete+insert for dialect simplicity
            self._db.execute(
                f"DELETE FROM identity_users WHERE user_id = {_sql_literal(user.user_id)}"
            )
            cols = ", ".join(row.keys())
            vals = ", ".join(_sql_literal(v) for v in row.values())
            self._db.execute(f"INSERT INTO identity_users ({cols}) VALUES ({vals})")
        return user

    def get(self, user_id: str) -> UserRecord | None:
        rows = self._db.fetchall(
            "SELECT * FROM identity_users",
            {"user_id": user_id},
        )
        # In-memory dialect filters by params; Postgres adapter needs WHERE.
        # Prefer explicit filter in Python for portability across dialects.
        for row in rows:
            if str(row.get("user_id", "")).lower() == user_id.strip().lower():
                return user_record_from_row(row)
        return None

    def get_by_username(self, username: str) -> UserRecord | None:
        rows = self._db.fetchall("SELECT * FROM identity_users")
        for row in rows:
            if str(row.get("username", "")).lower() == username.strip().lower():
                return user_record_from_row(row)
        return None

    def list_users(self) -> Sequence[UserRecord]:
        rows = self._db.fetchall("SELECT * FROM identity_users")
        return tuple(user_record_from_row(r) for r in rows)

    def set_active(self, user_id: str, *, active: bool) -> UserRecord:
        user = self.get(user_id)
        if user is None:
            raise SecurityError(f"unknown user: {user_id!r}")
        updated = UserRecord(
            user_id=user.user_id,
            username=user.username,
            role=user.role,
            active=active,
            display_name=user.display_name,
            extra_permissions=user.extra_permissions,
            email=user.email,
            password_hash=user.password_hash,
            email_verified=user.email_verified,
            org_id=user.org_id,
            failed_login_count=user.failed_login_count,
            locked_until=user.locked_until,
        )
        return self.upsert(updated)


def user_record_to_row(user: UserRecord) -> dict[str, Any]:
    return {
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role.value,
        "active": 1 if user.active else 0,
        "display_name": user.display_name or "",
        "email": user.email or "",
        "password_hash": user.password_hash or "",
        "email_verified": 1 if user.email_verified else 0,
        "org_id": user.org_id or "",
        "extra_permissions": ",".join(p.value for p in user.extra_permissions),
        "failed_login_count": int(user.failed_login_count),
        "locked_until": user.locked_until.isoformat() if user.locked_until else "",
    }


def user_record_from_row(row: dict[str, Any]) -> UserRecord:
    extras_raw = str(row.get("extra_permissions") or "")
    extras = tuple(
        assert_permission(p) for p in extras_raw.split(",") if p.strip()
    )
    locked_raw = str(row.get("locked_until") or "")
    locked_until: datetime | None = None
    if locked_raw:
        locked_until = datetime.fromisoformat(locked_raw)
    return UserRecord(
        user_id=str(row["user_id"]),
        username=str(row["username"]),
        role=assert_role(str(row["role"])),
        active=bool(int(row.get("active", 1))),
        display_name=(str(row.get("display_name") or "") or None),
        extra_permissions=extras,
        email=str(row.get("email") or "") or None,
        password_hash=str(row.get("password_hash") or "") or None,
        email_verified=bool(int(row.get("email_verified", 0))),
        org_id=str(row.get("org_id") or "") or None,
        failed_login_count=int(row.get("failed_login_count") or 0),
        locked_until=locked_until,
    )


def _sql_literal(value: Any) -> str:
    if value is None:
        return "''"
    if isinstance(value, int):
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"
