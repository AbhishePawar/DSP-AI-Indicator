"""Platform façade helpers for Persistence (EPIC-A008)."""

from __future__ import annotations

from typing import Any, Mapping

from persistence import (
    PERSISTENCE_SCHEMA_VERSION,
    PERSISTENCE_SERVICE_VERSION,
    get_persistence_service,
)

__all__ = [
    "persistence_schema",
    "persist_canonical_entity",
    "persist_canonical_workflow_record",
    "create_canonical_persistence_snapshot",
    "get_canonical_persisted_entity",
]


def persistence_schema() -> dict[str, Any]:
    return get_persistence_service().schema()


def persist_canonical_entity(
    *,
    kind: str,
    payload: Mapping[str, Any] | None = None,
    refs: Mapping[str, Any] | None = None,
    provenance: Mapping[str, Any] | None = None,
    entity_id: str | None = None,
    created_at: str | None = None,
    allow_update: bool = True,
) -> dict[str, Any]:
    return get_persistence_service().put(
        kind=kind,
        payload=payload,
        refs=refs,
        provenance=provenance,
        entity_id=entity_id,
        created_at=created_at,
        allow_update=allow_update,
    )


def get_canonical_persisted_entity(kind: str, entity_id: str) -> dict[str, Any] | None:
    return get_persistence_service().get(kind, entity_id)


def persist_canonical_workflow_record(
    workflow: Mapping[str, Any],
    *,
    entity_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    return get_persistence_service().persist_workflow_record(
        workflow, entity_id=entity_id, created_at=created_at
    )


def create_canonical_persistence_snapshot(
    *,
    kind: str,
    source_entity_id: str,
    payload: Mapping[str, Any],
    snapshot_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    return get_persistence_service().create_snapshot(
        kind=kind,
        source_entity_id=source_entity_id,
        payload=payload,
        snapshot_id=snapshot_id,
        created_at=created_at,
    )
