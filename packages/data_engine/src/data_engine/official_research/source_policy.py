"""Approved-source whitelist. Secondary sources cannot become VERIFIED truth.

Screener is Tier-1C approved research: it may CROSS_CHECK a primary
value. It cannot itself become VERIFIED or be retrieved as truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

__all__ = [
    "APPROVED_RESEARCH_HOST_SUFFIXES",
    "AUTHORITY_TIERS",
    "FIELD_AUTHORITY_CHAIN",
    "FIELD_POLICY_MATRIX",
    "PRIMARY_HOST_SUFFIXES",
    "SECONDARY_HOST_SUFFIXES",
    "FieldPolicy",
    "SourceClass",
    "SourcePolicy",
    "authority_tier_for",
    "classify_source_url",
    "field_authority_chain",
    "field_policy",
    "record_source_clash",
    "source_authority_rank",
]

SourceClass = str  # primary | approved_research | secondary | forbidden | unknown

PRIMARY_HOST_SUFFIXES: tuple[str, ...] = (
    "nseindia.com",
    "nseindia.in",
    "nse.co.in",
    "nsearchives.nseindia.com",
    "archives.nseindia.com",
    "mcp.nseindia.in",
    "bseindia.com",
    "sebi.gov.in",
    "mca.gov.in",
    "rbi.org.in",
    "nsdl.co.in",
    "nsdl.com",
    "cdslindia.com",
)

APPROVED_RESEARCH_HOST_SUFFIXES: tuple[str, ...] = ("screener.in",)

# Company IR hosts are primary only when the caller marks source_type company_ir.
# Host allowlist here is exchange/regulator. Company sites are validated by
# source_type == "company_ir" plus an https URL, not a global crawl of the web.

SECONDARY_HOST_SUFFIXES: tuple[str, ...] = (
    "finance.yahoo.com",
    "yahoo.com",
    "ibef.org",
)

_FORBIDDEN_HINTS: tuple[str, ...] = (
    "yfinance",
    "financialmodelingprep.com",
    "fmpcloud.io",
    "eodhd.com",
    "upstox.com",
    "alphavantage.co",
)


def _host(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        return host[4:]
    return host


def _matches(host: str, suffixes: tuple[str, ...]) -> bool:
    return any(host == suffix or host.endswith("." + suffix) for suffix in suffixes)


def classify_source_url(
    url: str | None, *, source_type: str | None = None
) -> SourceClass:
    text = str(url or "").strip()
    if not text:
        return "unknown"
    lowered = text.lower()
    if any(hint in lowered for hint in _FORBIDDEN_HINTS):
        return "forbidden"
    host = _host(text)
    if not host:
        return "unknown"
    if _matches(host, PRIMARY_HOST_SUFFIXES):
        return "primary"
    if _matches(host, APPROVED_RESEARCH_HOST_SUFFIXES):
        return "approved_research"
    if _matches(host, SECONDARY_HOST_SUFFIXES):
        return "secondary"
    if source_type == "company_ir" and lowered.startswith("https://"):
        return "primary"
    return "unknown"


@dataclass(frozen=True, slots=True)
class SourcePolicy:
    """Enforces primary vs secondary promotion rules."""

    def classify(
        self, url: str | None, *, source_type: str | None = None
    ) -> SourceClass:
        return classify_source_url(url, source_type=source_type)

    def may_verify(self, url: str | None, *, source_type: str | None = None) -> bool:
        return self.classify(url, source_type=source_type) == "primary"

    def may_cross_check(
        self, url: str | None, *, source_type: str | None = None
    ) -> bool:
        return self.classify(url, source_type=source_type) == "approved_research"

    def is_discovery_only(
        self, url: str | None, *, source_type: str | None = None
    ) -> bool:
        return self.classify(url, source_type=source_type) == "secondary"


FIELD_AUTHORITY_CHAIN: dict[str, tuple[str, ...]] = {
    "price": (
        "nse_bse",
        "company",
        "screener",
        "yahoo_ibef",
        "ai",
    ),
    "financials": (
        "company_or_exchange_filing",
        "screener",
        "yahoo_ibef",
        "ai",
    ),
    "shares": (
        "nse_bse_regulator_company",
        "screener",
        "yahoo_ibef",
        "ai",
    ),
    "corporate_actions": (
        "nse_bse_regulator",
        "company",
        "screener",
        "yahoo_ibef",
        "ai",
    ),
}


def field_authority_chain(field: str) -> tuple[str, ...]:
    group = _FIELD_GROUP.get(field, "financials")
    if field in {"corporate_actions", "bonus", "split", "buyback"}:
        group = "corporate_actions"
    return FIELD_AUTHORITY_CHAIN[group]


_FIELD_GROUP = {
    "eod_close": "price",
    "last_price": "price",
    "price": "price",
    "revenue": "financials",
    "operating_profit": "financials",
    "ebit": "financials",
    "ebitda": "financials",
    "net_income": "financials",
    "equity": "financials",
    "cash": "financials",
    "cfo": "financials",
    "fcf": "financials",
    "capex": "financials",
    "debt": "financials",
    "total_assets": "financials",
    "total_liabilities": "financials",
    "shares_outstanding": "shares",
    "market_cap": "price",
    "enterprise_value": "price",
}

AUTHORITY_TIERS: tuple[str, ...] = (
    "TIER_1A",
    "TIER_1B",
    "TIER_1C",
    "TIER_2",
    "TIER_3",
    "UNKNOWN",
)

_AI_AGENTS = frozenset(
    {
        "gemini_find",
        "chatgpt_verify",
        "claude_review",
        "deep_search_attack",
        "openai_nse_mcp",
        "openai",
    }
)
_AI_SOURCE_TYPES = frozenset({"llm", "agent_claim"})
_SUPPORTED_EQUITY_TYPES = frozenset({"equity", "bank_equity", "ordinary_equity"})


@dataclass(frozen=True, slots=True)
class FieldPolicy:
    """Field-specific authority and verification requirements. Not a second policy engine."""

    field: str
    authority_chain: tuple[str, ...]
    freshness_class: str
    semantic_kinds: tuple[str, ...]
    as_of_required: bool
    period_required: bool
    unit_required: bool
    currency_required: bool
    statement_basis_required: bool
    corporate_action_required: bool
    calculation_dependency: tuple[str, ...]
    allowed_security_types: tuple[str, ...]
    derived: bool = False


def _financial_policy(field: str) -> FieldPolicy:
    return FieldPolicy(
        field=field,
        authority_chain=FIELD_AUTHORITY_CHAIN["financials"],
        freshness_class="latest_audited_period",
        semantic_kinds=("CONSOLIDATED", "STANDALONE"),
        as_of_required=True,
        period_required=True,
        unit_required=True,
        currency_required=True,
        statement_basis_required=True,
        corporate_action_required=False,
        calculation_dependency=(),
        allowed_security_types=tuple(sorted(_SUPPORTED_EQUITY_TYPES)),
    )


FIELD_POLICY_MATRIX: dict[str, FieldPolicy] = {
    "eod_close": FieldPolicy(
        field="eod_close",
        authority_chain=FIELD_AUTHORITY_CHAIN["price"],
        freshness_class="session_or_latest_eod",
        semantic_kinds=("EOD",),
        as_of_required=True,
        period_required=False,
        unit_required=False,
        currency_required=True,
        statement_basis_required=False,
        corporate_action_required=True,
        calculation_dependency=(),
        allowed_security_types=tuple(sorted(_SUPPORTED_EQUITY_TYPES)),
    ),
    "last_price": FieldPolicy(
        field="last_price",
        authority_chain=FIELD_AUTHORITY_CHAIN["price"],
        freshness_class="current_research_window",
        semantic_kinds=("CURRENT", "DELAYED"),
        as_of_required=True,
        period_required=False,
        unit_required=False,
        currency_required=True,
        statement_basis_required=False,
        corporate_action_required=True,
        calculation_dependency=(),
        allowed_security_types=tuple(sorted(_SUPPORTED_EQUITY_TYPES)),
    ),
    "price": FieldPolicy(
        field="price",
        authority_chain=FIELD_AUTHORITY_CHAIN["price"],
        freshness_class="session_or_latest_eod",
        semantic_kinds=("EOD", "CURRENT", "DELAYED"),
        as_of_required=True,
        period_required=False,
        unit_required=False,
        currency_required=True,
        statement_basis_required=False,
        corporate_action_required=True,
        calculation_dependency=(),
        allowed_security_types=tuple(sorted(_SUPPORTED_EQUITY_TYPES)),
    ),
    "revenue": _financial_policy("revenue"),
    "ebit": _financial_policy("ebit"),
    "ebitda": _financial_policy("ebitda"),
    "net_income": _financial_policy("net_income"),
    "cfo": _financial_policy("cfo"),
    "cash": _financial_policy("cash"),
    "debt": _financial_policy("debt"),
    "equity": _financial_policy("equity"),
    "operating_profit": _financial_policy("operating_profit"),
    "capex": _financial_policy("capex"),
    "fcf": FieldPolicy(
        field="fcf",
        authority_chain=FIELD_AUTHORITY_CHAIN["financials"],
        freshness_class="latest_audited_period",
        semantic_kinds=("CONSOLIDATED", "STANDALONE"),
        as_of_required=True,
        period_required=True,
        unit_required=True,
        currency_required=True,
        statement_basis_required=True,
        corporate_action_required=False,
        calculation_dependency=("cfo", "capex"),
        allowed_security_types=tuple(sorted(_SUPPORTED_EQUITY_TYPES)),
        derived=True,
    ),
    "shares_outstanding": FieldPolicy(
        field="shares_outstanding",
        authority_chain=FIELD_AUTHORITY_CHAIN["shares"],
        freshness_class="latest_count_plus_ca_review",
        semantic_kinds=("TOTAL_OUTSTANDING",),
        as_of_required=True,
        period_required=False,
        unit_required=False,
        currency_required=False,
        statement_basis_required=False,
        corporate_action_required=True,
        calculation_dependency=(),
        allowed_security_types=tuple(sorted(_SUPPORTED_EQUITY_TYPES)),
    ),
    "market_cap": FieldPolicy(
        field="market_cap",
        authority_chain=FIELD_AUTHORITY_CHAIN["price"],
        freshness_class="session_or_latest_eod",
        semantic_kinds=("MARKET_CAP",),
        as_of_required=True,
        period_required=False,
        unit_required=True,
        currency_required=True,
        statement_basis_required=False,
        corporate_action_required=True,
        calculation_dependency=("eod_close", "shares_outstanding"),
        allowed_security_types=tuple(sorted(_SUPPORTED_EQUITY_TYPES)),
        derived=True,
    ),
    "enterprise_value": FieldPolicy(
        field="enterprise_value",
        authority_chain=FIELD_AUTHORITY_CHAIN["price"],
        freshness_class="session_or_latest_eod",
        semantic_kinds=("ENTERPRISE_VALUE",),
        as_of_required=True,
        period_required=False,
        unit_required=True,
        currency_required=True,
        statement_basis_required=False,
        corporate_action_required=True,
        calculation_dependency=("eod_close", "shares_outstanding", "debt", "cash"),
        allowed_security_types=tuple(sorted(_SUPPORTED_EQUITY_TYPES)),
        derived=True,
    ),
}


def field_policy(field: str) -> FieldPolicy:
    if field in FIELD_POLICY_MATRIX:
        return FIELD_POLICY_MATRIX[field]
    group = _FIELD_GROUP.get(field, "financials")
    if group == "price":
        return FIELD_POLICY_MATRIX["eod_close"]
    if group == "shares":
        return FIELD_POLICY_MATRIX["shares_outstanding"]
    return _financial_policy(field)


def authority_tier_for(
    url: str | None,
    *,
    source_type: str | None = None,
    agent: str | None = None,
) -> str:
    """TIER_1A regulator/exchange → 1B issuer → 1C Screener → 2 secondary → 3 AI."""
    kind = str(source_type or "")
    if kind in _AI_SOURCE_TYPES or str(agent or "") in _AI_AGENTS:
        return "TIER_3"
    classified = classify_source_url(url, source_type=source_type)
    if classified == "approved_research":
        return "TIER_1C"
    if classified == "secondary":
        return "TIER_2"
    if classified == "primary":
        if kind == "company_ir":
            return "TIER_1B"
        return "TIER_1A"
    return "UNKNOWN"

_CLASS_ORDER: tuple[str, ...] = (
    "primary",
    "approved_research",
    "secondary",
    "unknown",
    "forbidden",
)

_TYPE_ORDER: tuple[str, ...] = (
    "exchange_eod",
    "regulator",
    "company_ir",
    "approved_research",
    "secondary",
    "llm",
    "agent_claim",
)


def source_authority_rank(
    field: str,
    source_class: str,
    *,
    source_type: str | None = None,
) -> tuple[int, int]:
    """Lower tuple is stronger. Field-specific: filings treat NSE and company IR equally."""
    group = _FIELD_GROUP.get(field, "financials")
    class_rank = (
        _CLASS_ORDER.index(source_class) if source_class in _CLASS_ORDER else 99
    )
    kind = str(source_type or "")
    if source_class == "primary" and kind in {"exchange_eod", "regulator"}:
        type_rank = 0
    elif source_class == "primary" and kind == "company_ir":
        type_rank = 0 if group == "financials" else 1
    elif source_class == "approved_research":
        type_rank = 2
    else:
        type_rank = _TYPE_ORDER.index(kind) if kind in _TYPE_ORDER else 9
    return (class_rank, type_rank)


def record_source_clash(
    *,
    field: str,
    primary_url: str,
    primary_value: str,
    research_url: str,
    research_value: str,
) -> dict[str, object]:
    """Record a Screener/primary clash. Primary wins. Never silent overwrite."""
    if str(primary_value) == str(research_value):
        return {
            "field": field,
            "cross_check": "PASS",
            "winner": "primary",
            "silent_overwrite": False,
            "stronger_source": primary_url,
            "stronger_value": primary_value,
            "weaker_source": research_url,
            "weaker_value": research_value,
        }
    return {
        "field": field,
        "cross_check": "CONFLICT",
        "winner": "primary",
        "recorded_as": "CONFLICT",
        "silent_overwrite": False,
        "stronger_source": primary_url,
        "stronger_value": primary_value,
        "weaker_source": research_url,
        "weaker_value": research_value,
    }
