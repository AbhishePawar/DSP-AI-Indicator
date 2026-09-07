"""Resolve listed-equity identity without ticker-specific branches."""

from __future__ import annotations

from dsp_platform.share_count_refresh import InstrumentIdentity
from dsp_platform.share_research.models import ShareResearchRequest

__all__ = ["EXCHANGE_TO_MIC", "equivalent_mics", "resolve_research_identity"]

EXCHANGE_TO_MIC = {
    "NSE": "XNSE",
    "BSE": "XBOM",
    "NYSE": "XNYS",
    "NASDAQ": "XNAS",
}
_EQUIVALENT = (frozenset({"XNSE", "XBOM"}),)


def equivalent_mics(left: str, right: str) -> bool:
    a = left.strip().upper()
    b = right.strip().upper()
    if not a or not b:
        return False
    if a == b:
        return True
    return any({a, b} <= group for group in _EQUIVALENT)


def resolve_research_identity(
    request: ShareResearchRequest,
) -> InstrumentIdentity | None:
    ticker = str(request.ticker or "").strip().upper()
    if not ticker:
        return None
    exchange = str(request.exchange or "").strip().upper()
    isin = str(request.isin or "").strip().upper()
    mic = str(request.mic or "").strip().upper() or EXCHANGE_TO_MIC.get(exchange, "")
    company = str(request.company or "").strip()
    catalog = _catalog_match(ticker, exchange, isin, mic)
    if catalog is not None:
        return catalog
    if not isin or not mic:
        return None
    return InstrumentIdentity(
        symbol=ticker,
        exchange=exchange,
        mic=mic,
        isin=isin,
        issuer=company,
        security_type="common_equity",
    ).normalized()


def _catalog_match(
    ticker: str, exchange: str, isin: str, mic: str
) -> InstrumentIdentity | None:
    try:
        from dsp_platform.share_count_acquisition.universe import iter_listed_equities
    except Exception:  # noqa: BLE001
        return None
    matches: list[InstrumentIdentity] = []
    for row in iter_listed_equities():
        ident = row.identity.normalized()
        if ident.symbol != ticker:
            continue
        if isin and ident.isin != isin:
            continue
        if mic and not equivalent_mics(ident.mic, mic) and ident.mic != mic:
            continue
        if exchange and ident.exchange != exchange and not equivalent_mics(
            ident.mic, EXCHANGE_TO_MIC.get(exchange, "")
        ):
            continue
        matches.append(ident)
    if len(matches) == 1:
        return matches[0]
    return None
