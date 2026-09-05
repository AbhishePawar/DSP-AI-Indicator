"""DSP-owned current-outstanding web-research queries.

These strings are search tasks for an untrusted researcher. They are not
evidence, not HTTP, and not ShareCount authority.
"""

from __future__ import annotations

from dsp_platform.external_evidence.models import ExternalEvidenceIdentity

__all__ = ["share_count_web_research_queries"]

_TEMPLATES = (
    "{q} shares outstanding",
    "{q} outstanding shares",
    "{q} current shares outstanding",
    "{q} annual report shares outstanding",
    "{q} filing shares outstanding",
    "{q} Screener shares outstanding",
)


def share_count_web_research_queries(
    identity: ExternalEvidenceIdentity,
) -> tuple[str, ...]:
    """Deterministic query list. Does not perform a network search."""
    if not isinstance(identity, ExternalEvidenceIdentity):
        return ()
    seeds: list[str] = []
    name = str(identity.company_name or "").strip()
    symbol = str(identity.symbol or "").strip()
    exchange = str(identity.exchange or "").strip()
    isin = str(identity.isin or "").strip()
    mic = str(identity.mic or "").strip()
    if name:
        seeds.append(name)
    if symbol and symbol not in seeds:
        seeds.append(symbol)
    if exchange and exchange not in seeds:
        seeds.append(exchange)
    if isin and isin not in seeds:
        seeds.append(isin)
    if mic and mic not in seeds:
        seeds.append(mic)
    compound: list[str] = []
    if name and exchange:
        compound.append(f"{name} {exchange}")
    if symbol and exchange:
        compound.append(f"{symbol} {exchange}")
    if name and isin:
        compound.append(f"{name} {isin}")
    if symbol and isin:
        compound.append(f"{symbol} {isin}")
    if name and mic:
        compound.append(f"{name} {mic}")
    for item in compound:
        if item not in seeds:
            seeds.append(item)
    seen: set[str] = set()
    queries: list[str] = []
    for seed in seeds:
        for template in _TEMPLATES:
            query = template.format(q=seed)
            key = query.casefold()
            if key in seen:
                continue
            seen.add(key)
            queries.append(query)
    return tuple(queries)
