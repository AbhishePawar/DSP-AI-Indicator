"""Listed-equity identity catalog for acquisition. Lookup is ISIN + MIC.

Catalog rows live in listed_equity_universe.json (data, not ticker branches).
Unknown identities fail closed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dsp_platform.share_count_refresh import InstrumentIdentity

__all__ = [
    "ListedEquityInstrument",
    "get_listed_equity",
    "iter_listed_equities",
]

_CATALOG_PATH = Path(__file__).with_name("listed_equity_universe.json")


@dataclass(frozen=True, slots=True)
class ListedEquityInstrument:
    identity: InstrumentIdentity
    bse_scrip: str
    ir_urls: tuple[str, ...]
    ir_hosts: frozenset[str]
    predecessor_isins: tuple[str, ...]


def _hosts_from_urls(urls: tuple[str, ...]) -> frozenset[str]:
    hosts: set[str] = set()
    for url in urls:
        rest = str(url).split("://", 1)[-1]
        host = rest.split("/", 1)[0].strip().lower()
        if not host:
            continue
        hosts.add(host)
        if host.startswith("www."):
            hosts.add(host[4:])
        else:
            hosts.add(f"www.{host}")
    return frozenset(hosts)


@lru_cache(maxsize=1)
def _catalog() -> tuple[ListedEquityInstrument, ...]:
    raw = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    rows: list[ListedEquityInstrument] = []
    for item in raw.get("instruments") or []:
        if not isinstance(item, dict):
            continue
        identity = InstrumentIdentity(
            symbol=str(item.get("symbol") or ""),
            exchange=str(item.get("exchange") or ""),
            mic=str(item.get("mic") or ""),
            isin=str(item.get("isin") or ""),
            issuer=str(item.get("issuer") or ""),
        ).normalized()
        if not identity.isin or not identity.mic:
            continue
        urls = tuple(str(url) for url in (item.get("ir_urls") or ()) if str(url).strip())
        rows.append(
            ListedEquityInstrument(
                identity=identity,
                bse_scrip=str(item.get("bse_scrip") or "").strip(),
                ir_urls=urls,
                ir_hosts=_hosts_from_urls(urls),
                predecessor_isins=tuple(
                    str(value).strip().upper()
                    for value in (item.get("predecessor_isins") or ())
                    if str(value).strip()
                ),
            )
        )
    return tuple(rows)


def get_listed_equity(isin: str, mic: str) -> ListedEquityInstrument | None:
    wanted_isin = str(isin or "").strip().upper()
    wanted_mic = str(mic or "").strip().upper()
    for row in _catalog():
        if row.identity.isin == wanted_isin and row.identity.mic == wanted_mic:
            return row
    return None


def iter_listed_equities() -> tuple[ListedEquityInstrument, ...]:
    return _catalog()
