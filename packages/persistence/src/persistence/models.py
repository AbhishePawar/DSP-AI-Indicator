"""Persistence domain models (EPIC-A008).

Stores references and metadata only — research artifact payloads are never stored.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Mapping

__all__ = [
    "ENTITY_KINDS",
    "PERSISTENCE_SCHEMA_VERSION",
    "PERSISTENCE_SERVICE_VERSION",
    "UNAVAILABLE_MESSAGE",
    "PersistedEntity",
    "PersistenceSnapshot",
    "freeze_mapping",
    "utc_now",
]

PERSISTENCE_SCHEMA_VERSION = "1.0.0"
PERSISTENCE_SERVICE_VERSION = "1.0.0"
UNAVAILABLE_MESSAGE = "Data unavailable."

ENTITY_KINDS = (
    "research_ref",
    "workflow_record",
    "approval_history",
    "audit_record",
    "citation",
    "provenance",
    "metadata",
)


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if value is None:
        return MappingProxyType({})

    def _freeze(obj: Any) -> Any:
        if isinstance(obj, Mapping):
            return MappingProxyType({str(k): _freeze(v) for k, v in obj.items()})
        if isinstance(obj, list):
            return tuple(_freeze(v) for v in obj)
        if isinstance(obj, tuple):
            return tuple(_freeze(v) for v in obj)
        return obj

    return _freeze(value)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class PersistedEntity:
    entity_id: str
    kind: str
    created_at: str
    updated_at: str
    version: int = 1
    # References / metadata only — never research payload bodies
    payload: Mapping[str, Any] = field(default_factory=dict)
    refs: Mapping[str, Any] = field(default_factory=dict)
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        def _plain(obj: Any) -> Any:
            if isinstance(obj, Mapping):
                return {str(k): _plain(v) for k, v in sorted(obj.items(), key=lambda x: str(x[0]))}
            if isinstance(obj, (list, tuple)):
                return [_plain(v) for v in obj]
            return obj

        return {
            "entity_id": self.entity_id,
            "kind": self.kind,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "payload": _plain(self.payload),
            "refs": _plain(self.refs),
            "provenance": _plain(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class PersistenceSnapshot:
    snapshot_id: str
    kind: str  # workflow | audit | metadata
    created_at: str
    source_entity_id: str
    content_hash: str
    payload: Mapping[str, Any]
    read_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        def _plain(obj: Any) -> Any:
            if isinstance(obj, Mapping):
                return {str(k): _plain(v) for k, v in sorted(obj.items(), key=lambda x: str(x[0]))}
            if isinstance(obj, (list, tuple)):
                return [_plain(v) for v in obj]
            return obj

        return {
            "snapshot_id": self.snapshot_id,
            "kind": self.kind,
            "created_at": self.created_at,
            "source_entity_id": self.source_entity_id,
            "content_hash": self.content_hash,
            "payload": _plain(self.payload),
            "read_only": True,
        }
