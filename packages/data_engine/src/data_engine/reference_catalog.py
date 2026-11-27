"""Reference-backed investment identity catalog.

Identity resolution is independent of live market-data access.
Unknown instruments never silently become equities.
"""

from __future__ import annotations

import csv
import gzip
import json
import math

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


def normalize(value) -> str:
    return " ".join(str(value or "").upper().split())


@dataclass(frozen=True, slots=True)
class ReferenceInstrument:
    instrument_id: str
    symbol: str
    name: str
    exchange: str
    category: str
    source: str
    isins: tuple[str, ...] = ()
    instrument_key: str = ""
    exchange_code: str = ""
    security_type: str = ""
    short_name: str = ""
    plan: str = ""
    option: str = ""
    nav: float | None = None
    nav_date: date | None = None


def read_master(path: Path) -> list:
    limit = 128 * 1024 * 1024

    with gzip.open(path, "rb") as f:
        raw = f.read(limit + 1)

    if len(raw) > limit:
        raise ValueError("Reference file exceeds size limit")

    data = json.loads(raw)

    if not isinstance(data, list) or not data:
        raise ValueError("Invalid reference master")

    return data


def listed_category(row: dict) -> str:
    """Preliminary classification, never valuation eligibility."""

    isin = normalize(row.get("isin"))
    series = normalize(row.get("instrument_type"))

    if isin.startswith("INF"):
        return "listed_fund_candidate"

    if (
        isin.startswith("INE")
        and isin[6:8] == "01"
    ):
        return "equity_candidate"

    return "listed_unclassified"


class ReferenceCatalog:

    def __init__(self, records):
        self.records = tuple(dict.fromkeys(records))
        self._index = defaultdict(list)

        for record in self.records:
            aliases = {
                record.instrument_id,
                record.symbol,
                record.name,
                record.short_name,
                record.instrument_key,
                record.exchange_code,
                *record.isins,
            }

            for alias in {
                normalize(a) for a in aliases if a
            }:
                self._index[alias].append(record)

    def resolve(
        self,
        query: str,
        exchange: str | None = None,
    ) -> tuple[ReferenceInstrument, ...]:

        matches = self._index.get(
            normalize(query), ()
        )

        if exchange:
            matches = [
                record for record in matches
                if record.exchange == normalize(exchange)
            ]

        return tuple(matches)

    @classmethod
    def from_directory(cls, directory):
        root = Path(directory)
        records = []

        for exchange in ("NSE", "BSE"):

            for row in read_master(
                root / f"{exchange}.json.gz"
            ):
                if not isinstance(row, dict):
                    raise ValueError("Invalid listed record")

                if row.get("segment") != exchange + "_EQ":
                    continue

                key = normalize(row.get("instrument_key"))
                isin = normalize(row.get("isin"))
                symbol = normalize(
                    row.get("trading_symbol")
                    or row.get("tradingsymbol")
                )

                if not key or not symbol:
                    raise ValueError(
                        "Missing listed instrument identity"
                    )

                if normalize(row.get("exchange")) != exchange:
                    raise ValueError("Exchange identity mismatch")

                if not key.startswith(exchange + "_EQ|"):
                    raise ValueError("Instrument key mismatch")

                if isin and key.split("|", 1)[1] != isin:
                    raise ValueError("Instrument ISIN mismatch")

                records.append(ReferenceInstrument(
                    instrument_id=key,
                    symbol=symbol,
                    name=str(row.get("name") or symbol),
                    exchange=exchange,
                    category=listed_category(row),
                    source="upstox_reference_master",
                    isins=(isin,) if isin else (),
                    instrument_key=key,
                    exchange_code=(
                        str(row.get("exchange_token") or "")
                        if exchange == "BSE" else ""
                    ),
                    security_type=str(
                        row.get("instrument_type") or ""
                    ),
                    short_name=str(
                        row.get("short_name") or ""
                    ),
                ))

        with (root / "NAVAll.txt").open(
            encoding="utf-8-sig", newline=""
        ) as file:

            for line in file:
                if line.startswith("Scheme Code;"):
                    header = line.strip().split(";")
                    break
            else:
                raise ValueError("AMFI header not found")

            required = {
                "Scheme Code", "Scheme Name", "Plan",
                "Option", "Net Asset Value", "Date",
            }

            if not required.issubset(header):
                raise ValueError("Invalid AMFI schema")

            seen = set()

            for row in csv.DictReader(
                file, fieldnames=header, delimiter=";"
            ):
                code = str(
                    row.get("Scheme Code") or ""
                ).strip()

                if not code.isdigit():
                    continue

                if code in seen:
                    raise ValueError(
                        f"Duplicate AMFI scheme code: {code}"
                    )

                seen.add(code)

                isins = tuple(dict.fromkeys(
                    normalize(row.get(field))
                    for field in (
                        "ISIN Div Payout/ ISIN Growth",
                        "ISIN Div Reinvestment",
                    )
                    if normalize(row.get(field))
                    not in ("", "-")
                ))

                try:
                    nav = float(row["Net Asset Value"])

                    if not math.isfinite(nav) or nav <= 0:
                        nav = None
                except (ValueError, TypeError):
                    nav = None

                try:
                    nav_date = datetime.strptime(
                        row["Date"], "%d-%b-%Y"
                    ).date()
                except (ValueError, TypeError):
                    nav_date = None

                records.append(ReferenceInstrument(
                    instrument_id="AMFI:" + code,
                    symbol=code,
                    name=str(row.get("Scheme Name") or ""),
                    exchange="AMFI",
                    category="fund",
                    source="amfi_nav_report",
                    isins=isins,
                    plan=str(row.get("Plan") or ""),
                    option=str(row.get("Option") or ""),
                    nav=nav,
                    nav_date=nav_date,
                ))

        return cls(records)
