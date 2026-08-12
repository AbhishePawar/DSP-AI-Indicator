"""Device tracking and trusted-device registry for enterprise sessions."""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any

__all__ = ["DeviceRecord", "DeviceRegistry"]

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


class DeviceRegistry:
    """In-process + persistence-backed device inventory."""

    def __init__(self, persistence: Any | None = None) -> None:
        self._persistence = persistence
        self._devices: dict[str, DeviceRecord] = {}
        self._lock = Lock()

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
            for device in self._devices.values():
                if (
                    device.user_id == user_id
                    and device.fingerprint_hash == fp
                    and not device.revoked
                ):
                    device.last_seen_at = now
                    device.ip_hint = ip_hint
                    device.user_agent_hint = user_agent_hint
                    self._persist(device)
                    return device
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
            self._devices[device.device_id] = device
            self._persist(device, session_id=session_id)
            return device

    def list_for_user(self, user_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = [
                d.to_dict()
                for d in self._devices.values()
                if d.user_id == user_id and not d.revoked
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
        with self._lock:
            device = self._devices.get(device_id)
            if device is None or device.user_id != user_id or device.revoked:
                raise KeyError("device not found")
            device.trusted = trusted
            if trusted:
                days = ttl_days if ttl_days and ttl_days > 0 else _trusted_device_ttl_days()
                device.trusted_until = (
                    datetime.now(tz=UTC) + timedelta(days=days)
                ).isoformat()
            else:
                device.trusted_until = None
            self._persist(device)
            return device.to_dict()

    def is_record_trusted(self, device: DeviceRecord) -> bool:
        """Trust check that also enforces :meth:`DeviceRecord.is_trust_active`."""
        return device.is_trust_active()

    def revoke(self, device_id: str, *, user_id: str | None = None) -> None:
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                raise KeyError("device not found")
            if user_id and device.user_id != user_id:
                raise KeyError("device not found")
            device.revoked = True
            self._persist(device)

    def revoke_all(self, user_id: str) -> int:
        count = 0
        with self._lock:
            for device in self._devices.values():
                if device.user_id == user_id and not device.revoked:
                    device.revoked = True
                    self._persist(device)
                    count += 1
        return count

    def is_trusted(self, user_id: str, *, ip_hint: str | None, user_agent_hint: str | None) -> bool:
        fp = fingerprint(ip_hint, user_agent_hint)
        with self._lock:
            return any(
                d.user_id == user_id
                and d.fingerprint_hash == fp
                and not d.revoked
                and d.is_trust_active()
                for d in self._devices.values()
            )

    def _persist(self, device: DeviceRecord, *, session_id: str | None = None) -> None:
        if self._persistence is None:
            return
        payload = device.to_dict()
        payload["auth_entity"] = "device"
        if session_id:
            payload["session_id"] = session_id
        try:
            self._persistence.put(
                kind="metadata",
                entity_id=f"auth-device-{device.device_id}",
                payload=payload,
                refs={"auth_entity": "device", "user_id": device.user_id},
                created_at=device.created_at,
                allow_update=True,
            )
        except Exception:  # noqa: BLE001
            pass
