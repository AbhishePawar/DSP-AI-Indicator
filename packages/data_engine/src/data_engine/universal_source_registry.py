"""Universal financial research source inventory.

Source registration is not authorization for automated retrieval,
financial evidence verification, or production valuation.
"""

from dataclasses import dataclass
from types import MappingProxyType
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class ResearchSource:

    source_id: str
    domains: tuple[str, ...]
    authority: str
    capabilities: frozenset[str]
    access: str

    # Explicit activation review required.
    enabled: bool = False


def source(
    source_id,
    domains,
    authority,
    capabilities,
    access="review_required",
):

    return ResearchSource(
        source_id=source_id,
        domains=tuple(domains.split()),
        authority=authority,
        capabilities=frozenset(capabilities.split()),
        access=access,
    )


_SOURCES = (

    # Indian financial and regulatory sources.

    source("NSE", "nseindia.com",
           "primary", "filings fundamentals corporate_actions prices history"),

    source("BSE", "bseindia.com",
           "primary", "filings fundamentals corporate_actions prices history"),

    source("SEBI", "sebi.gov.in",
           "primary", "regulation disclosures"),

    source("RBI", "rbi.org.in",
           "primary", "economics banking interest_rates currency"),

    source("MCA", "mca.gov.in",
           "primary", "company_identity filings"),

    source("AMFI", "amfiindia.com",
           "primary", "fund_nav fund_identity"),

    source("NSDL", "nsdl.co.in nsdl.com",
           "primary", "depository statistics"),

    source("CDSL", "cdslindia.com",
           "primary", "depository statistics"),

    source("CAMS", "camsonline.com camskra.com",
           "primary", "fund_services"),

    source("KFINTECH", "kfintech.com",
           "primary", "fund_services"),

    source("NSE_INDICES", "niftyindices.com",
           "primary", "index_data"),

    source("BSE_INDICES", "bseindices.com",
           "primary", "index_data"),

    source("CCIL", "ccilindia.com",
           "primary", "bonds money_market currency"),

    source("IBBI", "ibbi.gov.in",
           "primary", "insolvency regulation"),

    source("COMPANY_OFFICIAL", "",
           "issuer_specific", "filings fundamentals corporate_actions shares"),

    source("AMC_OFFICIAL", "",
           "issuer_specific", "fund_nav fund_portfolio fund_expenses"),

    # International sources.

    source("SEC_EDGAR", "sec.gov",
           "primary", "filings fundamentals shares",
           "public_fair_access"),

    source("SEC_COMPANY_FACTS", "data.sec.gov",
           "primary", "structured_fundamentals",
           "public_fair_access"),

    source("SEC_SUBMISSIONS", "data.sec.gov",
           "primary", "filing_discovery company_identity",
           "public_fair_access"),

    source("FRED", "stlouisfed.org",
           "primary", "economics interest_rates",
           "api_key_or_dataset"),

    source("WORLD_BANK", "worldbank.org",
           "primary", "economics development",
           "public_api"),

    source("IMF", "imf.org",
           "primary", "economics forecasts"),

    source("BIS", "bis.org",
           "primary", "banking economics credit"),

    source("OECD", "oecd.org",
           "primary", "economics statistics"),

    source("US_TREASURY", "treasury.gov",
           "primary", "interest_rates bonds fiscal_data"),

    source("FEDERAL_RESERVE", "federalreserve.gov",
           "primary", "economics interest_rates banking"),

    source("ECB", "ecb.europa.eu",
           "primary", "economics interest_rates currency"),

    source("BOE", "bankofengland.co.uk",
           "primary", "economics interest_rates"),

    source("ADB", "adb.org",
           "primary", "economics development"),

    # Independent financial sources.

    source("SCREENER", "screener.in",
           "secondary", "fundamentals ratios shares"),

    source("YAHOO_FINANCE", "finance.yahoo.com",
           "secondary", "fundamentals prices history"),

    source("MONEYCONTROL", "moneycontrol.com",
           "secondary", "fundamentals prices news"),

    source("TRENDLYNE", "trendlyne.com",
           "secondary", "fundamentals shares corporate_actions"),

    source("TICKERTAPE", "tickertape.in",
           "secondary", "fundamentals ratios"),

    source("STOCKEDGE", "stockedge.com",
           "secondary", "fundamentals market_statistics"),

    source("GOOGLE_FINANCE", "google.com",
           "secondary", "prices market_statistics"),

    source("TRADINGVIEW", "tradingview.com",
           "secondary", "prices history technicals"),

    source("INVESTING", "investing.com",
           "secondary", "prices economics news"),

    source("FMP", "financialmodelingprep.com",
           "secondary", "fundamentals prices history",
           "api_key"),

    source("ALPHA_VANTAGE", "alphavantage.co",
           "secondary", "prices history fundamentals",
           "api_key"),

    source("TWELVE_DATA", "twelvedata.com",
           "secondary", "prices history",
           "api_key"),

    source("MORNINGSTAR", "morningstar.com morningstar.in",
           "secondary", "fund_research fundamentals"),

    source("VALUE_RESEARCH", "valueresearchonline.com",
           "secondary", "fund_research fund_risk"),

    source("ET_MONEY", "etmoney.com",
           "secondary", "fund_research"),

    source("GROWW", "groww.in",
           "secondary", "fund_research fundamentals"),

    # Government and economic datasets.

    source("MOSPI", "mospi.gov.in",
           "primary", "economics gdp inflation"),

    source("DATA_GOV_INDIA", "data.gov.in",
           "primary", "government_datasets"),

    source("MINISTRY_FINANCE", "finmin.gov.in",
           "primary", "fiscal_data economic_policy"),

    source("ECONOMIC_SURVEY", "indiabudget.gov.in",
           "primary", "economics sector_research"),

    source("UNION_BUDGET", "indiabudget.gov.in",
           "primary", "fiscal_data budget"),

    source("DPIIT", "dpiit.gov.in",
           "primary", "industry investment statistics"),

    source("COMMERCE", "commerce.gov.in",
           "primary", "trade economics"),

    source("LABOUR_BUREAU", "labourbureau.gov.in",
           "primary", "employment wages inflation"),

    source("NITI_AAYOG", "niti.gov.in",
           "primary", "policy development"),

    source("PIB", "pib.gov.in",
           "primary", "government_announcements"),

    # Sector-specific intelligence.

    source("TRAI", "trai.gov.in",
           "primary", "telecom regulation"),

    source("CEA", "cea.nic.in",
           "primary", "electricity energy"),

    source("CERC", "cercind.gov.in",
           "primary", "electricity regulation"),

    source("PPAC", "ppac.gov.in",
           "primary", "petroleum energy"),

    source("PNGRB", "pngrb.gov.in",
           "primary", "gas energy regulation"),

    source("IRDAI", "irdai.gov.in",
           "primary", "insurance regulation"),

    source("PFRDA", "pfrda.org.in",
           "primary", "pension regulation"),

    source("NABARD", "nabard.org",
           "primary", "agriculture rural_credit"),

    source("ICRA", "icra.in",
           "primary", "credit_ratings"),

    source("CRISIL", "crisil.com",
           "primary", "credit_ratings"),

    source("CARE_RATINGS", "careratings.com",
           "primary", "credit_ratings"),

    source("INDIA_RATINGS", "indiaratings.co.in",
           "primary", "credit_ratings"),

    source("SIAM", "siam.in",
           "primary", "automobile industry_statistics"),

    # AI discovery is not financial authority.

    source("OPENAI_RESEARCH", "",
           "discovery_only", "source_discovery",
           "api_key"),

    source("GEMINI_RESEARCH", "",
           "discovery_only", "source_discovery",
           "api_key"),
)

if len({s.source_id for s in _SOURCES}) != len(_SOURCES):
    raise RuntimeError("Duplicate research source IDs")

SOURCE_REGISTRY = MappingProxyType({
    s.source_id: s for s in _SOURCES
})


def get_source(source_id):

    return SOURCE_REGISTRY.get(
        str(source_id).strip().upper()
    )


def sources_for_capability(capability):

    capability = str(capability).strip().lower()

    return tuple(
        item for item in SOURCE_REGISTRY.values()
        if capability in item.capabilities
    )


def source_matches_url(source_id, url):
    """Publisher identity candidate check only.

    This does not replace SSRF protection, access review,
    issuer identification or document-level validation.
    """

    item = get_source(source_id)

    if item is None or not isinstance(url, str):
        return False

    if any(ord(c) <= 32 or ord(c) == 127 for c in url):
        return False

    try:

        parsed = urlsplit(url)

        if (
            parsed.scheme != "https"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in (None, 443)
        ):
            return False

        host = (parsed.hostname or "").lower()

        return any(
            host == domain
            or host.endswith("." + domain)
            for domain in item.domains
        )

    except ValueError:

        return False
