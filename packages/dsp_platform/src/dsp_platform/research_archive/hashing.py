"""Canonical hashing + subject extraction for archive (EPIC-R004)."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

__all__ = [
    "canonical_json_bytes",
    "content_sha256",
    "extract_subject_ids",
    "infer_content_schema_version",
    "infer_ticker",
    "to_plain_jsonable",
]


def to_plain_jsonable(value: Any) -> Any:
    """Normalize mappings/sequences for deterministic JSON (tuples→lists)."""
    if isinstance(value, Mapping):
        return {str(k): to_plain_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_plain_jsonable(v) for v in value]
    return value


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    """Deterministic JSON bytes for integrity hashing."""
    plain = to_plain_jsonable(payload)
    return json.dumps(
        plain,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def content_sha256(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def infer_content_schema_version(kind: str, payload: Mapping[str, Any]) -> str:
    if kind == "research_object":
        version = payload.get("version")
        if isinstance(version, Mapping) and version.get("schema_version"):
            return str(version["schema_version"])
        return str(payload.get("schema_version") or "unknown")
    if kind == "institutional_report":
        version = payload.get("version")
        if isinstance(version, Mapping) and version.get("schema_version"):
            return str(version["schema_version"])
        return str(payload.get("schema_version") or "unknown")
    if kind == "export_metadata":
        meta = payload.get("metadata")
        if isinstance(meta, Mapping) and meta.get("schema_version"):
            return str(meta["schema_version"])
        version = payload.get("version")
        if isinstance(version, Mapping) and version.get("schema_version"):
            return str(version["schema_version"])
        return str(payload.get("schema_version") or "unknown")
    return "unknown"


def infer_ticker(kind: str, payload: Mapping[str, Any]) -> str | None:
    meta = payload.get("metadata")
    if isinstance(meta, Mapping) and meta.get("ticker"):
        return str(meta["ticker"])
    identity = payload.get("identity")
    if isinstance(identity, Mapping):
        id_payload = identity.get("payload")
        if isinstance(id_payload, Mapping):
            if id_payload.get("ticker"):
                return str(id_payload["ticker"])
            if id_payload.get("symbol"):
                return str(id_payload["symbol"])
    return None


def extract_subject_ids(kind: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Pass-through identifiers already present on R001/R002/R003 payloads."""
    ids: dict[str, Any] = {"kind": kind}
    meta = payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {}
    if kind == "research_object":
        ids["research_object_id"] = meta.get("research_object_id")
        ids["correlation_id"] = meta.get("correlation_id")
    elif kind == "institutional_report":
        ids["report_id"] = meta.get("report_id")
        ids["research_object_id"] = meta.get("research_object_id")
        ids["correlation_id"] = meta.get("correlation_id")
    elif kind == "export_metadata":
        src = meta if meta else payload
        ids["export_id"] = src.get("export_id")
        ids["report_id"] = src.get("report_id")
        ids["research_object_id"] = src.get("research_object_id")
        ids["format"] = src.get("format")
    return ids
