"""Listed-equity identity catalog for share-count acquisition fixtures.

This five-row JSON is NOT the production Security Master and NOT the DSP
supported universe. TCS/INFY/RELIANCE/HDFCBANK/ICICIBANK are test fixtures
with IR URLs. Official listed-security identity lives in security_master.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

from dsp_platform.share_count_refresh import InstrumentIdentity

__all__ = [
    "ListedEquityInstrument",
    "PredecessorIsin",
    "get_listed_equity",
    "iter_listed_equities",
]

_CATALOG_PATH = Path(__file__).with_name("listed_equity_universe.json")


@dataclass(frozen=True, slots=True)
class PredecessorIsin:
    isin: str
    effective_from: date | None = None
    effective_until: date | None = None

    def active_on(self, on: date | None) -> bool:
        if on is None:
            return self.effective_until is None
        if self.effective_from is not None and on < self.effective_from:
            return False
        if self.effective_until is not None and on > self.effective_until:
            return False
        return True


@dataclass(frozen=True, slots=True)
class ListedEquityInstrument:
    identity: InstrumentIdentity
    bse_scrip: str
    ir_urls: tuple[str, ...]
    ir_hosts: frozenset[str]
    predecessor_isins: tuple[str, ...]
    predecessors: tuple[PredecessorIsin, ...] = ()

    def equivalent_isins(self, on: date | None = None) -> tuple[str, ...]:
        if self.predecessors:
            return tuple(row.isin for row in self.predecessors if row.active_on(on))
        if on is None:
            return self.predecessor_isins
        return self.predecessor_isins


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
        predecessors = _parse_predecessors(item.get("predecessor_isins"))
        rows.append(
            ListedEquityInstrument(
                identity=identity,
                bse_scrip=str(item.get("bse_scrip") or "").strip(),
                ir_urls=urls,
                ir_hosts=_hosts_from_urls(urls),
                predecessor_isins=tuple(row.isin for row in predecessors),
                predecessors=predecessors,
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


def _parse_date(raw: object) -> date | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _parse_predecessors(raw: object) -> tuple[PredecessorIsin, ...]:
    rows: list[PredecessorIsin] = []
    if not isinstance(raw, list):
        return ()
    for item in raw:
        if isinstance(item, str):
            isin = item.strip().upper()
            if isin:
                rows.append(PredecessorIsin(isin=isin))
            continue
        if not isinstance(item, dict):
            continue
        isin = str(item.get("isin") or "").strip().upper()
        if not isin:
            continue
        rows.append(
            PredecessorIsin(
                isin=isin,
                effective_from=_parse_date(item.get("effective_from")),
                effective_until=_parse_date(item.get("effective_until")),
            )
        )
    return tuple(rows)
