"""Persistence validation (EPIC-A008)."""

from __future__ import annotations

from typing import Mapping

from persistence.exceptions import ValidationError
from persistence.models import ENTITY_KINDS, PersistedEntity, PersistenceSnapshot

__all__ = [
    "validate_entity",
    "validate_snapshot",
    "validate_refs",
]


def validate_refs(refs: Mapping[str, object] | None) -> None:
    if refs is None:
        return
    for key, value in refs.items():
        if not str(key).strip():
            raise ValidationError("empty ref key")
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationError(f"broken reference for {key!r}")


def validate_entity(entity: PersistedEntity) -> None:
    if not entity.entity_id.strip():
        raise ValidationError("missing entity_id")
    if entity.kind not in ENTITY_KINDS:
        raise ValidationError(f"invalid kind {entity.kind!r}")
    if not entity.created_at or not entity.updated_at:
        raise ValidationError("missing timestamps")
    if entity.version < 1:
        raise ValidationError("version must be >= 1")
    validate_refs(dict(entity.refs))
    # Never store research payload bodies under reserved keys
    banned = {"research_object", "institutional_report", "analysis_payload"}
    for key in entity.payload.keys():
        if str(key) in banned:
            raise ValidationError(
                f"payload key {key!r} forbidden — research artifacts are immutable "
                "and must not be duplicated in persistence"
            )


def validate_snapshot(snapshot: PersistenceSnapshot) -> None:
    if not snapshot.snapshot_id.strip():
        raise ValidationError("missing snapshot_id")
    if snapshot.kind not in {"workflow", "audit", "metadata"}:
        raise ValidationError(f"invalid snapshot kind {snapshot.kind!r}")
    if not snapshot.source_entity_id.strip():
        raise ValidationError("missing source_entity_id")
    if not snapshot.content_hash.strip():
        raise ValidationError("missing content_hash")
    if not snapshot.read_only:
        raise ValidationError("snapshots must be read_only")
    if not snapshot.created_at:
        raise ValidationError("missing created_at")
