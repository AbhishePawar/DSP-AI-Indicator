"""Device tracking and trusted-device registry for enterprise sessions."""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any

__all__ = ["DeviceRecord", "DeviceRegistry"]

logger = logging.getLogger(__name__)

_DEFAULT_TRUSTED_DEVICE_DAYS = 30


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _trusted_device_ttl_days() -> int:
    raw = (os.environ.get("DSP_AUTH_TRUSTED_DEVICE_DAYS") or "").strip()
    if not raw:
        return _DEFAULT_TRUSTED_DEVICE_DAYS
    try:
        value = int(raw)
    except ValueError:
        return _DEFAULT_TRUSTED_DEVICE_DAYS
    return value if value > 0 else _DEFAULT_TRUSTED_DEVICE_DAYS


def fingerprint(ip_hint: str | None, user_agent_hint: str | None) -> str:
    raw = f"{ip_hint or ''}|{user_agent_hint or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _as_bool(value: Any) -> bool:
    return value in (True, "true", "True", 1, "1")


class DeviceRecord:
    __slots__ = (
        "device_id",
        "user_id",
        "label",
        "fingerprint_hash",
        "ip_hint",
        "user_agent_hint",
        "trusted",
        "trusted_until",
        "last_seen_at",
        "created_at",
        "revoked",
    )

    def __init__(
        self,
        *,
        device_id: str,
        user_id: str,
        label: str,
        fingerprint_hash: str,
        ip_hint: str | None,
        user_agent_hint: str | None,
        trusted: bool,
        last_seen_at: str,
        created_at: str,
        revoked: bool = False,
        trusted_until: str | None = None,
    ) -> None:
        self.device_id = device_id
        self.user_id = user_id
        self.label = label
        self.fingerprint_hash = fingerprint_hash
        self.ip_hint = ip_hint
        self.user_agent_hint = user_agent_hint
        self.trusted = trusted
        self.trusted_until = trusted_until
        self.last_seen_at = last_seen_at
        self.created_at = created_at
        self.revoked = revoked

    def is_trust_active(self, *, now: datetime | None = None) -> bool:
        """Whether this device's "remembered" MFA trust is currently valid.

        A device can have ``trusted=True`` yet an expired ``trusted_until``
        (the record is intentionally kept, not deleted, so audit history and
        UI listings remain accurate) — callers must check both.
        """
        if not self.trusted:
            return False
        if not self.trusted_until:
            # Legacy records written before expiration support existed:
            # honor the trust flag as-is rather than silently revoking it.
            return True
        current = now or datetime.now(tz=UTC)
        try:
            expires = datetime.fromisoformat(self.trusted_until)
        except ValueError:
            return True
        return current < expires

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "user_id": self.user_id,
            "label": self.label,
            "fingerprint_hash": self.fingerprint_hash,
            "ip_hint": self.ip_hint,
            "user_agent_hint": self.user_agent_hint,
            "trusted": self.trusted,
            "trusted_until": self.trusted_until,
            "trust_active": self.is_trust_active(),
            "last_seen_at": self.last_seen_at,
            "created_at": self.created_at,
            "revoked": self.revoked,
        }

    def to_store_payload(self, *, session_id: str | None = None) -> dict[str, Any]:
        payload = {
            "auth_entity": "device",
            "device_id": self.device_id,
            "user_id": self.user_id,
            "label": self.label,
            "fingerprint_hash": self.fingerprint_hash,
            "ip_hint": self.ip_hint,
            "user_agent_hint": self.user_agent_hint,
            "trusted": bool(self.trusted),
            "trusted_until": self.trusted_until,
            "last_seen_at": self.last_seen_at,
            "created_at": self.created_at,
            "revoked": bool(self.revoked),
        }
        if session_id:
            payload["session_id"] = session_id
        return payload

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> DeviceRecord | None:
        device_id = str(payload.get("device_id") or "")
        user_id = str(payload.get("user_id") or "")
        if not device_id or not user_id:
            return None
        trusted_until = payload.get("trusted_until")
        return cls(
            device_id=device_id,
            user_id=user_id,
            label=str(payload.get("label") or "unknown")[:80],
            fingerprint_hash=str(payload.get("fingerprint_hash") or ""),
            ip_hint=payload.get("ip_hint"),
            user_agent_hint=payload.get("user_agent_hint"),
            trusted=_as_bool(payload.get("trusted")),
            last_seen_at=str(payload.get("last_seen_at") or payload.get("created_at") or ""),
            created_at=str(payload.get("created_at") or ""),
            revoked=_as_bool(payload.get("revoked")),
            trusted_until=None if trusted_until in (None, "") else str(trusted_until),
        )


class DeviceRegistry:
    """A008-backed device inventory shared across Cloud Run instances."""

    def __init__(self, persistence: Any | None = None, *, store: Any | None = None) -> None:
        from auth.device_store import DeviceStore, default_device_store

        self._store: DeviceStore = store if store is not None else default_device_store(persistence)
        self._lock = Lock()

    def get(self, device_id: str) -> DeviceRecord | None:
        payload = self._store.get_device(device_id)
        if payload is None:
            return None
        return DeviceRecord.from_payload(payload)

    def register(
        self,
        *,
        user_id: str,
        label: str | None = None,
        ip_hint: str | None = None,
        user_agent_hint: str | None = None,
        session_id: str | None = None,
    ) -> DeviceRecord:
        fp = fingerprint(ip_hint, user_agent_hint)
        now = _utc_now()
        with self._lock:
            existing_id = self._store.get_fingerprint_device_id(user_id, fp)
            if existing_id:
                live = self.get(existing_id)
                if live is not None and live.user_id == user_id and not live.revoked:
                    updated = self._store.merge_device(
                        live.device_id,
                        fields={
                            "last_seen_at": now,
                            "ip_hint": ip_hint,
                            "user_agent_hint": user_agent_hint,
                        },
                        updated_at=now,
                        user_id=user_id,
                        require_not_revoked=True,
                    )
                    record = DeviceRecord.from_payload(updated) if updated else live
                    if record is None:
                        record = live
                    record.last_seen_at = now
                    record.ip_hint = ip_hint
                    record.user_agent_hint = user_agent_hint
                    return record

            device = DeviceRecord(
                device_id=str(uuid.uuid4()),
                user_id=user_id,
                label=label or (user_agent_hint or "unknown")[:80],
                fingerprint_hash=fp,
                ip_hint=ip_hint,
                user_agent_hint=user_agent_hint,
                trusted=False,
                last_seen_at=now,
                created_at=now,
            )
            self._store.put_device(device.to_store_payload(session_id=session_id))
            winner_id = self._store.claim_fingerprint(
                user_id=user_id,
                fingerprint_hash=fp,
                device_id=device.device_id,
                created_at=now,
            )
            if winner_id != device.device_id:
                winner = self.get(winner_id)
                if winner is not None and winner.user_id == user_id and not winner.revoked:
                    self._store.delete_device(device.device_id)
                    patched = self._store.merge_device(
                        winner.device_id,
                        fields={
                            "last_seen_at": now,
                            "ip_hint": ip_hint,
                            "user_agent_hint": user_agent_hint,
                        },
                        updated_at=now,
                        user_id=user_id,
                        require_not_revoked=True,
                    )
                    return DeviceRecord.from_payload(patched) if patched else winner
                self._store.replace_fingerprint(
                    user_id=user_id,
                    fingerprint_hash=fp,
                    device_id=device.device_id,
                    created_at=now,
                )
            return device

    def list_for_user(self, user_id: str) -> list[dict[str, Any]]:
        rows = [
            record.to_dict()
            for payload in self._store.list_device_payloads_for_user(user_id)
            if (record := DeviceRecord.from_payload(payload)) is not None and not record.revoked
        ]
        rows.sort(key=lambda r: str(r.get("last_seen_at") or ""), reverse=True)
        return rows

    def set_trusted(
        self,
        device_id: str,
        *,
        user_id: str,
        trusted: bool,
        ttl_days: int | None = None,
    ) -> dict[str, Any]:
        """Mark ``device_id`` trusted (remembered for MFA step-up) or not.

        Trust always expires — ``ttl_days`` (default
        ``DSP_AUTH_TRUSTED_DEVICE_DAYS``, 30) bounds how long "remember this
        device" can skip MFA before re-verification is required again.
        """
        if trusted:
            days = ttl_days if ttl_days and ttl_days > 0 else _trusted_device_ttl_days()
            trusted_until: str | None = (
                datetime.now(tz=UTC) + timedelta(days=days)
            ).isoformat()
        else:
            trusted_until = None
        updated = self._store.merge_device(
            device_id,
            fields={"trusted": trusted, "trusted_until": trusted_until},
            updated_at=_utc_now(),
            user_id=user_id,
            require_not_revoked=True,
        )
        record = DeviceRecord.from_payload(updated) if updated else None
        if record is None:
            raise KeyError("device not found")
        return record.to_dict()

    def is_record_trusted(self, device: DeviceRecord) -> bool:
        """Trust check that also enforces :meth:`DeviceRecord.is_trust_active`."""
        return device.is_trust_active()

    def revoke(self, device_id: str, *, user_id: str | None = None) -> None:
        current = self.get(device_id)
        if current is None:
            raise KeyError("device not found")
        if user_id and current.user_id != user_id:
            raise KeyError("device not found")
        updated = self._store.merge_device(
            device_id,
            fields={"revoked": True},
            updated_at=_utc_now(),
            user_id=user_id,
        )
        if updated is None:
            raise KeyError("device not found")
        logger.info("device revoked")

    def revoke_all(self, user_id: str) -> int:
        count = 0
        for payload in self._store.list_device_payloads_for_user(user_id):
            record = DeviceRecord.from_payload(payload)
            if record is None or record.revoked:
                continue
            updated = self._store.merge_device(
                record.device_id,
                fields={"revoked": True},
                updated_at=_utc_now(),
                user_id=user_id,
            )
            if updated is not None:
                count += 1
        return count

    def is_trusted(self, user_id: str, *, ip_hint: str | None, user_agent_hint: str | None) -> bool:
        fp = fingerprint(ip_hint, user_agent_hint)
        device_id = self._store.get_fingerprint_device_id(user_id, fp)
        if not device_id:
            return False
        device = self.get(device_id)
        if device is None or device.user_id != user_id or device.revoked:
            return False
        return device.is_trust_active()
