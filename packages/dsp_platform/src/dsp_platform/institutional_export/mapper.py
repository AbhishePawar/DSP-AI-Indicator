"""Read-only flatten of Institutional Report for export (EPIC-R003).

No calculations. Preserves values exactly (including \"Data unavailable.\").
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from dsp_platform.institutional_report.models import (
    REPORT_SECTION_ORDER,
    InstitutionalResearchReport,
    UNAVAILABLE_MESSAGE,
)
from dsp_platform.institutional_report.serde import institutional_report_from_dict

__all__ = [
    "ExportFlatRow",
    "flatten_report",
    "load_report",
    "report_document_dict",
    "section_lines",
]


@dataclass(frozen=True, slots=True)
class ExportFlatRow:
    section: str
    rs_id: str
    field: str
    value: str
    available: str
    status: str
    source_section: str


def load_report(
    report: InstitutionalResearchReport | Mapping[str, Any],
) -> InstitutionalResearchReport:
    if isinstance(report, InstitutionalResearchReport):
        return report
    if isinstance(report, Mapping):
        return institutional_report_from_dict(report)
    raise TypeError("report must be InstitutionalResearchReport or mapping")


def report_document_dict(report: InstitutionalResearchReport) -> dict[str, Any]:
    """Canonical public dict — same content as R002 serialization (no reformatting)."""
    return report.to_dict()


def _value_as_text(value: Any) -> str:
    if value is None:
        return UNAVAILABLE_MESSAGE
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        parts = [
            f"{k}={_value_as_text(value[k])}"
            for k in sorted(value.keys(), key=str)
        ]
        return "{" + ", ".join(parts) + "}"
    if isinstance(value, (list, tuple)):
        return "[" + "; ".join(_value_as_text(v) for v in value) + "]"
    return str(value)


def _walk_fields(
    section_name: str,
    rs_id: str | None,
    available: bool,
    status: str,
    source_section: str,
    payload: Mapping[str, Any] | None,
) -> list[ExportFlatRow]:
    rows: list[ExportFlatRow] = []
    rs = rs_id or ""
    avail = "true" if available else "false"
    if not available or payload is None:
        rows.append(
            ExportFlatRow(
                section=section_name,
                rs_id=rs,
                field="(section)",
                value=UNAVAILABLE_MESSAGE,
                available=avail,
                status=status,
                source_section=source_section,
            )
        )
        return rows

    fields = payload.get("fields")
    if isinstance(fields, Mapping) and fields:
        for key in sorted(fields.keys(), key=str):
            rows.append(
                ExportFlatRow(
                    section=section_name,
                    rs_id=rs,
                    field=str(key),
                    value=_value_as_text(fields[key]),
                    available=avail,
                    status=status,
                    source_section=source_section,
                )
            )
        return rows

    for key in sorted(payload.keys(), key=str):
        if key in {"source_payload", "source_status", "source_name"}:
            continue
        rows.append(
            ExportFlatRow(
                section=section_name,
                rs_id=rs,
                field=str(key),
                value=_value_as_text(payload[key]),
                available=avail,
                status=status,
                source_section=source_section,
            )
        )
    if not rows:
        rows.append(
            ExportFlatRow(
                section=section_name,
                rs_id=rs,
                field="(section)",
                value=UNAVAILABLE_MESSAGE,
                available=avail,
                status=status,
                source_section=source_section,
            )
        )
    return rows


def flatten_report(report: InstitutionalResearchReport) -> tuple[ExportFlatRow, ...]:
    """Deterministic flat rows in REPORT_SECTION_ORDER."""
    rows: list[ExportFlatRow] = []
    meta = report.metadata.to_dict()
    for key in sorted(meta.keys(), key=str):
        rows.append(
            ExportFlatRow(
                section="metadata",
                rs_id="",
                field=str(key),
                value=_value_as_text(meta[key]),
                available="true",
                status="ok",
                source_section="metadata",
            )
        )

    for name in REPORT_SECTION_ORDER:
        if name == "metadata":
            continue
        section = report.section(name)
        rows.extend(
            _walk_fields(
                section.name,
                section.rs_id,
                section.available,
                section.status,
                section.source_section,
                dict(section.payload) if section.payload is not None else None,
            )
        )
    return tuple(rows)


def section_lines(report: InstitutionalResearchReport) -> tuple[str, ...]:
    """Plain-text lines for PDF — values preserved, no research reformatting."""
    lines: list[str] = [
        "DSP Institutional Research Report",
        f"Report ID: {report.metadata.report_id}",
        f"Schema: {report.version.schema_version}",
        f"Generated At: {report.metadata.generated_at}",
        f"Ticker: {report.metadata.ticker or UNAVAILABLE_MESSAGE}",
        f"Research Mode: {report.metadata.research_mode}",
        "",
    ]
    for row in flatten_report(report):
        prefix = f"[{row.section}]"
        if row.rs_id:
            prefix = f"[{row.section}/{row.rs_id}]"
        lines.append(f"{prefix} {row.field}: {row.value}")
    return tuple(lines)
