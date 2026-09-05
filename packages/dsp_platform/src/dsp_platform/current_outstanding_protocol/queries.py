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
    *,
    issuer_official_host: str = "",
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
    for extra in _identity_anchor_queries(
        name=name,
        symbol=symbol,
        exchange=exchange,
        isin=isin,
        mic=mic,
        issuer_official_host=issuer_official_host,
    ):
        key = extra.casefold()
        if key in seen:
            continue
        seen.add(key)
        queries.append(extra)
    return tuple(queries)


def _identity_anchor_queries(
    *,
    name: str,
    symbol: str,
    exchange: str,
    isin: str,
    mic: str,
    issuer_official_host: str = "",
) -> tuple[str, ...]:
    """Quoted identity and official-domain locators. Not evidence."""
    extras: list[str] = []
    if name and isin:
        extras.append(f'"{name}" "{isin}" shares outstanding')
    if symbol and isin:
        extras.append(f'"{symbol}" "{isin}" shares outstanding')
        extras.append(f'"{symbol}" "{isin}" "shares outstanding"')
    if name and exchange:
        extras.append(f'"{name}" {exchange} shares outstanding')
    if symbol and exchange and mic:
        extras.append(f'"{symbol}" {exchange} {mic} shares outstanding')
    if symbol and exchange:
        extras.append(f'"{symbol}" {exchange} corporate action equity shares')
    if name:
        extras.append(f'"{name}" shares outstanding bonus split buyback')
    nse_like = exchange.upper() == "NSE" or mic.upper() == "XNSE"
    if nse_like and name:
        extras.append(f'site:nseindia.com "{name}" shares')
        extras.append(f'site:bseindia.com "{name}" shares')
        extras.append(f'site:sebi.gov.in "{name}" shares outstanding')
    if nse_like and symbol:
        extras.append(f'site:nseindia.com "{symbol}" shares outstanding')
    site_query = _issuer_site_query(issuer_official_host, name=name, symbol=symbol)
    if site_query is not None:
        extras.append(site_query)
    return tuple(extras)


def _issuer_site_query(host: str, *, name: str, symbol: str) -> str | None:
    """Restrict a search to a caller-supplied official host. No ticker map."""
    cleaned = str(host or "").strip().lower()
    cleaned = cleaned.removeprefix("https://").removeprefix("http://")
    cleaned = cleaned.split("/", 1)[0]
    if not cleaned or " " in cleaned or ".." in cleaned:
        return None
    if not all(char.isalnum() or char in ".-" for char in cleaned):
        return None
    label = name or symbol
    if not label:
        return None
    return f'site:{cleaned} "{label}" "shares outstanding"'
