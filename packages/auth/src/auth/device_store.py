"""Durable trusted-device store (A008 metadata).

Device trust/revocation on Cloud Run cannot use process-local dicts. Device
records and fingerprint indexes are persisted through A008 (Postgres in
production). Fingerprint claim uses a compare-and-set insert so two instances
cannot create two live devices for the same user+fingerprint.

Entity identifiers:
- ``auth-device-{uuid}`` — device record (fingerprint is already hashed)
- ``auth-device-fp-{hmac}`` — HMAC of user_id+fingerprint, not the raw fingerprint
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import Any

from auth.credential_boundary import resolve_auth_jwt_secret

__all__ = [
    "DeviceStore",
    "default_device_store",
    "resolve_device_persistence",
]

logger = logging.getLogger(__name__)

_ENTITY_KIND = "metadata"
_DEVICE_PREFIX = "auth-device-"
_FP_PREFIX = "auth-device-fp-"
_HMAC_INFO = b"dsp.device.id.v1"


def _hmac_id(message: str) -> str:
    key = resolve_auth_jwt_secret().encode("utf-8")
    material = _HMAC_INFO + b":" + message.encode("utf-8")
    return hmac.new(key, material, hashlib.sha256).hexdigest()


def _device_entity_id(device_id: str) -> str:
    return f"{_DEVICE_PREFIX}{device_id}"


def _fp_entity_id(user_id: str, fingerprint_hash: str) -> str:
    return f"{_FP_PREFIX}{_hmac_id(f'{user_id}:{fingerprint_hash}')}"


def _is_device_entity_id(entity_id: str) -> bool:
    return entity_id.startswith(_DEVICE_PREFIX) and not entity_id.startswith(_FP_PREFIX)


def resolve_device_persistence(persistence: Any | None = None) -> Any:
    if persistence is not None:
        return persistence
    environment = (os.environ.get("DSP_ENVIRONMENT") or "").strip().lower()
    if environment == "production":
        from persistence import get_persistence_service

        return get_persistence_service()
    from persistence import InMemoryStorageProvider, PersistenceService, RepositoryRegistry

    return PersistenceService(RepositoryRegistry(storage=InMemoryStorageProvider()))


def default_device_store(persistence: Any | None = None) -> DeviceStore:
    return DeviceStore(resolve_device_persistence(persistence))


class DeviceStore:
    """Put/get/claim trusted-device records on the shared A008 persistence service."""

    def __init__(self, persistence_service: Any | None = None) -> None:
        self._persistence = resolve_device_persistence(persistence_service)

    def put_device(self, payload: dict[str, Any]) -> None:
        device_id = str(payload.get("device_id") or "")
        created_at = str(payload.get("created_at") or "")
        self._persistence.put(
            kind=_ENTITY_KIND,
            entity_id=_device_entity_id(device_id),
            payload=dict(payload),
            refs={"auth_entity": "device", "user_id": payload.get("user_id")},
            created_at=created_at,
            allow_update=True,
        )
        logger.info("device record stored")

    def get_device(self, device_id: str) -> dict[str, Any] | None:
        row = self._persistence.get(_ENTITY_KIND, _device_entity_id(device_id))
        if row is None:
            return None
        payload = dict(row.get("payload") or {})
        return payload or None

    def delete_device(self, device_id: str) -> bool:
        return bool(self._persistence.delete(_ENTITY_KIND, _device_entity_id(device_id)))

    def get_fingerprint_device_id(self, user_id: str, fingerprint_hash: str) -> str | None:
        row = self._persistence.get(_ENTITY_KIND, _fp_entity_id(user_id, fingerprint_hash))
        if row is None:
            return None
        payload = dict(row.get("payload") or {})
        device_id = str(payload.get("device_id") or "")
        return device_id or None

    def claim_fingerprint(
        self,
        *,
        user_id: str,
        fingerprint_hash: str,
        device_id: str,
        created_at: str,
    ) -> str:
        stored = self._persistence.atomic_put_if_absent(
            kind=_ENTITY_KIND,
            entity_id=_fp_entity_id(user_id, fingerprint_hash),
            payload={
                "auth_entity": "device_fingerprint",
                "device_id": device_id,
                "user_id": user_id,
            },
            refs={"auth_entity": "device_fingerprint"},
            created_at=created_at,
        )
        payload = dict(stored.get("payload") or {})
        winner = str(payload.get("device_id") or device_id)
        logger.info("device fingerprint claimed")
        return winner

    def replace_fingerprint(
        self,
        *,
        user_id: str,
        fingerprint_hash: str,
        device_id: str,
        created_at: str,
    ) -> None:
        self._persistence.put(
            kind=_ENTITY_KIND,
            entity_id=_fp_entity_id(user_id, fingerprint_hash),
            payload={
                "auth_entity": "device_fingerprint",
                "device_id": device_id,
                "user_id": user_id,
            },
            refs={"auth_entity": "device_fingerprint"},
            created_at=created_at,
            allow_update=True,
        )

    def merge_device(
        self,
        device_id: str,
        *,
        fields: dict[str, Any],
        updated_at: str,
        user_id: str | None = None,
        require_not_revoked: bool = False,
    ) -> dict[str, Any] | None:
        match: dict[str, Any] = {}
        if user_id is not None:
            match["user_id"] = user_id
        if require_not_revoked:
            match["revoked"] = False
        stored = self._persistence.atomic_merge_payload(
            _ENTITY_KIND,
            _device_entity_id(device_id),
            fields=fields,
            updated_at=updated_at,
            match=match or None,
        )
        if stored is None:
            return None
        payload = dict(stored.get("payload") or {})
        return payload or None

    def list_device_payloads_for_user(self, user_id: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for entity_id in self._persistence.list_ids(_ENTITY_KIND):
            if not _is_device_entity_id(str(entity_id)):
                continue
            row = self._persistence.get(_ENTITY_KIND, str(entity_id))
            if row is None:
                continue
            payload = dict(row.get("payload") or {})
            if str(payload.get("user_id") or "") != user_id:
                continue
            rows.append(payload)
        return rows
