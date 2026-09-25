"""LIVE shareholding + CA discovery for 14N-D. Authoritative NSE only."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from data_engine.official_research.models import utc_now
from data_engine.official_research.nse_eod import NsePublicHttp
from data_engine.official_research.nse_primary import (
    NSE_ANNOUNCEMENTS_URL,
    NSE_SHAREHOLDING_URL,
    parse_announcement_capital_events,
    parse_announcement_documents,
    parse_shareholding_shares,
)

TICKERS = ("WIPRO", "HDFCBANK", "TCS", "INFY")
OUT = Path("artifacts/simple14nd_shares.json")
HORIZON = date(2026, 9, 11)


def main() -> None:
    transport = NsePublicHttp()
    rows = {}
    for ticker in TICKERS:
        hold_url = f"{NSE_SHAREHOLDING_URL}?index=equities&symbol={ticker}"
        try:
            hold_payload = json.loads(
                transport.get_bytes(hold_url, referer="https://www.nseindia.com/all-reports")
            )
            hold = parse_shareholding_shares(hold_payload, ticker=ticker)
        except LookupError as exc:
            hold = None
            hold_error = str(exc)
        else:
            hold_error = None
        ann_url = f"{NSE_ANNOUNCEMENTS_URL}?index=equities&symbol={ticker}"
        try:
            ann_payload = json.loads(
                transport.get_bytes(ann_url, referer="https://www.nseindia.com/all-reports")
            )
            events = parse_announcement_capital_events(ann_payload)
            docs = [
                {
                    "title": d.title,
                    "url": d.url,
                    "as_of": None if d.as_of is None else d.as_of.isoformat(),
                    "kind": d.kind,
                }
                for d in parse_announcement_documents(ann_payload)
                if any(
                    token in (d.title or "").lower()
                    for token in (
                        "buyback",
                        "extinguish",
                        "share capital",
                        "paid-up",
                        "paid up",
                        "allotment",
                        "esop",
                        "bonus",
                        "split",
                    )
                )
            ]
        except LookupError as exc:
            events = ()
            docs = [{"error": str(exc)}]
        later = [
            {
                "type": e.event_type,
                "date": e.event_date.isoformat(),
                "url": e.source_url,
            }
            for e in events
            if e.event_date.year >= 2025
        ]
        hold_dump = None if hold is None else {
            "value": hold.value,
            "as_of": None if hold.as_of is None else hold.as_of.isoformat(),
            "locator": hold.locator,
            "status": hold.semantic_status,
        }
        current = None
        if hold is not None and hold.as_of is not None:
            current = is_current(
                as_of=hold.as_of,
                current_through=hold.as_of,
                retrieved_at=utc_now(),
                corporate_actions=tuple(
                    CapitalEvent(e.event_type, e.event_date)
                    for e in events
                    if e.event_date > hold.as_of
                ),
                valuation_date=HORIZON,
            )
            hold_dump["is_current"] = current
        rows[ticker] = {
            "shareholding": hold_dump,
            "hold_error": hold_error,
            "ca_2025plus": later,
            "share_docs": docs[:15],
            "horizon": HORIZON.isoformat(),
        }
        print(ticker, hold_dump, "later", later[:8], flush=True)
    OUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
