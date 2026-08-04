"""JSON export of Institutional Report (EPIC-R003) — content-preserving."""

from __future__ import annotations

import json
from typing import Any

from dsp_platform.institutional_export.mapper import report_document_dict
from dsp_platform.institutional_report.models import InstitutionalResearchReport

__all__ = ["export_json_bytes", "export_json_document"]


def export_json_document(report: InstitutionalResearchReport) -> dict[str, Any]:
    """Return the report public dict unchanged (deterministic key order via dumps)."""
    return report_document_dict(report)


def export_json_bytes(report: InstitutionalResearchReport) -> bytes:
    doc = export_json_document(report)
    text = json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    return text.encode("utf-8")
