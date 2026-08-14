"""Audit / workflow / research-ref viewers + search/export (EPIC-A010)."""

from __future__ import annotations

import json
from typing import Any

from admin.exceptions import ValidationError

__all__ = [
    "AuditViewer",
    "export_audit_metadata",
    "filter_records",
    "search_records",
]


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    payload = row.get("payload")
    return dict(payload) if isinstance(payload, dict) else {}


def filter_records(
    records: list[dict[str, Any]],
    *,
    query: str | None = None,
    subject: str | None = None,
    workflow_id: str | None = None,
    event_type: str | None = None,
) -> list[dict[str, Any]]:
    q = (query or "").strip().casefold()
    sub = (subject or "").strip().casefold()
    wid = (workflow_id or "").strip().casefold()
    et = (event_type or "").strip().casefold()
    out: list[dict[str, Any]] = []
    for row in records:
        payload = _payload(row)
        blob = json.dumps(row, sort_keys=True, default=str).casefold()
        if q and q not in blob:
            continue
        if sub and str(payload.get("subject") or row.get("refs", {}).get("subject") or "").casefold() != sub:
            if sub not in blob:
                continue
        if wid:
            cand = str(
                payload.get("workflow_id")
                or (row.get("refs") or {}).get("workflow_id")
                or ""
            ).casefold()
            if cand != wid and wid not in blob:
                continue
        if et:
            cand = str(
                payload.get("event_type") or payload.get("type") or payload.get("action") or ""
            ).casefold()
            if cand != et and et not in blob:
                continue
        out.append(row)
    return out


def search_records(
    records: list[dict[str, Any]],
    query: str,
) -> list[dict[str, Any]]:
    if not str(query or "").strip():
        raise ValidationError("query is required")
    return filter_records(records, query=query)


def export_audit_metadata(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic JSON-serializable export — metadata only, no research bodies."""
    ordered = sorted(
        records,
        key=lambda r: (
            str(r.get("created_at") or ""),
            str(r.get("entity_id") or ""),
        ),
    )
    return {
        "export_kind": "audit_metadata",
        "count": len(ordered),
        "records": ordered,
        "rules": [
            "metadata_only",
            "no_research_mutation",
            "no_engine_execution",
            "deterministic_order",
        ],
    }


class AuditViewer:
    def __init__(self, persistence_service: Any) -> None:
        self._persistence = persistence_service

    def list_audit_records(self) -> list[dict[str, Any]]:
        rows = self._persistence.list_entities("audit_record")
        rows.sort(
            key=lambda r: (
                str(r.get("created_at") or ""),
                str(r.get("entity_id") or ""),
            )
        )
        return rows

    def list_workflow_history(self) -> list[dict[str, Any]]:
        rows = self._persistence.list_entities("workflow_record")
        rows.sort(
            key=lambda r: (
                str(r.get("created_at") or ""),
                str(r.get("entity_id") or ""),
            )
        )
        return rows

    def list_approval_history(self) -> list[dict[str, Any]]:
        rows = self._persistence.list_entities("approval_history")
        rows.sort(
            key=lambda r: (
                str(r.get("created_at") or ""),
                str(r.get("entity_id") or ""),
            )
        )
        return rows

    def list_research_archive_metadata(self) -> list[dict[str, Any]]:
        """Research *references* only — never research payloads."""
        rows = self._persistence.list_entities("research_ref")
        rows.sort(
            key=lambda r: (
                str(r.get("created_at") or ""),
                str(r.get("entity_id") or ""),
            )
        )
        return rows

    def activity_timeline(self, *, limit: int = 100) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for row in self.list_audit_records():
            events.append(
                {
                    "kind": "audit_record",
                    "entity_id": row.get("entity_id"),
                    "created_at": row.get("created_at"),
                    "summary": _payload(row),
                }
            )
        for row in self.list_workflow_history():
            payload = _payload(row)
            events.append(
                {
                    "kind": "workflow_record",
                    "entity_id": row.get("entity_id"),
                    "created_at": row.get("updated_at") or row.get("created_at"),
                    "summary": {
                        "workflow_id": payload.get("workflow_id"),
                        "stage": payload.get("stage"),
                        "subject": payload.get("subject"),
                    },
                }
            )
        events.sort(
            key=lambda e: (str(e.get("created_at") or ""), str(e.get("entity_id") or "")),
            reverse=True,
        )
        return events[: max(0, int(limit))]
