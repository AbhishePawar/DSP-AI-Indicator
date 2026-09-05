"""Deterministic corporate-action ledger for Option B currentness.

Classifies already-retrieved exchange records. Makes no HTTP calls and
does not invent a zero-event corpus. Empty input without an explicit
exhausted date range is OPTION_B_UNPROVEN.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping

from dsp_platform.current_outstanding_protocol.currentness import (
    CorporateActionCurrentnessEvidence,
    ShareChangingCorporateAction,
)
from dsp_platform.external_evidence.models import ExternalEvidenceIdentity
from dsp_platform.external_evidence.validation import normalize_identity_token

__all__ = [
    "CorporateActionRecord",
    "ExchangeCompletenessCorpus",
    "OptionBCompletenessAttestation",
    "attest_option_b_from_exchange_corpus",
    "classify_exchange_event",
]

_ADMISSIBLE_TIERS = frozenset({"TIER_1_PRIMARY", "TIER_2_SECONDARY"})
_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
_CHANGING_TOKENS = (
    "bonus",
    "stock split",
    "split (",
    "sub-division",
    "subdivision",
    "rights ",
    "rights issue",
    "buy back",
    "buyback",
    "qip",
    "fpo",
    "preferential",
    "allotment",
    "esop",
    "demerger",
    "capital reduction",
    "fresh issue",
    "further issue",
    "new issue",
    "share swap",
    "merger",
    "conversion",
    "treasury",
    "reverse split",
    "reverse-split",
    "cancellation of share",
)
_DIVIDEND_TOKENS = (
    "dividend",
    "interim dividend",
    "special dividend",
    "interest payment",
    "distribution",
)
_NSE_NON_CAPITAL_CATEGORIES = frozenset(
    {
        "updates",
        "general updates",
        "press release",
        "copy of newspaper publication",
        "analysts/institutional investor meet/con. call updates",
        "bagging/receiving of orders/contracts",
        "news verification",
        "change in management",
        "outcome of board meeting",
        "company update",
        "result",
        "board meeting",
        "others",
        "corp action",
        "corp. action",
    }
)
_NON_CAPITAL_TOKENS = (
    "press release",
    "analyst",
    "investor meet",
    "con. call",
    "newspaper",
    "financial results",
    "board meeting",
    "transcript",
    "recording",
    "schedule of meet",
    "news verification",
    "rumour verification",
    "clarification sought",
    "bagging",
    "receiving of orders",
    "award of order",
    "receipt of order",
    "award_of_order",
    "receipt_of_order",
    "change in management",
    "general updates",
    "date of payment of dividend",
    "symbol change",
    "board announcement",
    "threat-intelligence",
    "identified shareholders",
    "hypervault",
    "depositories and participants",
    "certificate under sebi",
    "regulation 74",
    "reg 74",
    "reg. 74",
    "regulation 76",
    "shareholding pattern",
    "investor complaints",
    "reconciliation of share capital audit",
    "compliance certificate",
    "trading window",
    "code of conduct",
    "shareholders meeting",
    "annual general meeting",
    "postal ballot",
    "scrutinizer",
    "srutinizer",
    "change in director",
    "takeover regulation",
)
_SEBI_CONSIDERATION_PROMPT = re.compile(
    r"whether\s+cash\s+consideration\s+or\s+share\s+swap\s+or\s+any\s+other\s+form"
    r"(?:\s+and\s+details\s+of\s+the\s+same)?",
    re.IGNORECASE,
)
_CASH_CONSIDERATION = re.compile(
    r"\bcash\s+consideration\b|"
    r"\bconsideration\s+is\s+cash\b|"
    r"\bnature of consideration\s+cash\b|"
    r"\bconsideration\s*[:\-]\s*cash\b|"
    r"\bentirely\s+in\s+cash\b|"
    r"\bfor\s+cash\s+consideration\b|"
    r"\bpaid\s+in\s+cash\b|"
    r"\bcash[- ]only\b",
    re.IGNORECASE,
)
_COMPLETED_ACQUISITION = re.compile(
    r"\b(?:has\s+completed|completed\s+the|completes)\s+(?:the\s+)?acquisition\b",
    re.IGNORECASE,
)
_SHARE_CONSIDERATION = re.compile(
    r"\bshare\s+swap\b|"
    r"\bshare\s+consideration\b|"
    r"\bstock\s+consideration\b|"
    r"\bissue\s+of\s+(?:equity\s+)?shares\s+(?:as|of)\s+consideration\b|"
    r"\ballotment\s+of\s+equity\s+shares\s+of\s+the\s+(?:company|acquirer)\b|"
    r"\bconsideration\s+in\s+the\s+form\s+of\s+(?:equity\s+)?shares\b|"
    r"\bnew\s+shares\s+(?:will\s+be\s+)?issued\b",
    re.IGNORECASE,
)
_MIXED_CONSIDERATION = re.compile(
    r"\bcash\s+(?:and|&)\s+(?:share|stock)\b|"
    r"\bpartly\s+cash\b|"
    r"\bcombination\s+of\s+cash\s+and\b|"
    r"\bcash\s+and\s+share\s+consideration\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class CorporateActionRecord:
    issuer: str
    isin: str
    exchange: str
    mic: str
    event_type: str
    announcement_date: date | None
    effective_date: date | None
    shares_before: int | None
    shares_delta: int | None
    shares_after: int | None
    source: str
    source_url: str
    evidence_excerpt: str
    changes_outstanding_shares: bool | None


@dataclass(frozen=True, slots=True)
class ExchangeCompletenessCorpus:
    identity: ExternalEvidenceIdentity
    share_count_as_of: date
    requested_start: date
    requested_end: date
    retrieved_at: datetime
    pagination_exhausted: bool
    date_range_explicit: bool
    source_tier: str
    source_url: str
    evidence_reference: str
    corporate_actions: tuple[Mapping[str, Any], ...]
    announcements: tuple[Mapping[str, Any], ...] = ()
    equivalent_isins: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OptionBCompletenessAttestation:
    proven: bool
    reason: str
    evidence: CorporateActionCurrentnessEvidence | None
    ledger: tuple[CorporateActionRecord, ...] = ()


def classify_exchange_event(blob: str) -> tuple[str, bool | None]:
    """Return (event_type, changes_outstanding) or unknown (type, None)."""
    text = " ".join(str(blob or "").casefold().split())
    if not text:
        return ("unclassified", None)
    if (
        "takeover regulation" in text
        or "regulation 31(4)" in text
        or "regulation 31 (4)" in text
    ):
        return ("non_capital_disclosure", False)
    if "acquisition" in text:
        return _classify_acquisition(text)
    if any(token in text for token in _CHANGING_TOKENS):
        if "buy back" in text or "buyback" in text:
            if "extinguish" in text or "cancellation" in text:
                return ("buyback_extinguishment", True)
            return ("buyback", True)
        if "bonus" in text:
            return ("bonus_issue", True)
        if "reverse split" in text or "reverse-split" in text:
            return ("reverse_split", True)
        if "split" in text or "sub-division" in text or "subdivision" in text:
            return ("stock_split", True)
        if "rights" in text:
            return ("rights_issue", True)
        if "demerger" in text:
            return ("demerger", True)
        if "merger" in text:
            return ("merger", True)
        if "conversion" in text:
            return ("conversion", True)
        if "treasury" in text:
            return ("treasury", True)
        if "cancellation of share" in text:
            return ("cancellation", True)
        if "new issue" in text or "fresh issue" in text or "further issue" in text:
            return ("new_issue", True)
        if "allotment" in text or "esop" in text:
            return ("allotment", True)
        return ("share_capital_change", True)
    if any(token in text for token in _DIVIDEND_TOKENS):
        return ("dividend", False)
    if "symbol change" in text or "change in symbol" in text:
        return ("symbol_change", False)
    if "board announcement" in text:
        return ("board_announcement", False)
    if any(token in text for token in _NON_CAPITAL_TOKENS):
        return ("non_capital_disclosure", False)
    if any(
        text == category or text.startswith(f"{category} ")
        for category in _NSE_NON_CAPITAL_CATEGORIES
    ):
        return ("non_capital_disclosure", False)
    return ("unclassified", None)


def attest_option_b_from_exchange_corpus(
    corpus: ExchangeCompletenessCorpus,
) -> OptionBCompletenessAttestation:
    """Build Option B evidence from an exhausted T1/T2 exchange corpus."""
    if not isinstance(corpus.retrieved_at, datetime) or corpus.retrieved_at.tzinfo is None:
        return OptionBCompletenessAttestation(
            proven=False,
            reason="retrieved_at must be timezone-aware and is not as_of",
            evidence=None,
        )
    if not corpus.date_range_explicit:
        return OptionBCompletenessAttestation(
            proven=False,
            reason="exchange corpus does not expose an explicit date range",
            evidence=None,
        )
    if not corpus.pagination_exhausted:
        return OptionBCompletenessAttestation(
            proven=False,
            reason="exchange corpus pagination was not exhausted",
            evidence=None,
        )
    if corpus.requested_end < corpus.retrieved_at.date():
        return OptionBCompletenessAttestation(
            proven=False,
            reason="requested_end does not cover retrieved_at; Option B currentness is unproven",
            evidence=None,
        )
    if str(corpus.source_tier or "").strip() not in _ADMISSIBLE_TIERS:
        return OptionBCompletenessAttestation(
            proven=False,
            reason="corporate-action evidence is not an admissible source tier",
            evidence=None,
        )
    if not str(corpus.source_url or "").strip():
        return OptionBCompletenessAttestation(
            proven=False,
            reason="corporate-action evidence source_url is required",
            evidence=None,
        )
    if not str(corpus.evidence_reference or "").strip():
        return OptionBCompletenessAttestation(
            proven=False,
            reason="corporate-action evidence_reference is required",
            evidence=None,
        )
    wanted_symbol = normalize_identity_token(corpus.identity.symbol)
    wanted_isin = normalize_identity_token(corpus.identity.isin)
    equivalent = tuple(
        normalize_identity_token(item) for item in corpus.equivalent_isins if item
    )
    ledger: list[CorporateActionRecord] = []
    events: list[ShareChangingCorporateAction] = []
    for raw in corpus.corporate_actions:
        if not isinstance(raw, Mapping):
            return _unproven("corporate-action record is not an object")
        if not _identity_matches(
            raw,
            wanted_symbol=wanted_symbol,
            wanted_isin=wanted_isin,
            equivalent_isins=equivalent,
        ):
            return _unproven("corporate-action identity does not match the requested instrument")
        subject = str(raw.get("subject") or raw.get("desc") or "")
        event_type, changes = classify_exchange_event(subject)
        if changes is None:
            return _unproven(
                f"corporate-action type {event_type!r} is not classified"
            )
        effective = _parse_exchange_date(
            raw.get("exDate") or raw.get("recDate") or raw.get("effective_date")
        )
        record = CorporateActionRecord(
            issuer=str(raw.get("comp") or raw.get("sm_name") or corpus.identity.company_name or ""),
            isin=str(raw.get("isin") or raw.get("sm_isin") or wanted_isin),
            exchange=str(corpus.identity.exchange or ""),
            mic=str(corpus.identity.mic or ""),
            event_type=event_type,
            announcement_date=_parse_exchange_date(raw.get("an_dt") or raw.get("caBroadcastDate")),
            effective_date=effective,
            shares_before=None,
            shares_delta=None,
            shares_after=None,
            source="nse_corporate_actions",
            source_url=corpus.source_url,
            evidence_excerpt=subject,
            changes_outstanding_shares=changes,
        )
        ledger.append(record)
        events.append(
            ShareChangingCorporateAction(
                action_type=event_type,
                effective_date=effective,
                changes_outstanding_shares=changes,
                already_reflected_in_share_count=False,
                description=subject,
            )
        )
    for raw in corpus.announcements:
        if not isinstance(raw, Mapping):
            return _unproven("announcement record is not an object")
        if not _identity_matches(
            raw,
            wanted_symbol=wanted_symbol,
            wanted_isin=wanted_isin,
            equivalent_isins=equivalent,
        ):
            return _unproven("announcement identity does not match the requested instrument")
        blob = " ".join(
            str(raw.get(key) or "")
            for key in (
                "desc",
                "attchmntText",
                "NEWSSUB",
                "MORE",
                "filing_excerpt",
                "subject",
                "attachment_text",
            )
        )
        event_type, changes = classify_exchange_event(blob)
        if changes is None:
            return _unproven(
                f"announcement type {event_type!r} is not classified"
            )
        if changes is False:
            continue
        effective = _parse_exchange_date(
            raw.get("an_dt") or raw.get("NEWS_DT") or raw.get("effective_date")
        )
        events.append(
            ShareChangingCorporateAction(
                action_type=event_type,
                effective_date=effective,
                changes_outstanding_shares=True,
                already_reflected_in_share_count=False,
                description=blob[:240],
            )
        )
    evidence = CorporateActionCurrentnessEvidence(
        events=tuple(events),
        complete_through=corpus.requested_end,
        share_count_as_of=corpus.share_count_as_of,
        source_tier=str(corpus.source_tier).strip(),
        source_url=corpus.source_url,
        evidence_reference=corpus.evidence_reference,
    )
    return OptionBCompletenessAttestation(
        proven=True,
        reason="exhausted exchange corpus classified with no unreconciled share-count event",
        evidence=evidence,
        ledger=tuple(ledger),
    )


def _unproven(reason: str) -> OptionBCompletenessAttestation:
    return OptionBCompletenessAttestation(proven=False, reason=reason, evidence=None)


def _classify_acquisition(text: str) -> tuple[str, bool | None]:
    stripped = " ".join(_SEBI_CONSIDERATION_PROMPT.sub(" ", text).split())
    mixed = bool(_MIXED_CONSIDERATION.search(stripped))
    cash = bool(_CASH_CONSIDERATION.search(stripped))
    share = bool(_SHARE_CONSIDERATION.search(stripped))
    if mixed or (cash and share):
        return ("acquisition_mixed_consideration", True)
    if cash:
        return ("acquisition_cash", False)
    if share:
        return ("acquisition_share_consideration", True)
    if _COMPLETED_ACQUISITION.search(stripped) and "is subject" not in stripped:
        return ("acquisition_completion", False)
    return ("acquisition_unresolved", None)


def _identity_matches(
    raw: Mapping[str, Any],
    *,
    wanted_symbol: str,
    wanted_isin: str,
    equivalent_isins: tuple[str, ...] = (),
) -> bool:
    symbol = normalize_identity_token(
        raw.get("symbol") or raw.get("bm_symbol") or raw.get("SecurityId")
    )
    isin = normalize_identity_token(
        raw.get("isin") or raw.get("sm_isin") or raw.get("ISIN")
    )
    accepted = {wanted_isin, *(item for item in equivalent_isins if item)}
    accepted.discard("")
    if symbol and symbol != wanted_symbol:
        return False
    if isin and wanted_isin and isin not in accepted:
        return False
    return True


def _parse_exchange_date(value: object) -> date | None:
    text = str(value or "").strip()
    if not text or text in {"-", "None", "none"}:
        return None
    if "T" in text:
        text = text.split("T", 1)[0]
    if " " in text and text[0].isdigit():
        text = text.split(" ", 1)[0]
    try:
        return date.fromisoformat(text)
    except ValueError:
        pass
    parts = text.replace(",", "").split("-")
    if len(parts) == 3 and parts[1].isalpha():
        day = int(parts[0])
        month = _MONTHS.get(parts[1][:3].casefold())
        year = int(parts[2])
        if month:
            return date(year, month, day)
    return None
