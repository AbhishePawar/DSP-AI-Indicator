"""User store via A008 persistence (EPIC-A009) — no persistence package changes."""

from __future__ import annotations

import uuid
from typing import Any

from auth.exceptions import DuplicateUserError, ValidationError
from auth.hashing import hash_password
from auth.models import AuthUser, freeze_mapping, utc_now
from auth.validation import assert_email, assert_roles, assert_status, assert_username

__all__ = ["UserStore"]

_USER_PREFIX = "auth-user-"


class UserStore:
    """Users persisted as A008 ``metadata`` entities with ``auth_entity=user``."""

    def __init__(self, persistence_service: Any) -> None:
        self._persistence = persistence_service

    def _entity_id(self, user_id: str) -> str:
        return f"{_USER_PREFIX}{user_id}"

    def create(
        self,
        *,
        username: str,
        email: str,
        password: str,
        display_name: str | None = None,
        roles: list[str] | None = None,
        user_id: str | None = None,
        created_at: str | None = None,
        password_salt: str | None = None,
    ) -> AuthUser:
        uname = assert_username(username)
        mail = assert_email(email)
        for existing in self.list_users():
            if existing.username.casefold() == uname.casefold():
                raise DuplicateUserError(f"duplicate username {uname!r}")
            if existing.email.casefold() == mail.casefold():
                raise DuplicateUserError(f"duplicate email {mail!r}")
        if not password:
            raise ValidationError("password is required")
        created = created_at or utc_now().isoformat()
        uid = user_id or str(uuid.uuid4())
        user = AuthUser(
            user_id=uid,
            username=uname,
            email=mail,
            display_name=(display_name or uname).strip(),
            password_hash=hash_password(password, salt=password_salt),
            status="active",
            created_at=created,
            updated_at=created,
            roles=assert_roles(roles) or ("read_only",),
            metadata=freeze_mapping({"auth_entity": "user"}),
        )
        payload = user.to_dict(include_hash=True)
        payload["auth_entity"] = "user"
        self._persistence.put(
            kind="metadata",
            entity_id=self._entity_id(uid),
            payload=payload,
            refs={"auth_entity": "user", "username": uname},
            created_at=created,
            allow_update=False,
        )
        return user

    def get(self, user_id: str) -> AuthUser | None:
        row = self._persistence.get("metadata", self._entity_id(user_id))
        if row is None:
            return None
        return self._from_payload(row.get("payload") or {})

    def get_by_username(self, username: str) -> AuthUser | None:
        target = assert_username(username).casefold()
        for user in self.list_users():
            if user.username.casefold() == target:
                return user
        return None

    def list_users(self) -> list[AuthUser]:
        out: list[AuthUser] = []
        for entity_id in self._persistence.list_ids("metadata"):
            if not str(entity_id).startswith(_USER_PREFIX):
                continue
            row = self._persistence.get("metadata", entity_id)
            if not row:
                continue
            payload = row.get("payload") or {}
            if payload.get("auth_entity") != "user" and "username" not in payload:
                continue
            out.append(self._from_payload(payload))
        out.sort(key=lambda u: u.username)
        return out

    def save(self, user: AuthUser) -> AuthUser:
        payload = user.to_dict(include_hash=True)
        payload["auth_entity"] = "user"
        self._persistence.put(
            kind="metadata",
            entity_id=self._entity_id(user.user_id),
            payload=payload,
            refs={"auth_entity": "user", "username": user.username},
            created_at=user.updated_at,
            allow_update=True,
        )
        return user

    def set_roles(self, user_id: str, roles: list[str]) -> AuthUser:
        user = self.get(user_id)
        if user is None:
            raise ValidationError("user not found")
        updated = AuthUser(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            password_hash=user.password_hash,
            status=assert_status(user.status),
            created_at=user.created_at,
            updated_at=utc_now().isoformat(),
            last_login=user.last_login,
            roles=assert_roles(roles),
            metadata=user.metadata,
        )
        return self.save(updated)

    def _from_payload(self, payload: dict[str, Any]) -> AuthUser:
        return AuthUser(
            user_id=str(payload.get("user_id") or ""),
            username=str(payload.get("username") or ""),
            email=str(payload.get("email") or ""),
            display_name=str(payload.get("display_name") or ""),
            password_hash=str(payload.get("password_hash") or ""),
            status=assert_status(str(payload.get("status") or "active")),
            created_at=str(payload.get("created_at") or ""),
            updated_at=str(payload.get("updated_at") or ""),
            last_login=payload.get("last_login"),
            roles=tuple(payload.get("roles") or ()),
            metadata=freeze_mapping(dict(payload.get("metadata") or {"auth_entity": "user"})),
        )
