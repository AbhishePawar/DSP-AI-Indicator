"""Compliance export interfaces (PEP-004 / DPDP data principal rights)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

__all__ = [
    "ComplianceExport",
    "ComplianceExportPort",
    "InMemoryComplianceExportPort",
]


@dataclass(frozen=True, slots=True)
class ComplianceExport:
    """Portable export envelope for a data principal."""

    export_id: str
    subject_id: str
    generated_at: datetime
    locale: str = "en-IN"
    timezone: str = "Asia/Kolkata"
    currency: str = "INR"
    payload: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        body = {
            "export_id": self.export_id,
            "subject_id": self.subject_id,
            "generated_at": self.generated_at.isoformat(),
            "locale": self.locale,
            "timezone": self.timezone,
            "currency": self.currency,
            "payload": self.payload,
        }
        return json.dumps(body, indent=2, sort_keys=True)


@runtime_checkable
class ComplianceExportPort(Protocol):
    """Export consent + history + archive references for a subject."""

    def export_subject(self, subject_id: str) -> ComplianceExport:
        """Build an export package."""


class InMemoryComplianceExportPort:
    """Builds exports from in-memory compliance stores passed at construction."""

    def __init__(
        self,
        *,
        consents: Any,
        history: Any | None = None,
        archive: Any | None = None,
        audit_refs: Any | None = None,
    ) -> None:
        self._consents = consents
        self._history = history
        self._archive = archive
        self._audit_refs = audit_refs

    def export_subject(self, subject_id: str) -> ComplianceExport:
        import uuid

        consent_rows = []
        for c in self._consents.list_for_subject(subject_id):
            consent_rows.append(
                {
                    "consent_id": c.consent_id,
                    "purpose_id": c.purpose_id,
                    "granted": c.granted,
                    "policy_version": c.policy_version,
                    "recorded_at": c.recorded_at.isoformat(),
                }
            )
        payload: dict[str, Any] = {"consents": consent_rows}
        if self._audit_refs is not None:
            payload["audit_references"] = [
                {
                    "reference_id": r.reference_id,
                    "event_id": r.event_id,
                    "content_hash": r.content_hash,
                    "retention_until": r.retention_until.isoformat(),
                }
                for r in self._audit_refs.list_references(limit=500)
            ]
        if self._archive is not None and hasattr(self._archive, "list_all"):
            payload["research_archives"] = [
                {
                    "archive_id": a.archive_id,
                    "report_ref": a.report_ref,
                    "archived_at": a.archived_at.isoformat(),
                    "retention_class": a.retention_class,
                }
                for a in self._archive.list_all()
            ]
        _ = self._history
        return ComplianceExport(
            export_id=f"exp_{uuid.uuid4().hex[:12]}",
            subject_id=subject_id,
            generated_at=datetime.now(tz=UTC),
            payload=payload,
        )
