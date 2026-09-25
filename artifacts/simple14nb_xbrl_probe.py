"""Follow-up 14N-B probe: NSE annual-reports + XBRL + dated CA + BSE payload."""

from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, build_opener, HTTPCookieProcessor
from http.cookiejar import CookieJar

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "data_engine" / "src"))

from data_engine.official_research.annual_report import (
    latest_completed_indian_fy,
    normalize_financial_year,
    select_annual_documents,
)
from data_engine.official_research.nse_eod import NSE_ALL_REPORTS, NsePublicHttp, parse_nse_calendar_date
from data_engine.official_research.nse_primary import (
    NSE_ANNOUNCEMENTS_URL,
    NSE_FINANCIAL_RESULTS_URL,
    parse_announcement_documents,
)
from data_engine.official_research.pdf_text import document_text_from_payload

NAMES = (
    ("INFY", "INE009A01021"),
    ("TCS", "INE467B01029"),
    ("WIPRO", "INE075A01022"),
    ("HDFCBANK", "INE040A01034"),
    ("RELIANCE", "INE002A01018"),
    ("ASIANPAINT", "INE021A01026"),
    ("HINDUNILVR", "INE030A01027"),
)

NSE_ANNUAL_REPORTS_URL = "https://www.nseindia.com/api/annual-reports"
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
FY = latest_completed_indian_fy()


def _json(transport: NsePublicHttp, url: str) -> object:
    payload = transport.get_bytes(url, referer=NSE_ALL_REPORTS)
    return json.loads(payload.decode("utf-8"))


def _fy_end(row: dict) -> int | None:
    blob = " ".join(
        str(row.get(k) or "")
        for k in ("financialYear", "fromDate", "toDate", "period", "relatingTo", "fromYr", "toYr")
    )
    return normalize_financial_year(blob)


def main() -> None:
    transport = NsePublicHttp()
    out = {"fy": FY, "names": []}
    for ticker, isin in NAMES:
        row = {"ticker": ticker, "isin": isin}
        symbol = quote(ticker, safe="")
        annual = _json(transport, f"{NSE_ANNUAL_REPORTS_URL}?index=equities&symbol={symbol}")
        docs = annual if isinstance(annual, list) else []
        fy_docs = []
        for item in docs:
            if not isinstance(item, dict):
                continue
            from_y = str(item.get("fromYr") or "")
            to_y = str(item.get("toYr") or "")
            fy_docs.append(
                {
                    "fromYr": from_y,
                    "toYr": to_y,
                    "companyName": item.get("companyName"),
                    "fileName": item.get("fileName"),
                    "wanted": from_y == str(FY - 1) and to_y == str(FY),
                }
            )
        row["annual_reports"] = fy_docs[:6]
        row["annual_fy_count"] = sum(1 for item in fy_docs if item["wanted"])

        results = _json(
            transport,
            f"{NSE_FINANCIAL_RESULTS_URL}?index=equities&symbol={symbol}&period=Annual",
        )
        fy_rows = []
        if isinstance(results, list):
            for item in results:
                if not isinstance(item, dict):
                    continue
                if _fy_end(item) != FY:
                    continue
                fy_rows.append(
                    {
                        "isin": item.get("isin"),
                        "audited": item.get("audited"),
                        "consolidated": item.get("consolidated"),
                        "period": item.get("period"),
                        "financialYear": item.get("financialYear"),
                        "fromDate": item.get("fromDate"),
                        "toDate": item.get("toDate"),
                        "xbrl": item.get("xbrl"),
                        "resultDetailedDataLink": item.get("resultDetailedDataLink"),
                    }
                )
        row["fy_result_rows"] = fy_rows

        anns = _json(transport, f"{NSE_ANNOUNCEMENTS_URL}?index=equities&symbol={symbol}")
        parsed = parse_announcement_documents(anns) if False else parse_announcement_documents(anns)
        ranked = select_annual_documents(parsed, financial_year=FY, limit=6)
        row["selected_from_announcements"] = [
            {"title": c.title, "kind": c.kind, "fy": c.financial_year, "score": c.score, "url": c.url}
            for c in ranked
        ]
        ca_hits = []
        if isinstance(anns, list):
            for item in anns:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("desc") or item.get("attchmntText") or "")
                lowered = title.lower()
                if not any(
                    token in lowered
                    for token in (
                        "buyback",
                        "buy-back",
                        "extinguish",
                        "bonus",
                        "split",
                        "rights issue",
                        "qip",
                    )
                ):
                    continue
                ca_hits.append(
                    {
                        "an_dt": item.get("an_dt"),
                        "desc": item.get("desc"),
                        "text": title[:180],
                    }
                )
                if len(ca_hits) >= 8:
                    break
        row["ca_announcements"] = ca_hits
        out["names"].append(row)
        print(ticker, "annual_fy", row["annual_fy_count"], "result_rows", len(fy_rows), "sel", [c.kind for c in ranked], flush=True)

    # Fetch first WIPRO/INFY FY XBRL sample (small) and one annual PDF HEAD-size via existing transport.
    infy = next(item for item in out["names"] if item["ticker"] == "INFY")
    xbrl_url = None
    for item in infy["fy_result_rows"]:
        if str(item.get("consolidated") or "").lower() == "consolidated" and item.get("xbrl"):
            xbrl_url = item["xbrl"]
            break
    if xbrl_url:
        started = time.perf_counter()
        payload = transport.get_bytes(xbrl_url)
        text = payload.decode("utf-8", errors="replace")
        out["infy_xbrl"] = {
            "url": xbrl_url,
            "bytes": len(payload),
            "seconds": round(time.perf_counter() - started, 3),
            "head": text[:2500],
            "has_unitRef": "unitRef" in text,
            "has_inr": "INR" in text or "inr" in text.lower(),
            "has_revenue": "RevenueFromOperations" in text or "RevenueFromOperation" in text,
        }
        print("INFY XBRL", out["infy_xbrl"]["bytes"], out["infy_xbrl"]["seconds"])

    wipro = next(item for item in out["names"] if item["ticker"] == "WIPRO")
    xbrl_url = None
    for item in wipro["fy_result_rows"]:
        if str(item.get("consolidated") or "").lower() == "consolidated" and item.get("xbrl"):
            xbrl_url = item["xbrl"]
            break
    if xbrl_url:
        started = time.perf_counter()
        payload = transport.get_bytes(xbrl_url)
        text = payload.decode("utf-8", errors="replace")
        out["wipro_xbrl"] = {
            "url": xbrl_url,
            "bytes": len(payload),
            "seconds": round(time.perf_counter() - started, 3),
            "head": text[:2500],
            "has_unitRef": "unitRef" in text,
            "has_shares": "NumberOfEquityShares" in text or "PaidUpValueOfEquityShares" in text,
        }
        print("WIPRO XBRL", out["wipro_xbrl"]["bytes"], out["wipro_xbrl"]["seconds"])

    dest = Path(__file__).with_name("simple14nb_xbrl.json")
    dest.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print("WROTE", dest)


if __name__ == "__main__":
    main()
