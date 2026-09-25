"""Non-production probe: financial-results index + one XBRL download."""
from __future__ import annotations

import json
import time
from urllib.parse import quote

from data_engine.official_research.nse_eod import NSE_ALL_REPORTS, NsePublicHttp
from data_engine.official_research.nse_primary import (
    NSE_FINANCIAL_RESULTS_URL,
    parse_financial_result_documents,
)
from data_engine.official_research.xbrl import extract_xbrl_fields

def main() -> None:
    transport = NsePublicHttp(timeout_seconds=20.0)
    symbol = quote("INFY", safe="")
    url = f"{NSE_FINANCIAL_RESULTS_URL}?index=equities&symbol={symbol}&period=Annual"
    t0 = time.perf_counter()
    raw = transport.get_bytes(url, referer=NSE_ALL_REPORTS)
    print("index_bytes", len(raw), "s", round(time.perf_counter() - t0, 2))
    payload = json.loads(raw.decode("utf-8"))
    docs = parse_financial_result_documents(payload, ticker="INFY")
    print("xbrl_docs", len(docs))
    if docs:
        print("first", docs[0].url, docs[0].statement_basis, docs[0].as_of)
        t1 = time.perf_counter()
        blob = transport.get_bytes(docs[0].url, referer=NSE_ALL_REPORTS)
        print("xbrl_bytes", len(blob), "s", round(time.perf_counter() - t1, 2), "head", blob[:80])
        parsed = extract_xbrl_fields(blob, isin="INE009A01021")
        print("identity", parsed.identity_ok, "fields", sorted(parsed.fields), "issues", parsed.issues[:6])
        if parsed.fields:
            sample = parsed.fields.get("revenue") or next(iter(parsed.fields.values()))
            print("sample", sample.field, sample.value, sample.unit_scale, sample.statement_basis, sample.as_of)

if __name__ == "__main__":
    main()
