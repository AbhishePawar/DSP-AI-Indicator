"""Business-type metric selection for educational analysis.

Does not calculate metrics — only selects which labels to prefer when
presenting financial health and economics sections.
"""

from __future__ import annotations

from typing import Any, Mapping

BusinessType = str

METRIC_PRESETS: dict[BusinessType, tuple[str, ...]] = {
    "bank": (
        "aum",
        "nim",
        "roa",
        "roe",
        "credit_cost",
        "gnpa",
        "nnpa",
        "capital_adequacy",
    ),
    "nbfc": (
        "aum",
        "nim",
        "roa",
        "roe",
        "credit_cost",
        "gnpa",
        "nnpa",
        "capital_adequacy",
    ),
    "insurance": (
        "premium_growth",
        "combined_ratio",
        "solvency",
        "roe",
        "investment_yield",
    ),
    "asset_manager": (
        "aum",
        "fee_income",
        "market_share",
        "operating_margin",
        "roe",
        "net_flows",
    ),
    "exchange": (
        "transaction_volumes",
        "market_share",
        "recurring_revenue",
        "operating_leverage",
        "roe",
        "regulatory_moat",
    ),
    "it_saas": (
        "revenue_growth",
        "ebit_margin",
        "fcf",
        "roce",
        "recurring_revenue",
        "arr",
        "retention",
        "client_concentration",
    ),
    "consumer": (
        "volume_growth",
        "pricing",
        "gross_margin",
        "distribution",
        "brand_strength",
        "roce",
    ),
    "manufacturing": (
        "capacity",
        "utilization",
        "margins",
        "working_capital",
        "roce",
        "capex",
    ),
    "infrastructure": (
        "asset_base",
        "utilization",
        "regulatory_returns",
        "leverage",
        "cash_conversion",
        "roce",
    ),
    "general": (
        "revenue_growth",
        "operating_margin",
        "net_margin",
        "roe",
        "roce",
        "operating_cash_flow",
        "free_cash_flow",
        "debt",
        "interest_coverage",
    ),
}

_KEYWORD_MAP: tuple[tuple[tuple[str, ...], BusinessType], ...] = (
    (("bank", "banking", "lender"), "bank"),
    (("nbfc", "non-banking", "housing finance", "hfc"), "nbfc"),
    (("insurance", "life insurance", "general insurance"), "insurance"),
    (("asset management", "mutual fund", "amc", "aum"), "asset_manager"),
    (("exchange", "clearing", "depository", "market infrastructure"), "exchange"),
    (("software", "saas", "it services", "information technology"), "it_saas"),
    (("fmcg", "consumer", "retail brand"), "consumer"),
    (("manufactur", "industrial", "auto ancillary"), "manufacturing"),
    (("infra", "power", "utility", " toll"), "infrastructure"),
)


def detect_business_type(
    *,
    sector: str | None = None,
    industry: str | None = None,
    company: str | None = None,
    hints: Mapping[str, Any] | None = None,
) -> BusinessType:
    """Best-effort classification from text hints; defaults to general."""
    if hints:
        explicit = hints.get("business_type") or hints.get("businessType")
        if isinstance(explicit, str) and explicit.strip().lower() in METRIC_PRESETS:
            return explicit.strip().lower()

    blob = " ".join(
        str(x).lower()
        for x in (sector, industry, company, (hints or {}).get("description"))
        if x
    )
    if not blob.strip():
        return "general"
    for keywords, btype in _KEYWORD_MAP:
        if any(k in blob for k in keywords):
            return btype
    return "general"


def preferred_metrics(business_type: BusinessType) -> tuple[str, ...]:
    return METRIC_PRESETS.get(business_type, METRIC_PRESETS["general"])


def economics_focus_bullets(business_type: BusinessType) -> list[str]:
    """Educational prompts for economics section (not fabricated facts)."""
    focuses: dict[BusinessType, list[str]] = {
        "bank": [
            "Revenue engine: net interest income and fee income from loans and deposits.",
            "Key lenses: NIM, credit cost, GNPA/NNPA, capital adequacy, ROA/ROE.",
            "Capital intensity: balance-sheet leverage and regulatory capital are central.",
        ],
        "nbfc": [
            "Revenue engine: interest and fee income on credit books (AUM).",
            "Key lenses: NIM, AUM growth, credit cost, GNPA/NNPA, capital adequacy.",
            "Funding and asset quality drive cash generation more than plant & equipment.",
        ],
        "insurance": [
            "Revenue engine: premiums and investment income on float.",
            "Key lenses: premium growth, combined/solvency ratios, investment yield.",
            "Underwriting discipline and float management shape economics.",
        ],
        "asset_manager": [
            "Revenue engine: fees on assets under management (AUM).",
            "Key lenses: AUM, net flows, fee rates, operating margin, ROE.",
            "Operating leverage can be high once scale is achieved.",
        ],
        "exchange": [
            "Revenue engine: transaction fees and often listing/data services.",
            "Key lenses: volumes, market share, operating leverage, regulatory position.",
            "Fixed-cost platforms can show strong incremental margins with volume.",
        ],
        "it_saas": [
            "Revenue engine: services contracts and/or subscription (ARR) revenue.",
            "Key lenses: revenue growth, EBIT margin, FCF, retention, client concentration.",
            "Capital intensity is often lower; talent and delivery quality matter.",
        ],
        "consumer": [
            "Revenue engine: product sales through brand and distribution.",
            "Key lenses: volume, pricing, gross margin, brand, ROCE.",
            "Working capital and advertising/distribution spend shape cash conversion.",
        ],
        "manufacturing": [
            "Revenue engine: production and sale of goods.",
            "Key lenses: capacity, utilization, raw materials, working capital, ROCE, capex.",
            "Operating leverage and inventory cycles are often material.",
        ],
        "infrastructure": [
            "Revenue engine: regulated or contracted returns on long-lived assets.",
            "Key lenses: asset base, utilization, leverage, cash conversion, ROCE.",
            "Capex and financing structure dominate reinvestment needs.",
        ],
        "general": [
            "Revenue engine: how customers pay for products or services.",
            "Key lenses: growth, margins, returns on capital, cash flow, leverage.",
            "Reinvestment needs depend on capital intensity and working capital.",
        ],
    }
    return list(focuses.get(business_type, focuses["general"]))
