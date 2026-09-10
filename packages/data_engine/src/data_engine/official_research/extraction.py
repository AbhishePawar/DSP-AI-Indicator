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
    "attack_corporate_actions",
    "extract_labeled_field",
    "extract_shares_outstanding",
    "parse_document_context",
    "share_label_is_outstanding",
    "document_identity_matches",
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
        re.compile(r"\bshare cancellation\b|\bcancellation of shares\b", re.I),
    ),
    ("capital_reduction", re.compile(r"\bcapital reduction\b", re.I)),
    ("merger", re.compile(r"\bmerger\b", re.I)),
    ("demerger", re.compile(r"\bdemerger\b", re.I)),
    ("scheme", re.compile(r"\bscheme of (arrangement|amalgamation)\b", re.I)),
    ("share_swap", re.compile(r"\bshare swap\b", re.I)),
)

_AS_OF = re.compile(
    r"\bas[ _]of\s*[:=]\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[-/]\w{3}[-/]\d{4})",
    re.I,
)

# Exact labels only. Operating profit is not EBIT; PPE purchase is not capex.
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
)

_CRORE = re.compile(r"(₹|rs\.?|inr).{0,12}(crore|crs)\b|\bin crore\b|\bin crs\b", re.I)
_LAKH = re.compile(r"(₹|rs\.?|inr).{0,12}(lakh|lac)s?\b|\bin lakh", re.I)
_MILLION = re.compile(r"(₹|rs\.?|inr).{0,12}million|\bin million\b", re.I)
_THOUSAND = re.compile(r"(₹|rs\.?|inr).{0,12}thousand|\bin thousand\b", re.I)
_ACTUAL = re.compile(r"unit:\s*actual|\bin actual\b|\bin rupees \(actual\)", re.I)
_YEAR_ENDED = re.compile(
    r"year ended\s+(\d{1,2}\s+\w+\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}[-/]\w{3}[-/]\d{4})",
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


_ISIN_TOKEN = re.compile(r"\bINE[A-Z0-9]{9}\b", re.I)


def document_identity_matches(text: str, *, isin: str) -> bool:
    """If the document names ISINs, one of them must be this listing."""
    found = {item.upper() for item in _ISIN_TOKEN.findall(text or "")}
    if not found:
        return True
    return isin.strip().upper() in found


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
    multiplier: Decimal | None = None
    unit_scale = None
    if _CRORE.search(text):
        multiplier, unit_scale = Decimal("10000000"), "crore"
    elif _LAKH.search(text):
        multiplier, unit_scale = Decimal("100000"), "lakh"
    elif _MILLION.search(text):
        multiplier, unit_scale = Decimal("1000000"), "million"
    elif _THOUSAND.search(text):
        multiplier, unit_scale = Decimal("1000"), "thousand"
    elif _ACTUAL.search(text):
        multiplier, unit_scale = Decimal("1"), "actual"
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
    if _QUARTER_ENDED.search(text):
        period_type = "quarter"
        issues.append("quarterly document cannot satisfy annual DSP fields")
    year = _YEAR_ENDED.search(text)
    if year is not None:
        period_type = "FY"
        period_end = _parse_date(year.group(1).replace(" ", "-")) or _parse_flexible_day(
            year.group(1)
        )
    as_of = _document_as_of(text)
    if period_end is None:
        period_end = as_of
    return DocumentContext(
        currency=currency,
        unit_scale=unit_scale,
        unit_multiplier=multiplier,
        statement_basis=basis,
        period_type=period_type,
        period_start=None,
        period_end=period_end,
        restated=bool(_RESTATED.search(text)),
        issues=tuple(issues),
    )


def _parse_flexible_day(raw: str) -> date | None:
    text = " ".join(raw.strip().split())
    from datetime import datetime

    for fmt in ("%d %B %Y", "%d %b %Y", "%d-%B-%Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return _parse_date(text)


def share_label_is_outstanding(label: str) -> bool:
    """Reject authorized / free-float / rupee capital as outstanding shares."""
    lowered = label.strip().lower()
    if any(item in lowered for item in _SHARE_REJECT_LABELS):
        return False
    if "capital" in lowered and "share" in lowered and "outstanding" not in lowered:
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
        dated = date.max
    for event_type, pattern in _CA_PATTERNS:
        if event_type not in CAPITAL_EVENT_TYPES:
            continue
        if event_type in seen:
            continue
        if pattern.search(text):
            seen.add(event_type)
            found.append(CapitalEvent(event_type, dated))
    return tuple(found)


def extract_labeled_field(text: str, field: str) -> ExtractedField | None:
    """Extract only when the document uses an allowed explicit label."""
    requested = field.strip().lower().replace(" ", "_")
    labels = _FIELD_LABELS.get(requested)
    if labels is None:
        return None
    context = parse_document_context(text)
    as_of = context.period_end or _document_as_of(text)
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
    for label in labels:
        if requested == "shares_outstanding" and not share_label_is_outstanding(label):
            continue
        pattern = re.compile(
            rf"{re.escape(label)}\s*[:=\s]\s*([-+]?\d[\d,]*(?:\.\d+)?)",
            re.I,
        )
        match = pattern.search(text)
        if match is None:
            continue
        semantic = semantic_field_status(
            requested_field=requested, document_label=label
        )
        raw = match.group(1).replace(",", "")
        if semantic != "VERIFIED":
            return ExtractedField(
                field=requested,
                value="",
                as_of=as_of,
                locator=label,
                semantic_status="UNKNOWN",
                currency=context.currency,
                raw_value=raw,
                raw_unit=context.unit_scale,
                period_end=context.period_end,
                period_type=context.period_type,
                statement_basis=context.statement_basis,
                restated=context.restated,
            )
        if requested != "shares_outstanding":
            if context.unit_multiplier is None:
                return ExtractedField(
                    field=requested,
                    value="",
                    as_of=as_of,
                    locator=label,
                    semantic_status="UNKNOWN",
                    currency=context.currency,
                    raw_value=raw,
                    raw_unit=None,
                    period_end=context.period_end,
                    period_type=context.period_type,
                    statement_basis=context.statement_basis,
                    restated=context.restated,
                )
            try:
                normalized = Decimal(raw) * context.unit_multiplier
            except (InvalidOperation, ValueError):
                return None
            value = format(normalized, "f")
        else:
            try:
                if Decimal(raw) <= 0:
                    return None
            except (InvalidOperation, ValueError):
                return None
            value = raw
        return ExtractedField(
            field=requested,
            value=value,
            as_of=as_of,
            locator=label,
            semantic_status="VERIFIED",
            currency=context.currency if requested != "shares_outstanding" else None,
            raw_value=raw,
            raw_unit=context.unit_scale,
            unit_scale="actual" if requested != "shares_outstanding" else "shares",
            period_start=context.period_start,
            period_end=context.period_end,
            period_type=context.period_type,
            statement_basis=context.statement_basis,
            restated=context.restated,
        )
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
