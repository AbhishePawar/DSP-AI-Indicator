"""Durable account lockout counters (A008 metadata).

Failed-login counts previously used get-then-put on the user row. Concurrent
failures (or two Cloud Run instances) could lose increments and delay lockout.
The authoritative counter is an A008 lockout entity incremented atomically.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from auth.exceptions import AuthenticationError
from auth.models import AuthUser, freeze_mapping, utc_now

__all__ = ["AuthLockoutStore"]

logger = logging.getLogger(__name__)

_ENTITY_KIND = "metadata"
_PREFIX = "auth-lockout-"
_USER_PREFIX = "auth-user-"


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


class AuthLockoutStore:
    def __init__(self, persistence_service: Any) -> None:
        self._persistence = persistence_service

    def _entity_id(self, user_id: str) -> str:
        return f"{_PREFIX}{user_id}"

    def record_failure(
        self,
        user: AuthUser,
        *,
        threshold: int,
        lockout_seconds: int,
    ) -> int:
        """Atomically increment failures. Lock the account at ``threshold``."""
        ts = _now()
        now_iso = ts.isoformat()
        expires = ts + timedelta(days=365)
        entity_id = self._entity_id(user.user_id)
        try:
            self._persistence.atomic_put_if_absent(
                kind=_ENTITY_KIND,
                entity_id=entity_id,
                payload={
                    "auth_entity": "auth_lockout",
                    "user_id": user.user_id,
                    "count": 0,
                    "expires_at": expires.isoformat(),
                    "consumed_at": None,
                },
                refs={"auth_entity": "auth_lockout", "user_id": user.user_id},
                created_at=now_iso,
            )
            stored = self._persistence.atomic_increment_unexpired(
                _ENTITY_KIND,
                entity_id,
                now_iso=now_iso,
                counter_field=("payload", "count"),
                max_value=max(int(threshold), 1),
            )
        except Exception as exc:  # noqa: BLE001
            logger.info("auth lockout increment unavailable")
            raise AuthenticationError("invalid credentials") from exc

        if stored is None:
            count = int(threshold)
        else:
            payload = dict(stored.get("payload") or {})
            count = int(payload.get("count") or 0)

        meta = dict(user.metadata or {})
        meta["failed_login_count"] = count
        fields: dict[str, Any] = {"metadata": dict(freeze_mapping(meta))}
        match: dict[str, Any] | None = None
        if count >= int(threshold):
            until = (ts + timedelta(seconds=int(lockout_seconds))).isoformat()
            meta["locked_until"] = until
            fields = {
                "status": "locked",
                "metadata": dict(freeze_mapping(meta)),
            }
            match = {"status": "active"}
            logger.info("auth lockout threshold reached")
        self._merge_user(user.user_id, fields=fields, match=match)
        return count

    def is_locked(self, user_id: str, *, threshold: int) -> bool:
        row = self._persistence.get(_ENTITY_KIND, self._entity_id(user_id))
        if row is None:
            return False
        payload = dict(row.get("payload") or {})
        return int(payload.get("count") or 0) >= int(threshold)

    def reset(self, user_id: str) -> None:
        self._persistence.delete(_ENTITY_KIND, self._entity_id(user_id))

    def _merge_user(
        self,
        user_id: str,
        *,
        fields: dict[str, Any],
        match: dict[str, Any] | None,
    ) -> None:
        self._persistence.atomic_merge_payload(
            _ENTITY_KIND,
            f"{_USER_PREFIX}{user_id}",
            fields=fields,
            updated_at=utc_now().isoformat(),
            match=match,
        )
