"""Serialize export artifacts (EPIC-R003)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.institutional_export.models import (
    EXPORT_SCHEMA_VERSION,
    EXPORTER_VERSION,
    ExportArtifact,
    ExportMetadata,
    ExportVersion,
    freeze_mapping,
)
from dsp_platform.institutional_export.validation import (
    InstitutionalExportValidationError,
    validate_export_artifact,
)

__all__ = [
    "export_artifact_from_dict",
    "export_artifact_to_dict",
]


def export_artifact_to_dict(artifact: ExportArtifact) -> dict[str, Any]:
    validate_export_artifact(artifact)
    return artifact.to_dict()


def export_artifact_from_dict(data: Mapping[str, Any]) -> ExportArtifact:
    if not isinstance(data, Mapping):
        raise InstitutionalExportValidationError("export artifact must be a mapping")
    meta_raw = data.get("metadata")
    if not isinstance(meta_raw, Mapping):
        raise InstitutionalExportValidationError("missing metadata")

    version_raw = data.get("version") or {}
    if not isinstance(version_raw, Mapping):
        version_raw = {}

    version = ExportVersion(
        schema_version=str(
            version_raw.get("schema_version") or EXPORT_SCHEMA_VERSION
        ),
        exporter_version=str(
            version_raw.get("exporter_version") or EXPORTER_VERSION
        ),
        report_schema_version=str(
            version_raw.get("report_schema_version") or ""
        ),
    )

    provenance = meta_raw.get("provenance") or {}
    metadata = ExportMetadata(
        export_id=str(meta_raw.get("export_id") or ""),
        format=str(meta_raw.get("format") or ""),
        schema_version=str(meta_raw.get("schema_version") or version.schema_version),
        exporter_version=str(
            meta_raw.get("exporter_version") or version.exporter_version
        ),
        report_id=str(meta_raw.get("report_id") or ""),
        report_schema_version=str(
            meta_raw.get("report_schema_version") or version.report_schema_version
        ),
        research_object_id=meta_raw.get("research_object_id"),
        exported_at=str(meta_raw.get("exported_at") or ""),
        content_type=str(meta_raw.get("content_type") or ""),
        filename=str(meta_raw.get("filename") or ""),
        byte_length=int(meta_raw.get("byte_length") or 0),
        research_mode=meta_raw.get("research_mode"),
        correlation_id=meta_raw.get("correlation_id"),
        ticker=meta_raw.get("ticker"),
        provenance=freeze_mapping(dict(provenance))
        if isinstance(provenance, Mapping)
        else freeze_mapping({}),
    )

    structured = data.get("structured_json")
    artifact = ExportArtifact(
        metadata=metadata,
        version=version,
        content_base64=str(data.get("content_base64") or ""),
        content_sha256=str(data.get("content_sha256") or ""),
        content_text=data.get("content_text"),
        structured_json=freeze_mapping(dict(structured))
        if isinstance(structured, Mapping)
        else None,
    )
    validate_export_artifact(artifact)
    return artifact
