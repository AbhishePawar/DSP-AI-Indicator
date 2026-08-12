"""Persistence service (EPIC-A008)."""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from persistence.exceptions import ValidationError
from persistence.models import (
    ENTITY_KINDS,
    PERSISTENCE_SCHEMA_VERSION,
    PERSISTENCE_SERVICE_VERSION,
    PersistedEntity,
    PersistenceSnapshot,
    freeze_mapping,
    utc_now,
)
from persistence.registry import get_repository_registry
from persistence.serde import content_hash, entity_to_dict, snapshot_to_dict, to_plain_jsonable
from persistence.transactions import TransactionManager
from persistence.validation import validate_entity

__all__ = [
    "PERSISTENCE_SERVICE_VERSION",
    "PersistenceService",
    "get_persistence_service",
    "reset_persistence_service_for_tests",
]


class PersistenceService:
    """Durable metadata persistence — does not mutate research artifacts."""

    def __init__(self, registry: Any | None = None) -> None:
        self.registry = registry or get_repository_registry()
        self.tx = TransactionManager(self.registry.storage)

    def schema(self) -> dict[str, Any]:
        return {
            "schema_version": PERSISTENCE_SCHEMA_VERSION,
            "service_version": PERSISTENCE_SERVICE_VERSION,
            "provider": getattr(self.registry.storage, "provider_id", "unknown"),
            "entity_kinds": list(ENTITY_KINDS),
            "snapshot_kinds": ["workflow", "audit", "metadata"],
            "rules": [
                "metadata_and_references_only",
                "no_research_payload_storage",
                "no_research_mutation",
                "deterministic_serialization",
                "immutable_snapshots",
            ],
        }

    def put(
        self,
        *,
        kind: str,
        payload: Mapping[str, Any] | None = None,
        refs: Mapping[str, Any] | None = None,
        provenance: Mapping[str, Any] | None = None,
        entity_id: str | None = None,
        created_at: str | None = None,
        allow_update: bool = True,
    ) -> dict[str, Any]:
        if kind not in ENTITY_KINDS:
            raise ValidationError(f"invalid kind {kind!r}")
        created = created_at or utc_now().isoformat()
        eid = entity_id or str(uuid.uuid4())
        entity = PersistedEntity(
            entity_id=eid,
            kind=kind,
            created_at=created,
            updated_at=created,
            version=1,
            payload=freeze_mapping(to_plain_jsonable(dict(payload or {}))),
            refs=freeze_mapping(to_plain_jsonable(dict(refs or {}))),
            provenance=freeze_mapping(
                to_plain_jsonable(
                    {
                        "source": "persistence",
                        "service_version": PERSISTENCE_SERVICE_VERSION,
                        "research_mutated": False,
                        **dict(provenance or {}),
                    }
                )
            ),
        )
        validate_entity(entity)
        saved = self.registry.repository(kind).put(entity, allow_update=allow_update)
        return entity_to_dict(saved)

    def get(self, kind: str, entity_id: str) -> dict[str, Any] | None:
        entity = self.registry.repository(kind).get(entity_id)
        return entity_to_dict(entity) if entity is not None else None

    def delete(self, kind: str, entity_id: str) -> bool:
        return self.registry.repository(kind).delete(entity_id)

    def list_ids(self, kind: str) -> list[str]:
        return list(self.registry.repository(kind).list_ids())

    def list_entities(self, kind: str) -> list[dict[str, Any]]:
        return [entity_to_dict(e) for e in self.registry.repository(kind).list_entities()]

    def persist_workflow_record(
        self,
        workflow: Mapping[str, Any],
        *,
        entity_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        """Store workflow metadata/state as a reference record — no research bodies."""
        wf = to_plain_jsonable(dict(workflow))
        wid = str(wf.get("workflow_id") or entity_id or "")
        if not wid:
            raise ValidationError("workflow_id required")
        # Strip any accidental nested research payloads
        refs = to_plain_jsonable(dict(wf.get("artifact_refs") or {}))
        safe_payload = {
            "workflow_id": wid,
            "template_id": wf.get("template_id"),
            "subject": wf.get("subject"),
            "stage": wf.get("stage"),
            "created_at": wf.get("created_at"),
            "updated_at": wf.get("updated_at"),
            "reviewers": wf.get("reviewers") or [],
            "approvals": wf.get("approvals") or [],
            "decision_history": wf.get("decision_history") or [],
            "audit_trail": wf.get("audit_trail") or [],
            "comment_ids": [
                c.get("comment_id")
                for c in (wf.get("comments") or [])
                if isinstance(c, Mapping)
            ],
        }
        return self.put(
            kind="workflow_record",
            entity_id=entity_id or f"wfrec-{wid}",
            payload=safe_payload,
            refs=refs,
            created_at=created_at or str(wf.get("updated_at") or ""),
        )

    def persist_audit_record(
        self,
        audit_entry: Mapping[str, Any],
        *,
        entity_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        entry = to_plain_jsonable(dict(audit_entry))
        eid = entity_id or str(entry.get("event_id") or entry.get("id") or uuid.uuid4())
        return self.put(
            kind="audit_record",
            entity_id=f"audit-{eid}" if not str(eid).startswith("audit-") else eid,
            payload=entry,
            refs={
                k: entry[k]
                for k in ("workflow_id", "subject", "ref_id")
                if entry.get(k)
            },
            created_at=created_at or str(entry.get("created_at") or ""),
        )

    def persist_citation(
        self,
        citation: Mapping[str, Any],
        *,
        entity_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        cite = to_plain_jsonable(dict(citation))
        path = str(cite.get("path") or "")
        section = str(cite.get("section") or "")
        if not path or not section:
            raise ValidationError("citation requires path and section")
        eid = entity_id or f"cite-{content_hash({'path': path, 'section': section})[:16]}"
        return self.put(
            kind="citation",
            entity_id=eid,
            payload=cite,
            refs={
                k: cite[k]
                for k in ("ref_id", "source_kind", "symbol")
                if cite.get(k)
            },
            created_at=created_at,
        )

    def persist_provenance(
        self,
        provenance: Mapping[str, Any],
        *,
        entity_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        prov = to_plain_jsonable(dict(provenance))
        eid = entity_id or f"prov-{content_hash(prov)[:16]}"
        return self.put(
            kind="provenance",
            entity_id=eid,
            payload=prov,
            refs={
                k: prov[k]
                for k in ("workflow_id", "result_id", "source")
                if prov.get(k)
            },
            created_at=created_at,
        )

    def create_snapshot(
        self,
        *,
        kind: str,
        source_entity_id: str,
        payload: Mapping[str, Any],
        snapshot_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        if kind not in {"workflow", "audit", "metadata"}:
            raise ValidationError(f"invalid snapshot kind {kind!r}")
        plain = to_plain_jsonable(dict(payload))
        created = created_at or utc_now().isoformat()
        snap = PersistenceSnapshot(
            snapshot_id=snapshot_id or str(uuid.uuid4()),
            kind=kind,
            created_at=created,
            source_entity_id=str(source_entity_id),
            content_hash=content_hash(plain),
            payload=freeze_mapping(plain),
            read_only=True,
        )
        saved = self.registry.snapshots.put(snap)
        return snapshot_to_dict(saved)

    def get_snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        snap = self.registry.snapshots.get(snapshot_id)
        return snapshot_to_dict(snap) if snap is not None else None

    def begin(self) -> None:
        self.tx.begin()

    def commit(self) -> None:
        self.tx.commit()

    def rollback(self) -> None:
        self.tx.rollback()


_SVC: PersistenceService | None = None


def get_persistence_service() -> PersistenceService:
    global _SVC
    if _SVC is None:
        _SVC = PersistenceService()
    return _SVC


def reset_persistence_service_for_tests(
    service: PersistenceService | None = None,
) -> None:
    global _SVC
    _SVC = service
