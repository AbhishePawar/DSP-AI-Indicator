"""Conservative primary-document extraction. No semantic aliases. No LLM arithmetic."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from data_engine.official_research.currentness import CapitalEvent
from data_engine.official_research.models import CAPITAL_EVENT_TYPES, FailureStatus
from data_engine.official_research.semantics import (
    cannot_derive_shares,
    semantic_field_status,
)

__all__ = [
    "DocumentContext",
    "ExtractedField",
    "CanonicalPeriod",
    "attack_corporate_actions",
    "extract_labeled_field",
    "extract_shares_outstanding",
    "nearest_statement_basis",
    "nearest_unit_scale",
    "parse_document_context",
    "share_label_is_outstanding",
    "classify_share_semantic_type",
    "canonical_share_semantic_type",
    "classify_capital_effect",
    "classify_share_count_impact",
    "classify_share_count_effect_status",
    "classify_acquisition_consideration",
    "VALUATION_SHARE_SEMANTIC",
    "CANONICAL_SHARE_SEMANTICS",
    "canonicalize_period",
    "document_identity_matches",
    "normalize_numeric_to_actual",
    "periods_comparable",
    "price_semantic_kind",
]


_CA_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("buyback", re.compile(r"\bbuy[ -]?back\b", re.I)),
    ("bonus", re.compile(r"\bbonus (issue|share|shares)\b", re.I)),
    ("split", re.compile(r"\b(stock |share )?split\b", re.I)),
    ("rights", re.compile(r"\brights issue\b", re.I)),
    ("qip", re.compile(r"\bqualified institutional placement\b|\bqip\b", re.I)),
    ("fpo", re.compile(r"\bfollow[ -]?on public offer\b|\bfpo\b", re.I)),
    ("preferential_issue", re.compile(r"\bpreferential (issue|allotment)\b", re.I)),
    ("esop", re.compile(r"\besop\b|\bemployee stock option\b", re.I)),
    ("warrants", re.compile(r"\bwarrants?\b", re.I)),
    ("convertibles", re.compile(r"\bconvertible (bond|debenture|preference)\b", re.I)),
    (
        "cancellation",
        re.compile(
            r"\bshare cancellation\b|\bcancellation of shares\b|"
            r"\bextinguish(?:ment|ed)? of shares\b|\bshares extinguished\b",
            re.I,
        ),
    ),
    ("extinguishment", re.compile(r"\bextinguish(?:ment|ed)\b", re.I)),
    ("capital_reduction", re.compile(r"\bcapital reduction\b", re.I)),
    ("merger", re.compile(r"\bmerger\b", re.I)),
    ("demerger", re.compile(r"\bdemerger\b", re.I)),
    ("scheme", re.compile(r"\bscheme of (arrangement|amalgamation)\b", re.I)),
    ("share_swap", re.compile(r"\bshare swap\b", re.I)),
    ("acquisition", re.compile(r"\bacquisition\b|\bshare consideration\b", re.I)),
    ("new_issue", re.compile(r"\bnew issue of (equity )?shares\b|\bfresh issue of equity\b", re.I)),
)

_AS_OF = re.compile(
    r"\bas[ _]of\s*[:=]\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[-/]\w{3}[-/]\d{4})",
    re.I,
)

# Exact labels only. Operating profit is not EBIT; PPE purchase is not capex.
_PL_HEAD = re.compile(
    r"statement of profit\s*(?:and|&)\s*loss|statement of financial performance|"
    r"income statement|statement of comprehensive income|profit and loss account",
    re.I,
)
_BS_HEAD = re.compile(
    r"balance sheet|statement of financial position",
    re.I,
)
_CF_HEAD = re.compile(
    r"statement of cash flows|cash flow statement|statement of cash flow",
    re.I,
)
_FIELD_STATEMENT_HEAD: dict[str, re.Pattern[str]] = {
    "revenue": _PL_HEAD,
    "operating_profit": _PL_HEAD,
    "ebit": _PL_HEAD,
    "net_income": _PL_HEAD,
    "equity": _BS_HEAD,
    "cash": _BS_HEAD,
    "debt": _BS_HEAD,
    "total_assets": _BS_HEAD,
    "total_liabilities": _BS_HEAD,
    "cfo": _CF_HEAD,
    "capex": _CF_HEAD,
}

_FIELD_LABELS: dict[str, tuple[str, ...]] = {
    "revenue": ("revenue from operations", "revenue", "total revenue"),
    "operating_profit": ("operating profit",),
    "ebit": ("ebit",),
    "net_income": (
        "net income",
        "profit after tax",
        "profit for the year",
        "profit for the period",
        "profit after tax for the year",
    ),
    "equity": ("shareholders equity", "shareholders' equity", "total equity", "equity"),
    "cfo": (
        "cfo",
        "cash from operations",
        "net cash from operating activities",
        "net cash generated from operating activities",
        "net cash flows from operating activities",
        "cash flow from operating activities",
    ),
    "capex": ("capex", "capital expenditure"),
    "cash": ("cash and cash equivalents", "cash"),
    "debt": ("total borrowings", "borrowings", "debt"),
    "total_assets": ("total assets",),
    "total_liabilities": ("total liabilities",),
    "shares_outstanding": (
        "equity shares outstanding",
        "shares outstanding",
        "number of equity shares outstanding",
    ),
}

_SHARE_REJECT_LABELS = (
    "authorized capital",
    "authorised capital",
    "authorized shares",
    "authorised shares",
    "free float",
    "freefloat",
    "promoter holding",
    "treasury shares",
    "paid-up capital",
    "paid up capital",
    "face value",
    "weighted average",
    "listed quantity",
    "listed capital",
    "potential equity",
    "dilutive potential",
)

_CRORE = re.compile(r"(₹|rs\.?|inr).{0,12}(crore|crs)\b|\bin crore\b|\bin crs\b", re.I)
_LAKH = re.compile(r"(₹|rs\.?|inr).{0,12}(lakh|lac)s?\b|\bin lakh", re.I)
_MILLION = re.compile(r"(₹|rs\.?|inr).{0,12}millions?|\bin millions?\b", re.I)
_THOUSAND = re.compile(r"(₹|rs\.?|inr).{0,12}thousand|\bin thousand\b", re.I)
_ACTUAL = re.compile(r"unit:\s*actual|\bin actual\b|\bin rupees \(actual\)", re.I)
_YEAR_ENDED = re.compile(
    r"year ended\s+(\d{1,2}(?:st|nd|rd|th)?\s+\w+,?\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}[-/]\w{3}[-/]\d{4})",
    re.I,
)
_QUARTER_ENDED = re.compile(r"quarter ended|three months ended|quarterly results", re.I)
_RESTATED = re.compile(
    r"\b(restated|recast|reclassified|prior period restatement|comparative restated)\b",
    re.I,
)


@dataclass(frozen=True, slots=True)
class ExtractedField:
    field: str
    value: str
    as_of: date | None
    locator: str
    semantic_status: FailureStatus
    currency: str | None = None
    raw_value: str | None = None
    raw_unit: str | None = None
    unit_scale: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    period_type: str | None = None
    statement_basis: str | None = None
    restated: bool = False


@dataclass(frozen=True, slots=True)
class DocumentContext:
    currency: str | None
    unit_scale: str | None
    unit_multiplier: Decimal | None
    statement_basis: str | None
    period_type: str | None
    period_start: date | None
    period_end: date | None
    restated: bool
    issues: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CanonicalPeriod:
    code: str
    period_type: str
    period_end: date | None


_UNIT_TO_ACTUAL: dict[str, Decimal] = {
    "actual": Decimal("1"),
    "rupee": Decimal("1"),
    "rupees": Decimal("1"),
    "inr": Decimal("1"),
    "share": Decimal("1"),
    "shares": Decimal("1"),
    "thousand": Decimal("1000"),
    "thousands": Decimal("1000"),
    "lakh": Decimal("100000"),
    "lakhs": Decimal("100000"),
    "lac": Decimal("100000"),
    "lacs": Decimal("100000"),
    "million": Decimal("1000000"),
    "millions": Decimal("1000000"),
    "crore": Decimal("10000000"),
    "crores": Decimal("10000000"),
    "crs": Decimal("10000000"),
    "cr": Decimal("10000000"),
}

_FY_YEAR = re.compile(
    r"^(?:fy\s*)?(\d{4})(?:\s*[-/]\s*(\d{2}|\d{4}))?$",
    re.I,
)
_YEAR_ENDED_PERIOD = re.compile(
    r"year ended\s+(?:march\s+)?(?:31|31st)?\s*,?\s*(?:march\s+)?(\d{4})",
    re.I,
)
_QUARTER_PERIOD = re.compile(r"\bq([1-4])\s*(?:fy)?\s*(\d{4})\b|\bquarter\b|\bttm\b|\bytd\b", re.I)


def normalize_numeric_to_actual(
    value: str | None, unit: str | None
) -> Decimal | None:
    """Convert labeled units to absolute amounts. Unknown units are never guessed."""
    if value is None or str(value).strip() == "":
        return None
    raw = str(value).strip().replace(",", "").replace("₹", "").replace("rs.", "")
    raw = raw.replace("INR", "").strip()
    try:
        amount = Decimal(raw)
    except (InvalidOperation, ValueError):
        return None
    scale = str(unit or "").strip().lower()
    if not scale:
        return None
    multiplier = _UNIT_TO_ACTUAL.get(scale)
    if multiplier is None:
        return None
    return amount * multiplier


def canonicalize_period(text: str | None, *, as_of: date | None = None) -> CanonicalPeriod | None:
    """Normalize FY / year-ended labels. Do not collapse FY, quarter, TTM, or YTD."""
    raw = str(text or "").strip()
    if not raw and as_of is None:
        return None
    lowered = raw.lower()
    if "ttm" in lowered or "trailing twelve" in lowered:
        return CanonicalPeriod(code="TTM", period_type="TTM", period_end=as_of)
    if re.search(r"\bytd\b|year to date|year-to-date", lowered):
        return CanonicalPeriod(code="YTD", period_type="YTD", period_end=as_of)
    quarter = re.search(r"\bq([1-4])\s*(?:fy)?\s*(\d{4})\b", lowered)
    if quarter:
        year = int(quarter.group(2))
        return CanonicalPeriod(
            code=f"Q{quarter.group(1)}FY{year}",
            period_type="QUARTER",
            period_end=as_of,
        )
    if _QUARTER_PERIOD.search(lowered) and "year ended" not in lowered:
        return CanonicalPeriod(code=raw or "QUARTER", period_type="QUARTER", period_end=as_of)
    ended = _YEAR_ENDED_PERIOD.search(lowered)
    if ended:
        year = int(ended.group(1))
        return CanonicalPeriod(
            code=f"FY{year}",
            period_type="FY",
            period_end=date(year, 3, 31),
        )
    fy = _FY_YEAR.match(re.sub(r"\s+", "", lowered))
    if fy:
        start = int(fy.group(1))
        end_raw = fy.group(2)
        if end_raw is None:
            year = start
        elif len(end_raw) == 2:
            year = (start // 100) * 100 + int(end_raw)
            if year < start:
                year += 100
        else:
            year = int(end_raw)
        return CanonicalPeriod(
            code=f"FY{year}",
            period_type="FY",
            period_end=date(year, 3, 31),
        )
    if as_of is not None and as_of.month == 3 and as_of.day == 31:
        return CanonicalPeriod(code=f"FY{as_of.year}", period_type="FY", period_end=as_of)
    if as_of is not None:
        return CanonicalPeriod(code=as_of.isoformat(), period_type="UNKNOWN", period_end=as_of)
    return None


def periods_comparable(left: CanonicalPeriod | None, right: CanonicalPeriod | None) -> bool:
    if left is None or right is None:
        return False
    if left.period_type != right.period_type:
        return False
    if left.period_type in {"FY", "QUARTER", "TTM", "YTD"}:
        return left.code == right.code
    return left.period_end == right.period_end and left.period_end is not None


def price_semantic_kind(*, field: str, raw_price_field: str | None, source_type: str | None) -> str:
    raw = str(raw_price_field or "").strip()
    lowered = raw.lower()
    token = str(field or "").strip().lower()
    if token in {"eod_close"} or raw in {"ClsPric", "cls_pric"} or lowered == "eod":
        return "EOD"
    if raw in {"PrvsClsgPric", "prvs_clsg_pric"} or "previous" in lowered:
        return "PREVIOUS_CLOSE"
    if token == "last_price" and ("delay" in lowered or source_type == "secondary"):
        return "DELAYED"
    if token == "last_price" or "realtime" in lowered or lowered == "current":
        return "CURRENT"
    if "historical" in lowered or token == "historical_close":
        return "HISTORICAL_CLOSE"
    if token in {"price", "last_price"}:
        return "UNKNOWN"
    return "UNKNOWN"


_ISIN_TOKEN = re.compile(r"\bINE[A-Z0-9]{9}\b", re.I)


def document_identity_matches(
    text: str,
    *,
    isin: str,
    company_name: str | None = None,
    other_issuers: tuple[str, ...] = (),
) -> bool:
    """If the document names ISINs, one of them must be this listing."""
    found = {item.upper() for item in _ISIN_TOKEN.findall(text or "")}
    if found and isin.strip().upper() not in found:
        return False
    if company_name and other_issuers:
        from data_engine.official_research.company_sources import issuer_names_compatible

        hay = str(text or "")[:16000]
        ours = issuer_names_compatible(company_name, hay)
        for other in other_issuers:
            if issuer_names_compatible(other, hay) and not ours:
                return False
    return True


_MIXED_BASIS_PHRASE = re.compile(
    r"consolidated\s+and\s+standalone|standalone\s+and\s+consolidated",
    re.I,
)


def nearest_statement_basis(text: str, position: int) -> str | None:
    """Nearest preceding standalone/consolidated token, ignoring mixed phrases."""
    prefix = _MIXED_BASIS_PHRASE.sub(" ", str(text or "")[:position])
    lowered = prefix.lower()
    cons = lowered.rfind("consolidated")
    stand = lowered.rfind("standalone")
    if cons < 0 and stand < 0:
        return None
    if cons > stand:
        return "consolidated"
    if stand > cons:
        return "standalone"
    return None


_UNIT_NEAR: tuple[tuple[re.Pattern[str], Decimal, str], ...] = (
    (_CRORE, Decimal("10000000"), "crore"),
    (_LAKH, Decimal("100000"), "lakh"),
    (_MILLION, Decimal("1000000"), "million"),
    (_THOUSAND, Decimal("1000"), "thousand"),
    (_ACTUAL, Decimal("1"), "actual"),
)


def nearest_unit_scale(
    text: str, position: int, *, window: int = 2500
) -> tuple[Decimal, str] | None:
    """Nearest explicit unit before a field. Mixed document units are allowed per field."""
    start = max(0, int(position) - window)
    prefix = str(text or "")[start:position]
    best_at = -1
    found: tuple[Decimal, str] | None = None
    for pattern, multiplier, scale in _UNIT_NEAR:
        for match in pattern.finditer(prefix):
            if match.start() >= best_at:
                best_at = match.start()
                found = (multiplier, scale)
    return found


def _parse_date(raw: str) -> date | None:
    text = raw.strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        pass
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%d/%m/%Y"):
        try:
            from datetime import datetime

            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _document_as_of(text: str) -> date | None:
    match = _AS_OF.search(text)
    if match is None:
        return None
    return _parse_date(match.group(1))


def parse_document_context(text: str) -> DocumentContext:
    """Read explicit header semantics only. Never guess unlabeled unit/basis."""
    issues: list[str] = []
    lowered = text.lower()
    currency = "INR" if re.search(r"₹|inr\b|rs\.?", lowered) else None
    scales: list[tuple[Decimal, str]] = []
    if _CRORE.search(text):
        scales.append((Decimal("10000000"), "crore"))
    if _LAKH.search(text):
        scales.append((Decimal("100000"), "lakh"))
    if _MILLION.search(text):
        scales.append((Decimal("1000000"), "million"))
    if _THOUSAND.search(text):
        scales.append((Decimal("1000"), "thousand"))
    if _ACTUAL.search(text):
        scales.append((Decimal("1"), "actual"))
    multiplier: Decimal | None = None
    unit_scale = None
    if len(scales) == 1:
        multiplier, unit_scale = scales[0]
    elif len(scales) > 1:
        issues.append("multiple unit scales present")
    has_consolidated = "consolidated" in lowered
    has_standalone = "standalone" in lowered
    basis = None
    if has_consolidated and not has_standalone:
        basis = "consolidated"
    elif has_standalone and not has_consolidated:
        basis = "standalone"
    elif has_consolidated and has_standalone:
        basis = None
        issues.append("consolidated and standalone both present")
    period_type = None
    period_end = None
    year = _YEAR_ENDED.search(text)
    if year is not None:
        period_type = "FY"
        period_end = _parse_date(year.group(1).replace(" ", "-")) or _parse_flexible_day(
            year.group(1)
        )
        if _QUARTER_ENDED.search(text):
            issues.append("document also mentions quarterly periods; annual year-ended used")
    elif _QUARTER_ENDED.search(text):
        period_type = "quarter"
        issues.append("quarterly document cannot satisfy annual DSP fields")
    as_of = _document_as_of(text)
    if period_end is None:
        period_end = as_of
    period_start = None
    if period_end is not None and period_end.month == 3 and period_end.day == 31:
        period_start = date(period_end.year - 1, 4, 1)
    return DocumentContext(
        currency=currency,
        unit_scale=unit_scale,
        unit_multiplier=multiplier,
        statement_basis=basis,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        restated=bool(_RESTATED.search(text)),
        issues=tuple(issues),
    )


def _parse_flexible_day(raw: str) -> date | None:
    text = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", " ".join(raw.strip().split()), flags=re.I)
    from datetime import datetime

    for fmt in ("%d %B %Y", "%d %b %Y", "%d-%B-%Y", "%d-%b-%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return _parse_date(text)


VALUATION_SHARE_SEMANTIC = "TOTAL_OUTSTANDING"
CANONICAL_SHARE_SEMANTICS: frozenset[str] = frozenset(
    {
        "TOTAL_OUTSTANDING",
        "ISSUED",
        "PAID_UP",
        "LISTED",
        "FREE_FLOAT",
        "PROMOTER",
        "WEIGHTED_AVERAGE_EPS",
        "POTENTIAL_DILUTED",
        "AUTHORIZED",
        "UNKNOWN",
    }
)
_SHARE_SEMANTIC_CANONICAL = {
    "TOTAL_OUTSTANDING": "TOTAL_OUTSTANDING",
    "ISSUED": "ISSUED",
    "PAID_UP": "PAID_UP",
    "LISTED": "LISTED",
    "FREE_FLOAT": "FREE_FLOAT",
    "PROMOTER": "PROMOTER",
    "WEIGHTED_AVERAGE": "WEIGHTED_AVERAGE_EPS",
    "DILUTED_EPS_DENOMINATOR": "WEIGHTED_AVERAGE_EPS",
    "WEIGHTED_AVERAGE_EPS": "WEIGHTED_AVERAGE_EPS",
    "TRANCHE": "POTENTIAL_DILUTED",
    "POTENTIAL_DILUTED": "POTENTIAL_DILUTED",
    "AUTHORIZED": "AUTHORIZED",
}


def classify_share_semantic_type(label: str) -> str:
    """Generic share-label semantics. Not an issuer table."""
    lowered = re.sub(r"\s+", " ", str(label or "").strip().lower())
    if not lowered:
        return "UNKNOWN"
    if "weighted average" in lowered:
        return "WEIGHTED_AVERAGE"
    if "dilut" in lowered and (
        "eps" in lowered or "earnings per" in lowered or "denominator" in lowered
    ):
        return "DILUTED_EPS_DENOMINATOR"
    if (
        "potential equity" in lowered
        or "dilutive potential" in lowered
        or "effect of potential" in lowered
        or "potential diluted" in lowered
    ):
        return "TRANCHE"
    if "listed quantity" in lowered or "listed shares" in lowered or "listed capital" in lowered:
        return "LISTED"
    if "free float" in lowered or "freefloat" in lowered:
        return "FREE_FLOAT"
    if "promoter holding" in lowered or "promoter shareholding" in lowered:
        return "PROMOTER"
    if "authorised" in lowered or "authorized" in lowered:
        return "AUTHORIZED"
    if "treasury" in lowered:
        return "TREASURY"
    if ("paid-up" in lowered or "paid up" in lowered) and "capital" in lowered:
        return "PAID_UP"
    if "issued" in lowered and "outstanding" not in lowered:
        return "ISSUED"
    compact = re.sub(r"[^a-z0-9]+", "", lowered)
    if compact in {"totalnoofshares", "totalnumberofshares", "total_shares"}:
        if "promoter" not in lowered and "float" not in lowered:
            return "TOTAL_OUTSTANDING"
    if share_label_is_outstanding(lowered) and "outstanding" in lowered:
        return "TOTAL_OUTSTANDING"
    if "outstanding" in lowered:
        return "OTHER"
    return "UNKNOWN"


def canonical_share_semantic_type(label: str) -> str:
    """Valuation-facing share class. Only TOTAL_OUTSTANDING may feed market cap."""
    token = str(label or "").strip()
    if token in _SHARE_SEMANTIC_CANONICAL:
        return _SHARE_SEMANTIC_CANONICAL[token]
    if token in CANONICAL_SHARE_SEMANTICS:
        return token
    raw = classify_share_semantic_type(label)
    return _SHARE_SEMANTIC_CANONICAL.get(raw, "UNKNOWN")


def classify_capital_effect(event_type: str) -> str:
    """Share-count effect of a CA type. Acquisition is UNKNOWN, not assumed."""
    kind = str(event_type or "").strip().lower()
    if kind in {"buyback", "cancellation", "extinguishment", "capital_reduction"}:
        return "DECREASE"
    if kind in {
        "bonus",
        "split",
        "rights",
        "qip",
        "fpo",
        "preferential_issue",
        "esop",
        "warrants",
        "convertibles",
        "new_issue",
    }:
        return "INCREASE"
    if kind in {"merger", "demerger", "scheme", "share_swap", "acquisition"}:
        return "UNKNOWN"
    return "UNKNOWN"


def classify_share_count_impact(
    event_type: str,
    *,
    acquisition_consideration: str | None = None,
) -> str:
    """Explicit share-count impact. Acquisition is not assumed to issue shares."""
    kind = str(event_type or "").strip().lower()
    if kind == "acquisition":
        consider = str(acquisition_consideration or "UNKNOWN").strip().upper()
        if consider == "CASH":
            return "NO_SHARE_COUNT_CHANGE"
        if consider in {"SHARE_SWAP", "MIXED"}:
            return "POTENTIAL_CHANGE"
        return "UNKNOWN"
    effect = classify_capital_effect(kind)
    if effect == "INCREASE":
        return "SHARE_COUNT_INCREASE"
    if effect == "DECREASE":
        return "SHARE_COUNT_DECREASE"
    if kind in {"merger", "demerger", "scheme", "share_swap"}:
        return "POTENTIAL_CHANGE"
    if not kind:
        return "NOT_APPLICABLE"
    return "UNKNOWN"


def classify_share_count_effect_status(
    event_type: str,
    *,
    acquisition_consideration: str | None = None,
) -> str:
    """SIMPLE-22 vocabulary over the existing CA impact classifier."""
    impact = classify_share_count_impact(
        event_type, acquisition_consideration=acquisition_consideration
    )
    return {
        "NO_SHARE_COUNT_CHANGE": "NO_SHARE_COUNT_EFFECT",
        "SHARE_COUNT_INCREASE": "INCREASES_OUTSTANDING",
        "SHARE_COUNT_DECREASE": "DECREASES_OUTSTANDING",
        "POTENTIAL_CHANGE": "POTENTIALLY_CHANGES_OUTSTANDING",
        "NOT_APPLICABLE": "NO_SHARE_COUNT_EFFECT",
        "UNKNOWN": "UNKNOWN",
    }.get(impact, "UNKNOWN")


def classify_acquisition_consideration(text: str) -> str:
    """Acquisition does not imply a share-count change. Classify consideration only."""
    lowered = re.sub(r"\s+", " ", str(text or "").strip().lower())
    if not lowered:
        return "UNKNOWN"
    cash = bool(
        re.search(
            r"\bcash (consideration|deal|acquisition)\b|"
            r"\bconsideration.{0,60}\bcash\b|"
            r"\bpaid (entirely |wholly |fully )?in cash\b|"
            r"\bcash acquisition\b",
            lowered,
        )
    )
    swap = bool(
        re.search(
            r"\bshare swap\b|"
            r"\bshare consideration\b|"
            r"\bconsideration.{0,60}\b(shares|equity)\b|"
            r"\bexchange of shares\b|"
            r"\bstock (as )?consideration\b",
            lowered,
        )
    )
    if cash and swap:
        return "MIXED"
    if cash:
        return "CASH"
    if swap:
        return "SHARE_SWAP"
    return "UNKNOWN"


def share_label_is_outstanding(label: str) -> bool:
    """Reject authorized / free-float / rupee capital as outstanding shares."""
    lowered = label.strip().lower()
    if any(item in lowered for item in _SHARE_REJECT_LABELS):
        return False
    if "capital" in lowered and "share" in lowered and "outstanding" not in lowered:
        return False
    if "weighted average" in lowered:
        return False
    if "potential equity" in lowered or "dilutive potential" in lowered:
        return False
    if "effect of potential" in lowered:
        return False
    if "listed quantity" in lowered or "listed shares" in lowered:
        return False
    return True


def attack_corporate_actions(
    text: str,
    *,
    event_date: date | None = None,
) -> tuple[CapitalEvent, ...]:
    """Deterministic CA attack on primary-document text. Does not fabricate agents."""
    found: list[CapitalEvent] = []
    seen: set[str] = set()
    dated = event_date or _document_as_of(text)
    if dated is None:
        return ()
    for event_type, pattern in _CA_PATTERNS:
        if event_type not in CAPITAL_EVENT_TYPES:
            continue
        if event_type in seen:
            continue
        if pattern.search(text):
            seen.add(event_type)
            changing = classify_capital_effect(event_type) in {"INCREASE", "DECREASE"}
            if event_type == "share_swap":
                changing = True
            elif event_type == "acquisition":
                consideration = classify_acquisition_consideration(text)
                changing = consideration in {"SHARE_SWAP", "MIXED"}
            elif event_type in {"merger", "demerger", "scheme"}:
                changing = False
            found.append(
                CapitalEvent(event_type, dated, capital_changing=changing)
            )
    return tuple(found)


def nearest_page_marker(text: str, position: int) -> str | None:
    matches = list(re.finditer(r"\[\[PAGE (\d+)\]\]", str(text or "")[: max(0, position)]))
    if not matches:
        return None
    return matches[-1].group(1)


def _locator_with_page(text: str, position: int, label: str) -> str:
    page = nearest_page_marker(text, position)
    if page is None:
        return label
    return f"page={page};row={label}"


_STATEMENT_WINDOW = 80000
_LONG_DOCUMENT_CHARS = 8000


def _last_heading_start(text: str, heading: re.Pattern[str]) -> int:
    last = -1
    for found in heading.finditer(text):
        last = found.start()
    return last


def _match_in_statement_window(
    text: str, heading: re.Pattern[str], match_start: int, *, window: int = _STATEMENT_WINDOW
) -> bool:
    """Accept a labeled number only after the nearest preceding statement heading."""
    last = -1
    for found in heading.finditer(text):
        if found.start() >= match_start:
            break
        last = found.start()
    if last < 0:
        return False
    return match_start - last <= window


def extract_labeled_field(text: str, field: str) -> ExtractedField | None:
    """Extract only when the document uses an allowed explicit label."""
    requested = field.strip().lower().replace(" ", "_")
    labels = _FIELD_LABELS.get(requested)
    if labels is None:
        return None
    context = parse_document_context(text)
    as_of = context.period_end or _document_as_of(text)
    if requested == "shares_outstanding":
        as_of = _document_as_of(text) or as_of
    if requested != "shares_outstanding" and context.period_type == "quarter":
        return ExtractedField(
            field=requested,
            value="",
            as_of=as_of,
            locator="quarterly",
            semantic_status="UNKNOWN",
            period_type="quarter",
            statement_basis=context.statement_basis,
        )
    if requested == "shares_outstanding" and not share_label_is_outstanding(
        " ".join(labels)
    ):
        return None
    unlabeled_unit: ExtractedField | None = None
    verified_hits: list[ExtractedField] = []
    require_heading = len(text) > _LONG_DOCUMENT_CHARS and requested != "shares_outstanding"
    lowered = text.lower()
    mixed_basis = context.statement_basis is None and (
        "consolidated" in lowered and "standalone" in lowered
    )
    search_text = text
    search_offset = 0
    heading = _FIELD_STATEMENT_HEAD.get(requested) if require_heading else None
    if heading is not None:
        last = _last_heading_start(text, heading)
        if last < 0:
            if requested == "ebit" and re.search(r"operating profit\s*[:=]", text, re.I):
                return ExtractedField(
                    field="ebit",
                    value="",
                    as_of=as_of,
                    locator="operating profit",
                    semantic_status="UNKNOWN",
                    statement_basis=context.statement_basis,
                )
            return None
        search_offset = last
        search_text = text[last : last + _STATEMENT_WINDOW]
    for label in labels:
        if requested == "shares_outstanding" and not share_label_is_outstanding(label):
            continue
        pattern = re.compile(
            rf"{re.escape(label)}\s*[:=\s]\s*([-+]?\d[\d,]*(?:\.\d+)?)",
            re.I,
        )
        pair_pattern = re.compile(
            rf"{re.escape(label)}\s*[:=\s]\s*([-+]?\d[\d,]*(?:\.\d+)?)\s+([-+]?\d[\d,]*(?:\.\d+)?)",
            re.I,
        )
        iterators = (
            pair_pattern.finditer(search_text)
            if require_heading
            else pattern.finditer(search_text)
        )
        for match in iterators:
            position = match.start() + search_offset
            if requested == "shares_outstanding":
                nearby = search_text[max(0, match.start() - 80) : match.end() + 40]
                if not share_label_is_outstanding(nearby):
                    continue
            local_basis = context.statement_basis
            if mixed_basis:
                local_basis = nearest_statement_basis(text, position)
                if local_basis is None:
                    continue
                if local_basis != "consolidated":
                    continue
            semantic = semantic_field_status(
                requested_field=requested, document_label=label
            )
            raw = match.group(1).replace(",", "")
            locator = _locator_with_page(text, position, label)
            if semantic != "VERIFIED":
                return ExtractedField(
                    field=requested,
                    value="",
                    as_of=as_of,
                    locator=locator,
                    semantic_status="UNKNOWN",
                    currency=context.currency,
                    raw_value=raw,
                    raw_unit=context.unit_scale,
                    period_end=context.period_end,
                    period_type=context.period_type,
                    statement_basis=local_basis,
                    restated=context.restated,
                )
            if requested != "shares_outstanding":
                if context.unit_multiplier is not None and context.unit_scale is not None:
                    local_unit = (context.unit_multiplier, context.unit_scale)
                else:
                    local_unit = nearest_unit_scale(text, position)
                if local_unit is None:
                    unlabeled_unit = ExtractedField(
                        field=requested,
                        value="",
                        as_of=as_of,
                        locator=locator,
                        semantic_status="UNKNOWN",
                        currency=context.currency,
                        raw_value=raw,
                        raw_unit=None,
                        period_end=context.period_end,
                        period_type=context.period_type,
                        statement_basis=local_basis,
                        restated=context.restated,
                    )
                    continue
                try:
                    normalized = Decimal(raw) * local_unit[0]
                except (InvalidOperation, ValueError):
                    return None
                value = format(normalized, "f")
                raw_unit = local_unit[1]
            else:
                try:
                    if Decimal(raw) <= 0:
                        return None
                except (InvalidOperation, ValueError):
                    return None
                value = raw
                raw_unit = "shares"
            verified_hits.append(
                ExtractedField(
                    field=requested,
                    value=value,
                    as_of=as_of,
                    locator=locator,
                    semantic_status="VERIFIED",
                    currency=context.currency if requested != "shares_outstanding" else None,
                    raw_value=raw,
                    raw_unit=raw_unit,
                    unit_scale="actual" if requested != "shares_outstanding" else "shares",
                    period_start=context.period_start,
                    period_end=context.period_end,
                    period_type=context.period_type,
                    statement_basis=local_basis,
                    restated=context.restated,
                )
            )
            if not require_heading:
                return verified_hits[0]
    if require_heading and verified_hits:
        distinct = {item.value for item in verified_hits}
        if len(distinct) > 1:
            first = verified_hits[0]
            return ExtractedField(
                field=requested,
                value="",
                as_of=as_of,
                locator=first.locator,
                semantic_status="CONFLICT",
                currency=first.currency,
                raw_value=first.raw_value,
                raw_unit=first.raw_unit,
                period_start=first.period_start,
                period_end=first.period_end,
                period_type=context.period_type,
                statement_basis=first.statement_basis,
                restated=context.restated,
            )
        return verified_hits[0]
    if unlabeled_unit is not None:
        return unlabeled_unit
    if requested == "ebit" and re.search(r"operating profit\s*[:=]", text, re.I):
        return ExtractedField(
            field="ebit",
            value="",
            as_of=as_of,
            locator="operating profit",
            semantic_status="UNKNOWN",
            statement_basis=context.statement_basis,
        )
    return None


def extract_shares_outstanding(
    text: str,
    *,
    derived_from: str | None = None,
) -> ExtractedField | None:
    if derived_from and cannot_derive_shares(derived_from):
        return None
    extracted = extract_labeled_field(text, "shares_outstanding")
    if extracted is None:
        return None
    if extracted.as_of is None:
        return ExtractedField(
            field="shares_outstanding",
            value="",
            as_of=None,
            locator=extracted.locator,
            semantic_status="UNKNOWN",
            raw_value=extracted.raw_value,
            raw_unit=extracted.raw_unit,
        )
    try:
        if Decimal(extracted.value) <= 0:
            return None
    except (InvalidOperation, ValueError):
        return None
    return extracted
