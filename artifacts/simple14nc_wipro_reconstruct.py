"""Reconstruct WIPRO FY26 statements from the already-downloaded AR PDF."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from data_engine.official_research.statement_tables import (
    extract_field_from_statements,
    reconstruct_statement_pages,
)

PDF = Path("artifacts/simple14nc_pdfs/WIPRO_AR.pdf")
OUT = Path("artifacts/simple14nc_wipro_reconstruct.json")


def main() -> None:
    payload = PDF.read_bytes()
    reader = PdfReader(BytesIO(payload))
    page_texts = [""] * len(reader.pages)
    for index in range(180, 311):
        page_texts[index - 1] = reader.pages[index - 1].extract_text() or ""
    pages = reconstruct_statement_pages(payload, page_texts=tuple(page_texts))
    fields = {}
    for name in (
        "revenue",
        "net_income",
        "ebit",
        "operating_profit",
        "equity",
        "cash",
        "cfo",
        "capex",
        "debt",
        "total_assets",
        "total_liabilities",
    ):
        item = extract_field_from_statements(pages, name)
        fields[name] = None if item is None else {
            "status": item.semantic_status,
            "value": item.value,
            "raw": item.raw_value,
            "unit": item.raw_unit,
            "locator": item.locator,
            "period": None if item.period_end is None else item.period_end.isoformat(),
            "basis": item.statement_basis,
        }
    OUT.write_text(
        json.dumps(
            {
                "statement_pages": [
                    {
                        "page": p.page,
                        "kind": p.statement_type,
                        "name": p.statement_name,
                        "basis": p.basis,
                        "unit": p.unit_scale,
                        "columns": [
                            {
                                "x": round(c.x, 1),
                                "end": c.period_end.isoformat(),
                                "label": c.label,
                            }
                            for c in p.columns
                        ],
                        "unique": [
                            {
                                "label": r.label[:100],
                                "current": r.current_raw,
                                "prior": r.prior_raw,
                            }
                            for r in p.rows
                            if r.pairing == "UNIQUE" and r.current_raw
                        ][:25],
                    }
                    for p in pages
                ],
                "fields": fields,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        "pages",
        [(p.page, p.statement_type, p.unit_scale, len(p.columns)) for p in pages],
    )
    print("fields", {k: (v or {}).get("status") for k, v in fields.items()})
    print("locators", {k: (v or {}).get("locator") for k, v in fields.items() if v})


if __name__ == "__main__":
    main()
