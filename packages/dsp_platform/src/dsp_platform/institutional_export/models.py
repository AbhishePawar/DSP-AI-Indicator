"""Institutional Export models (EPIC-R003).

Read-only export artifacts projected from Institutional Report (R002) only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Mapping

from dsp_platform.research_object.models import UNAVAILABLE_MESSAGE, freeze_mapping

__all__ = [
    "EXPORT_FORMATS",
    "EXPORT_SCHEMA_VERSION",
    "EXPORTER_VERSION",
    "UNAVAILABLE_MESSAGE",
    "ExportArtifact",
    "ExportMetadata",
    "ExportVersion",
    "freeze_mapping",
    "utc_now",
]

EXPORT_SCHEMA_VERSION = "1.0.0"
EXPORTER_VERSION = "1.0.0"
EXPORT_FORMATS = ("json", "csv", "xlsx", "pdf", "docx", "pptx")


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True)
class ExportMetadata:
    export_id: str
    format: str
    schema_version: str
    exporter_version: str
    report_id: str
    report_schema_version: str
    research_object_id: str | None
    exported_at: str
    content_type: str
    filename: str
    byte_length: int
    research_mode: str | None = None
    correlation_id: str | None = None
    ticker: str | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        def _plain(obj: Any) -> Any:
            if isinstance(obj, Mapping):
                return {str(k): _plain(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_plain(v) for v in obj]
            return obj

        return {
            "export_id": self.export_id,
            "format": self.format,
            "schema_version": self.schema_version,
            "exporter_version": self.exporter_version,
            "report_id": self.report_id,
            "report_schema_version": self.report_schema_version,
            "research_object_id": self.research_object_id,
            "exported_at": self.exported_at,
            "content_type": self.content_type,
            "filename": self.filename,
            "byte_length": self.byte_length,
            "research_mode": self.research_mode,
            "correlation_id": self.correlation_id,
            "ticker": self.ticker,
            "provenance": _plain(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class ExportVersion:
    schema_version: str
    exporter_version: str
    report_schema_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "exporter_version": self.exporter_version,
            "report_schema_version": self.report_schema_version,
        }


@dataclass(frozen=True, slots=True)
class ExportArtifact:
    """Immutable export result — bytes preserved as base64 for transport."""

    metadata: ExportMetadata
    version: ExportVersion
    content_base64: str
    content_sha256: str
    content_text: str | None = None  # json/csv convenience; never reformats research values
    structured_json: Mapping[str, Any] | None = None  # json format only

    def to_dict(self) -> dict[str, Any]:
        def _plain(obj: Any) -> Any:
            if isinstance(obj, Mapping):
                return {str(k): _plain(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_plain(v) for v in obj]
            return obj

        return {
            "metadata": self.metadata.to_dict(),
            "version": self.version.to_dict(),
            "content_base64": self.content_base64,
            "content_sha256": self.content_sha256,
            "content_text": self.content_text,
            "structured_json": _plain(self.structured_json)
            if self.structured_json is not None
            else None,
        }
