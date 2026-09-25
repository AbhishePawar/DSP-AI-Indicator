"""WIPRO page-level reconstruction + post-buyback PA share forensic. Not evidence."""

from __future__ import annotations

import json
import logging
import re
from io import BytesIO
from pathlib import Path

logging.getLogger("fontTools").setLevel(logging.ERROR)
logging.getLogger("pypdf").setLevel(logging.ERROR)

from pypdf import PdfReader

from data_engine.official_research.documents import retrieve_official_document, DocumentStore
from data_engine.official_research.extraction import extract_shares_outstanding, extract_labeled_field
from data_engine.official_research.nse_eod import NsePublicHttp
from data_engine.official_research.statement_tables import (
    reconstruct_statement_pages,
    spans_from_pdf,
    extract_field_from_statements,
)

AR_URL = (
    "https://nsearchives.nseindia.com/annual_reports/"
    "AR_29427_WIPRO_2025_2026_A_8877705_22062026190140.pdf"
)
PA_URL = (
    "https://nsearchives.nseindia.com/corporate/"
    "Cslogin_26062026181043_SEIntimationPostBuybackPA.pdf"
)
PAGES = (298, 326, 327, 348, 349, 360)
OUT = Path("artifacts/simple14nc_wipro_probe.json")
PDF_DIR = Path("artifacts/simple14nc_pdfs")


def _save(name: str, payload: bytes) -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    (PDF_DIR / name).write_bytes(payload)


def main() -> None:
    transport = NsePublicHttp()
    store = DocumentStore()
    ar = retrieve_official_document(
        AR_URL, transport=transport, isin="INE075A01022", mic="XNSE",
        source_type="regulator", store=store,
    )
    if hasattr(ar, "reason"):
        OUT.write_text(json.dumps({"ar_fail": ar.reason}), encoding="utf-8")
        return
    _save("WIPRO_AR.pdf", ar.payload)
    reader = PdfReader(BytesIO(ar.payload))
    page_texts = []
    for i, page in enumerate(reader.pages, start=1):
        if i in PAGES:
            page_texts.append(page.extract_text() or "")
        else:
            page_texts.append("")
    # reconstruct only selected pages by providing sparse page_texts with headings
    rebuilt = reconstruct_statement_pages(ar.payload, page_texts=tuple(page_texts))
    fields = {}
    for name in (
        "revenue", "net_income", "ebit", "operating_profit", "equity",
        "cash", "cfo", "capex", "debt", "total_assets", "total_liabilities",
    ):
        item = extract_field_from_statements(rebuilt, name)
        if item is None:
            fields[name] = None
            continue
        fields[name] = {
            "status": item.semantic_status,
            "value": item.value,
            "raw": item.raw_value,
            "unit": item.raw_unit,
            "locator": item.locator,
            "period": None if item.period_end is None else item.period_end.isoformat(),
            "basis": item.statement_basis,
        }
    pages_out = []
    for page in rebuilt:
        pages_out.append(
            {
                "page": page.page,
                "kind": page.statement_type,
                "name": page.statement_name,
                "basis": page.basis,
                "unit": page.unit_scale,
                "columns": [
                    {"x": c.x, "end": c.period_end.isoformat(), "label": c.label[:80]}
                    for c in page.columns
                ],
                "row_count": len(page.rows),
                "unique_rows": [
                    {
                        "label": r.label[:120],
                        "current": r.current_raw,
                        "prior": r.prior_raw,
                        "pairing": r.pairing,
                    }
                    for r in page.rows
                    if r.pairing == "UNIQUE" and r.current_raw
                ][:20],
            }
        )
    span_diag = {}
    selected_spans = spans_from_pdf(ar.payload, page_numbers=PAGES)
    for index, spans in enumerate(selected_spans, start=1):
        if index not in PAGES:
            continue
        dates = [s for s in spans if re.search(r"20(25|26)|March|March 31", s.text, re.I)]
        span_diag[str(index)] = {
            "span_count": len(spans),
            "date_like": [
                {"t": s.text[:80], "x": round(s.x, 1), "y": round(s.y, 1)}
                for s in dates[:18]
            ],
        }
    pa = retrieve_official_document(
        PA_URL, transport=transport, isin="INE075A01022", mic="XNSE",
        source_type="regulator", store=store,
    )
    pa_out = {"url": PA_URL}
    if hasattr(pa, "reason"):
        pa_out["fail"] = pa.reason
    else:
        _save("WIPRO_post_buyback_pa.pdf", pa.payload)
        from data_engine.official_research.pdf_text import document_text_from_payload
        text = document_text_from_payload(pa.payload) or ""
        pa_out.update(
            {
                "hash": pa.document_hash,
                "size": pa.content_length,
                "chars": len(text),
                "shares_field": None
                if extract_shares_outstanding(text) is None
                else {
                    "value": extract_shares_outstanding(text).value,
                    "as_of": None
                    if extract_shares_outstanding(text).as_of is None
                    else extract_shares_outstanding(text).as_of.isoformat(),
                    "locator": extract_shares_outstanding(text).locator,
                },
            }
        )
        hits = []
        for m in re.finditer(
            r".{0,80}(share[s]? (outstanding|outstanding as|capital)|equity shares|"
            r"paid[- ]up|extinguish|post[- ]buyback|resulting).{0,80}",
            text,
            re.I,
        ):
            hits.append(m.group(0).replace("\n", " ")[:200])
            if len(hits) >= 25:
                break
        pa_out["hits"] = hits
        nums = re.findall(r"\b\d{1,3}(?:,\d{2,3})+\b|\b\d{8,12}\b", text)
        pa_out["large_numbers"] = nums[:40]
    OUT.write_text(
        json.dumps(
            {
                "ar_hash": ar.document_hash,
                "ar_size": ar.content_length,
                "pages": pages_out,
                "fields": fields,
                "span_diag": span_diag,
                "post_buyback": pa_out,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("wrote", OUT, "pages", len(pages_out), "fields", {k: v and v.get("status") for k, v in fields.items()})


if __name__ == "__main__":
    main()
