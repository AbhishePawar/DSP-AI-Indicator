"""CSV summary export of Institutional Report (EPIC-R003)."""

from __future__ import annotations

import csv
import io

from dsp_platform.institutional_export.mapper import flatten_report
from dsp_platform.institutional_report.models import InstitutionalResearchReport

__all__ = ["export_csv_bytes"]

_COLUMNS = (
    "section",
    "rs_id",
    "field",
    "value",
    "available",
    "status",
    "source_section",
)


def export_csv_bytes(report: InstitutionalResearchReport) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in flatten_report(report):
        writer.writerow(
            {
                "section": row.section,
                "rs_id": row.rs_id,
                "field": row.field,
                "value": row.value,
                "available": row.available,
                "status": row.status,
                "source_section": row.source_section,
            }
        )
    return buffer.getvalue().encode("utf-8")
