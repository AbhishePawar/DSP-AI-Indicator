"""Trusted issuer-specific source registry.

Issuer domains are reviewed server-side, never authorized by
AI output or client-supplied metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class IssuerIdentity:

    ticker: str
    exchange: str
    isin: str
    company_name: str
    approved_hosts: frozenset[str]
    identity_reference: str


_ISSUERS = MappingProxyType({
    ("NSE", "INFY"): IssuerIdentity(
        ticker="INFY",
        exchange="NSE",
        isin="INE009A01021",
        company_name="Infosys Limited",
        approved_hosts=frozenset({
            "infosys.com",
            "www.infosys.com",
        }),
        identity_reference=(
            "https://www.infosys.com/investors/"
            "shareholder-services/faqs.html"
        ),
    ),
})


def resolve_issuer(
    ticker: str,
    exchange: str,
) -> IssuerIdentity | None:

    return _ISSUERS.get((
        str(exchange or "").strip().upper(),
        str(ticker or "").strip().upper(),
    ))


def issuer_url_is_approved(
    *,
    ticker: str,
    exchange: str,
    isin: str,
    url: str,
) -> bool:

    issuer = resolve_issuer(ticker, exchange)

    if issuer is None:
        return False

    if issuer.isin != str(isin or "").strip().upper():
        return False

    if not isinstance(url, str):
        return False

    if any(
        ord(character) < 32 or ord(character) == 127
        for character in url
    ):
        return False

    try:

        parsed = urlsplit(url)

        return (
            parsed.scheme == "https"
            and parsed.hostname in issuer.approved_hosts
            and parsed.username is None
            and parsed.password is None
            and parsed.port in (None, 443)
            and parsed.path.startswith("/investors/")
        )

    except ValueError:

        return False
