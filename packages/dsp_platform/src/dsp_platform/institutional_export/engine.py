"""Institutional Export Engine (EPIC-R003).

Exports Institutional Report (R002) only — no calculations or reformatting.
"""

from __future__ import annotations

import base64
import hashlib
import uuid
from typing import Any, Mapping

from dsp_platform.institutional_export.formats import (
    export_csv_bytes,
    export_docx_bytes,
    export_json_bytes,
    export_json_document,
    export_pdf_bytes,
    export_pptx_bytes,
    export_xlsx_bytes,
)
from dsp_platform.institutional_export.mapper import load_report
from dsp_platform.institutional_export.models import (
    EXPORT_SCHEMA_VERSION,
    EXPORTER_VERSION,
    ExportArtifact,
    ExportMetadata,
    ExportVersion,
    freeze_mapping,
    utc_now,
)
from dsp_platform.institutional_export.validation import (
    validate_export_artifact,
    validate_export_format,
)
from dsp_platform.institutional_report.models import InstitutionalResearchReport

__all__ = [
    "CONTENT_TYPES",
    "EXPORTER_VERSION",
    "InstitutionalExportEngine",
    "export_institutional_report",
]

CONTENT_TYPES = {
    "json": "application/json; charset=utf-8",
    "csv": "text/csv; charset=utf-8",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

_EXTENSIONS = {
    "json": "json",
    "csv": "csv",
    "xlsx": "xlsx",
    "pdf": "pdf",
    "docx": "docx",
    "pptx": "pptx",
}


class InstitutionalExportEngine:
    """Fluent export engine — Institutional Report is the sole source."""

    def __init__(self) -> None:
        self._report: InstitutionalResearchReport | None = None
        self._format: str = "json"
        self._export_id: str | None = None
        self._exported_at: str | None = None

    def with_report(
        self, report: InstitutionalResearchReport | Mapping[str, Any]
    ) -> InstitutionalExportEngine:
        self._report = load_report(report)
        return self

    def with_format(self, fmt: str) -> InstitutionalExportEngine:
        self._format = validate_export_format(fmt)
        return self

    def with_export_id(self, export_id: str) -> InstitutionalExportEngine:
        self._export_id = export_id
        return self

    def with_exported_at(self, exported_at: str) -> InstitutionalExportEngine:
        self._exported_at = exported_at
        return self

    def export(self) -> ExportArtifact:
        if self._report is None:
            raise ValueError("institutional report is required")

        fmt = validate_export_format(self._format)
        report = self._report
        exported_at = self._exported_at or utc_now().isoformat()
        export_id = self._export_id or str(uuid.uuid4())

        structured: dict[str, Any] | None = None
        content_text: str | None = None

        if fmt == "json":
            structured = export_json_document(report)
            raw = export_json_bytes(report)
            content_text = raw.decode("utf-8")
        elif fmt == "csv":
            raw = export_csv_bytes(report)
            content_text = raw.decode("utf-8")
        elif fmt == "xlsx":
            raw = export_xlsx_bytes(report)
        elif fmt == "pdf":
            raw = export_pdf_bytes(report)
        elif fmt == "docx":
            raw = export_docx_bytes(report)
        elif fmt == "pptx":
            raw = export_pptx_bytes(report)
        else:  # pragma: no cover
            raise ValueError(f"unsupported format {fmt}")

        digest = hashlib.sha256(raw).hexdigest()
        b64 = base64.b64encode(raw).decode("ascii")
        ticker = report.metadata.ticker or "report"
        safe_ticker = "".join(c for c in ticker if c.isalnum() or c in "-_") or "report"
        filename = f"{safe_ticker}_institutional_report_{report.metadata.report_id}.{_EXTENSIONS[fmt]}"

        provenance = {
            "source": "institutional_report",
            "report_id": report.metadata.report_id,
            "research_object_id": report.metadata.research_object_id,
            "report_schema_version": report.version.schema_version,
            "report_generated_at": report.metadata.generated_at,
            "exporter_version": EXPORTER_VERSION,
            "export_format": fmt,
        }

        metadata = ExportMetadata(
            export_id=export_id,
            format=fmt,
            schema_version=EXPORT_SCHEMA_VERSION,
            exporter_version=EXPORTER_VERSION,
            report_id=report.metadata.report_id,
            report_schema_version=report.version.schema_version,
            research_object_id=report.metadata.research_object_id,
            exported_at=exported_at,
            content_type=CONTENT_TYPES[fmt],
            filename=filename,
            byte_length=len(raw),
            research_mode=report.metadata.research_mode,
            correlation_id=report.metadata.correlation_id,
            ticker=report.metadata.ticker,
            provenance=freeze_mapping(provenance) or {},
        )

        version = ExportVersion(
            schema_version=EXPORT_SCHEMA_VERSION,
            exporter_version=EXPORTER_VERSION,
            report_schema_version=report.version.schema_version,
        )

        artifact = ExportArtifact(
            metadata=metadata,
            version=version,
            content_base64=b64,
            content_sha256=digest,
            content_text=content_text,
            structured_json=freeze_mapping(structured) if structured is not None else None,
        )
        validate_export_artifact(artifact)
        return artifact


def export_institutional_report(
    report: InstitutionalResearchReport | Mapping[str, Any],
    *,
    format: str = "json",
    export_id: str | None = None,
    exported_at: str | None = None,
) -> ExportArtifact:
    """Convenience entry — Institutional Report is the only input source."""
    engine = (
        InstitutionalExportEngine()
        .with_report(report)
        .with_format(format)
    )
    if export_id:
        engine = engine.with_export_id(export_id)
    if exported_at:
        engine = engine.with_exported_at(exported_at)
    return engine.export()
