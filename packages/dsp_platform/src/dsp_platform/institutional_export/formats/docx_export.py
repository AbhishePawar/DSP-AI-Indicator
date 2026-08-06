"""Minimal .docx export via Office Open XML (stdlib only, EPIC-R003).

Follows the same hand-rolled OOXML approach already used by
``excel_export.py`` for ``.xlsx`` — no third-party document library
dependency, deterministic output, values preserved exactly (including
"Data unavailable.").
"""

from __future__ import annotations

import zipfile
from io import BytesIO
from xml.sax.saxutils import escape

from dsp_platform.institutional_export.mapper import flatten_report
from dsp_platform.institutional_report.models import (
    REPORT_SECTION_ORDER,
    InstitutionalResearchReport,
    UNAVAILABLE_MESSAGE,
)

__all__ = ["export_docx_bytes"]

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    "</Types>"
)

_ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="word/document.xml"/>'
    "</Relationships>"
)


def _run(text: str, *, bold: bool = False) -> str:
    r_pr = "<w:rPr><w:b/></w:rPr>" if bold else ""
    return f'<w:r>{r_pr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def _paragraph(text: str, *, bold: bool = False, heading: bool = False) -> str:
    p_pr = "<w:pPr><w:spacing w:before=\"120\" w:after=\"60\"/></w:pPr>" if heading else ""
    return f"<w:p>{p_pr}{_run(text, bold=bold)}</w:p>"


def export_docx_bytes(report: InstitutionalResearchReport) -> bytes:
    """Build a minimal, valid .docx of the Institutional Report.

    One heading + paragraph list per report section, grouped in
    ``REPORT_SECTION_ORDER`` — values preserved as-is, no reformatting.
    """
    rows = flatten_report(report)
    by_section: dict[str, list[str]] = {}
    for row in rows:
        prefix = f"{row.section}/{row.rs_id}" if row.rs_id else row.section
        text = f"{row.field}: {row.value}" if row.field != "(section)" else row.value
        by_section.setdefault(prefix, []).append(text)

    body_parts: list[str] = [
        _paragraph("DSP Institutional Research Report", bold=True, heading=True),
        _paragraph(f"Report ID: {report.metadata.report_id}"),
        _paragraph(f"Schema: {report.version.schema_version}"),
        _paragraph(f"Generated At: {report.metadata.generated_at}"),
        _paragraph(f"Ticker: {report.metadata.ticker or UNAVAILABLE_MESSAGE}"),
        _paragraph(f"Research Mode: {report.metadata.research_mode}"),
    ]

    seen_sections: set[str] = set()
    for name in REPORT_SECTION_ORDER:
        if name == "metadata":
            continue
        for key in sorted(by_section.keys()):
            if key != name and not key.startswith(f"{name}/"):
                continue
            if key in seen_sections:
                continue
            seen_sections.add(key)
            body_parts.append(_paragraph(key, bold=True, heading=True))
            for line in by_section[key]:
                body_parts.append(_paragraph(line))

    body_parts.append(
        '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>'
    )

    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>" + "".join(body_parts) + "</w:body>"
        "</w:document>"
    )

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _ROOT_RELS)
        zf.writestr("word/document.xml", document_xml)
    return buffer.getvalue()
