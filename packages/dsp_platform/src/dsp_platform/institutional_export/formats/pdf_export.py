"""Minimal PDF export (stdlib only, EPIC-R003) — text projection of report."""

from __future__ import annotations

from dsp_platform.institutional_export.mapper import section_lines
from dsp_platform.institutional_report.models import InstitutionalResearchReport

__all__ = ["export_pdf_bytes"]


def _pdf_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def export_pdf_bytes(report: InstitutionalResearchReport) -> bytes:
    """Build a simple single-page PDF of report lines.

    Values are written as-is from the Institutional Report (PDF string escaping
    only — no research content reformatting).
    """
    lines = list(section_lines(report))

    y_start = 780
    line_height = 11
    content_ops: list[str] = ["BT", "/F1 9 Tf", "50 780 Td"]
    first = True
    y = y_start
    for line in lines:
        if y < 40:
            break
        # PDF string escaping only — do not alter research values
        if not first:
            content_ops.append(f"0 -{line_height} Td")
        first = False
        content_ops.append(f"({_pdf_escape(line)}) Tj")
        y -= line_height
    content_ops.append("ET")
    stream = "\n".join(content_ops).encode("latin-1", errors="replace")

    objects: list[bytes] = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objects.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n"
    )
    objects.append(
        b"4 0 obj<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>stream\n"
        + stream
        + b"\nendstream\nendobj\n"
    )
    objects.append(
        b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n"
    )

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(out))
        out.extend(obj)

    xref_pos = len(out)
    out.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    out.extend(
        f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    return bytes(out)
