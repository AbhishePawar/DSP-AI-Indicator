"""Approved primary hosts and the Gemini share-research master policy.

Search snippets are not evidence. Secondary aggregators cannot be final sources.
"""

from __future__ import annotations

from urllib.parse import urlparse

__all__ = [
    "APPROVED_PRIMARY_HOSTS",
    "PROHIBITED_FINAL_HOSTS",
    "SHARE_RESEARCH_MASTER_POLICY",
    "classify_source_url",
    "host_of",
]

APPROVED_PRIMARY_HOSTS = frozenset(
    {
        "nseindia.com",
        "www.nseindia.com",
        "nsearchives.nseindia.com",
        "bseindia.com",
        "www.bseindia.com",
        "api.bseindia.com",
        "sebi.gov.in",
        "www.sebi.gov.in",
        "mca.gov.in",
        "www.mca.gov.in",
        "sec.gov",
        "www.sec.gov",
        "www.sec.gov",
        "data.sec.gov",
        "nyse.com",
        "www.nyse.com",
        "nasdaq.com",
        "www.nasdaq.com",
        "listingcenter.nasdaq.com",
    }
)

PROHIBITED_FINAL_HOSTS = frozenset(
    {
        "wikipedia.org",
        "en.wikipedia.org",
        "screener.in",
        "www.screener.in",
        "moneycontrol.com",
        "www.moneycontrol.com",
        "yahoo.com",
        "finance.yahoo.com",
        "tradingview.com",
        "www.tradingview.com",
        "investing.com",
        "www.investing.com",
        "marketscreener.com",
        "www.marketscreener.com",
        "seekingalpha.com",
        "www.seekingalpha.com",
        "twitter.com",
        "x.com",
        "facebook.com",
        "reddit.com",
        "www.reddit.com",
        "medium.com",
        "blogspot.com",
        "substack.com",
    }
)

SHARE_RESEARCH_MASTER_POLICY = """DSP_SHARE_RESEARCH_PROMPT_v1

You are the DSP share-research engine. DSP stores evidence, validates
identity, dates, sources, corporate actions, and currentness. You research
and retrieve. You do not calculate valuation, intrinsic value, or scores.

A. Check the supplied DSP stored record first. If it is not proven current
through the requested research date, perform fresh authoritative research.
Never assume an old record is current merely because no change is obvious.

B. Approved final sources only:
1. Official stock exchanges (NSE, BSE, NYSE, NASDAQ, or the listing exchange).
2. The company's official IR, annual/quarterly reports, filings, share-capital
   disclosures, and official corporate announcements.
3. Official regulators (SEBI, MCA, SEC, or equivalent).
Search engines may discover primary documents. Search snippets are NOT evidence.

C. Prohibited as final evidence: Wikipedia, Screener, Moneycontrol, Yahoo,
TradingView, Investing.com, blogs, social media, analyst/broker estimates,
aggregators, news articles, another AI's answer, unverified databases.

D. Requested value is CURRENT OUTSTANDING EQUITY SHARES. Distinguish
authorized, issued, paid-up, listed, outstanding, free-float, promoter
holdings, and diluted shares. Never derive outstanding from market cap/price.

E. After the latest authoritative observation, investigate subsequent events:
bonus, split, rights, QIP, FPO, preferential issue, ESOP, warrant/convertible
conversion, new issuance, buyback, cancellation, capital reduction, merger,
demerger, scheme, share swap, acquisition involving shares.
Do not automatically classify an acquisition as share-changing. Determine
whether consideration is cash, shares, mixed, or unknown. Unknown and
potentially share-changing means currentness remains unresolved.

F. Never estimate, extrapolate, guess, or silently choose among conflicts.
Insufficient evidence → UNKNOWN. Old stored data → REFRESH_REQUIRED.
Conflicting primary sources → CONFLICT.

G. Return JSON only with keys:
STATUS, COMPANY, TICKER, ISIN, EXCHANGE, MIC, SECURITY_TYPE,
OUTSTANDING_SHARES, AS_OF, CURRENT_THROUGH, RESEARCHED_AT,
STORED_SHARE_COUNT, STORED_AS_OF, STORED_CURRENT_THROUGH,
STORED_LAST_VERIFIED_AT, STORED_SOURCE,
NEW_PRIMARY_SOURCE_1, NEW_PRIMARY_SOURCE_2,
CORPORATE_ACTION_CHECK, CORPORATE_ACTIONS_FOUND, SHARE_COUNT_EFFECT,
IDENTITY_CHECK, CROSS_CHECK, CONFIDENCE, STORED_RECORD_STATUS,
NEW_CANDIDATE, PROMOTION_RECOMMENDED, SOURCE_URLS, EVIDENCE,
UNRESOLVED_ISSUES, CA_COVERAGE_START, CA_COVERAGE_END,
CA_PAGINATION_EXHAUSTED, CA_SOURCE_URL.

CORPORATE_ACTIONS_FOUND is an array of objects with
description, effective_date, consideration.
SOURCE_URLS is an array of HTTPS URLs.
OUTSTANDING_SHARES is an integer share count or null.
AS_OF and CURRENT_THROUGH are ISO dates or null.
"""


def host_of(url: str) -> str:
    host = (urlparse(str(url or "").strip()).hostname or "").strip().lower()
    if host.startswith("www."):
        return host
    return host


def classify_source_url(
    url: str, *, extra_issuer_hosts: frozenset[str] = frozenset()
) -> tuple[bool, str]:
    """Return (accepted_as_final, reason)."""
    text = str(url or "").strip()
    if not text.startswith("https://"):
        return False, "source URL must be HTTPS"
    host = host_of(text)
    if not host:
        return False, "source URL host is missing"
    bare = host[4:] if host.startswith("www.") else host
    prohibited = host in PROHIBITED_FINAL_HOSTS or bare in PROHIBITED_FINAL_HOSTS
    if prohibited or any(
        host.endswith("." + p) or host == p for p in PROHIBITED_FINAL_HOSTS
    ):
        return False, f"prohibited final evidence host: {host}"
    extra = {h.strip().lower() for h in extra_issuer_hosts if h}
    extra |= {("www." + h) if not h.startswith("www.") else h[4:] for h in extra}
    if host in APPROVED_PRIMARY_HOSTS or bare in APPROVED_PRIMARY_HOSTS:
        return True, "approved primary host"
    if host in extra or bare in extra:
        return True, "issuer official host"
    return False, f"host is not an approved primary source: {host}"
