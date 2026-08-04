"""Validate export artifacts (EPIC-R003)."""

from __future__ import annotations

from dsp_platform.institutional_export.models import (
    EXPORT_FORMATS,
    EXPORT_SCHEMA_VERSION,
    ExportArtifact,
)

__all__ = [
    "InstitutionalExportValidationError",
    "validate_export_artifact",
    "validate_export_format",
]


class InstitutionalExportValidationError(ValueError):
    """Export artifact failed structural validation."""


def validate_export_format(fmt: str) -> str:
    normalized = fmt.strip().lower()
    if normalized == "excel":
        normalized = "xlsx"
    if normalized not in EXPORT_FORMATS:
        raise InstitutionalExportValidationError(
            f"unsupported export format {fmt!r}; allowed={EXPORT_FORMATS}"
        )
    return normalized


def validate_export_artifact(artifact: ExportArtifact) -> None:
    if artifact.version.schema_version != EXPORT_SCHEMA_VERSION:
        raise InstitutionalExportValidationError(
            f"unsupported schema_version {artifact.version.schema_version!r}"
        )
    fmt = validate_export_format(artifact.metadata.format)
    if artifact.metadata.format != fmt:
        raise InstitutionalExportValidationError("metadata.format mismatch")
    if not artifact.metadata.export_id.strip():
        raise InstitutionalExportValidationError("missing export_id")
    if not artifact.metadata.report_id.strip():
        raise InstitutionalExportValidationError("missing report_id")
    if not artifact.metadata.exported_at:
        raise InstitutionalExportValidationError("missing exported_at")
    if not artifact.content_base64:
        raise InstitutionalExportValidationError("missing content_base64")
    if not artifact.content_sha256:
        raise InstitutionalExportValidationError("missing content_sha256")
    if artifact.metadata.byte_length < 0:
        raise InstitutionalExportValidationError("invalid byte_length")
    if fmt == "json" and artifact.structured_json is None:
        raise InstitutionalExportValidationError("json export missing structured_json")
