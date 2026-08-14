"""Deterministic serialization (EPIC-A008)."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from typing import Any, Mapping
from uuid import UUID

from persistence.models import PersistedEntity, PersistenceSnapshot, freeze_mapping

__all__ = [
    "canonical_dumps",
    "content_hash",
    "entity_from_dict",
    "entity_to_dict",
    "snapshot_from_dict",
    "snapshot_to_dict",
    "to_plain_jsonable",
]


def to_plain_jsonable(obj: Any) -> Any:
    """Deterministic plain JSON-compatible structure."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.astimezone().isoformat() if obj.tzinfo else obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, Mapping):
        return {
            str(k): to_plain_jsonable(v)
            for k, v in sorted(obj.items(), key=lambda x: str(x[0]))
        }
    if isinstance(obj, (list, tuple)):
        return [to_plain_jsonable(v) for v in obj]
    if isinstance(obj, set):
        return sorted(to_plain_jsonable(v) for v in obj)
    return str(obj)


def canonical_dumps(obj: Any) -> str:
    return json.dumps(
        to_plain_jsonable(obj),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def content_hash(obj: Any) -> str:
    return hashlib.sha256(canonical_dumps(obj).encode("utf-8")).hexdigest()


def entity_to_dict(entity: PersistedEntity) -> dict[str, Any]:
    return to_plain_jsonable(entity.to_dict())


def entity_from_dict(data: Mapping[str, Any]) -> PersistedEntity:
    return PersistedEntity(
        entity_id=str(data.get("entity_id") or ""),
        kind=str(data.get("kind") or ""),
        created_at=str(data.get("created_at") or ""),
        updated_at=str(data.get("updated_at") or ""),
        version=int(data.get("version") or 1),
        payload=freeze_mapping(dict(data.get("payload") or {})),
        refs=freeze_mapping(dict(data.get("refs") or {})),
        provenance=freeze_mapping(dict(data.get("provenance") or {})),
    )


def snapshot_to_dict(snapshot: PersistenceSnapshot) -> dict[str, Any]:
    return to_plain_jsonable(snapshot.to_dict())


def snapshot_from_dict(data: Mapping[str, Any]) -> PersistenceSnapshot:
    return PersistenceSnapshot(
        snapshot_id=str(data.get("snapshot_id") or ""),
        kind=str(data.get("kind") or ""),
        created_at=str(data.get("created_at") or ""),
        source_entity_id=str(data.get("source_entity_id") or ""),
        content_hash=str(data.get("content_hash") or ""),
        payload=freeze_mapping(dict(data.get("payload") or {})),
        read_only=True,
    )
