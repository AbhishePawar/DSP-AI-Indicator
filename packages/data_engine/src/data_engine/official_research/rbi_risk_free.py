"""RBI risk-free *observation* acquisition. Not a WACC engine.

RBI publishes labeled interest-rate observations. EvidenceJudge verifies
those observations. DSP still calculates WACC via compute_wacc.

Canonical DCF/CAPM currently has no government-security tenor policy.
This module records POLICY_GAP and does not silently bind a T-bill,
5-year G-sec, or 10-year G-sec as the DCF risk-free rate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from time import perf_counter
from typing import Any, Callable

from data_engine.official_research.dcf_tenor_policy import (
    DCF_RISK_FREE_FRESHNESS_DAYS,
    DCF_RISK_FREE_MATURITY_POLICY,
    DCF_RISK_FREE_REQUIRED_MATURITY,
    evaluate_risk_free_binding,
)
from data_engine.official_research.documents import (
    DocumentRecord,
    RetrievalFailure,
    retrieve_approved_https,
)
from data_engine.official_research.judge import EvidenceJudge
from data_engine.official_research.models import EvidenceItem, new_evidence_id, utc_now
from data_engine.official_research.prompt_guard import sanitize_document_text
from data_engine.official_research.source_policy import classify_source_url, record_source_clash
from data_engine.security_master.models import SecurityListing

__all__ = [
    "RBI_NSDP_URL",
    "RBI_RISK_FREE_FRESHNESS_DAYS",
    "RBI_RISK_FREE_MATURITY_POLICY",
    "RBI_RISK_FREE_REQUIRED_MATURITY",
    "RbiRateObservation",
    "RbiRiskFreeResult",
    "acquire_rbi_risk_free",
    "binding_decision",
    "classify_rbi_instrument",
    "extract_rbi_interest_rates",
    "normalize_percent_per_annum",
    "observation_freshness",
    "parse_rbi_date",
]

RBI_NSDP_URL = "https://www.rbi.org.in/Scripts/BS_NSDPDisplay.aspx"
RBI_RISK_FREE_MATURITY_POLICY = DCF_RISK_FREE_MATURITY_POLICY
RBI_RISK_FREE_REQUIRED_MATURITY = DCF_RISK_FREE_REQUIRED_MATURITY
RBI_RISK_FREE_FRESHNESS_DAYS = DCF_RISK_FREE_FRESHNESS_DAYS
RBI_AGENT = "official_rbi_primary"
_ALLOWED_HTML_TYPES = frozenset(
    {"text/html", "application/xhtml+xml", "text/plain", "application/xml"}
)
_HTML_UNESCAPE = {
    "&nbsp;": " ",
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&#8377;": "INR",
}
_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}
_LABELED_ROWS: tuple[tuple[str, str], ...] = (
    ("Bank Rate", r"Bank Rate\^?\s+Per cent per annum\s+(?P<date>[A-Za-z]+/\d{1,2}/\d{4})\s+(?P<value>\d+(?:\.\d+)?)"),
    (
        "MCLR (1-Year)",
        r"MCLR \(1-Year\)\^?\s+Per cent per annum\s+(?P<date>[A-Za-z]+/\d{1,2}/\d{4})\s+(?P<value>\d+(?:\.\d+)?)",
    ),
    (
        "Treasury Bill Rates",
        r"Treasury Bill Rates\s+Per cent per annum\s+(?P<date>[A-Za-z]+/\d{1,2}/\d{4})\s+(?P<value>\d+(?:\.\d+)?)",
    ),
    (
        "Policy Repo Rate",
        r"(?:Policy\s+)?Repo Rate\s+(?:Per cent per annum\s+)?(?P<date>[A-Za-z]+/\d{1,2}/\d{4})?\s*(?P<value>\d+(?:\.\d+)?)",
    ),
    (
        "Reverse Repo Rate",
        r"Reverse Repo(?: Rate)?\s+(?:Per cent per annum\s+)?(?P<date>[A-Za-z]+/\d{1,2}/\d{4})?\s*(?P<value>\d+(?:\.\d+)?)",
    ),
    (
        "CRR",
        r"(?:Cash Reserve Ratio|CRR)\s+(?:Per cent(?: per annum)?\s+)?(?P<date>[A-Za-z]+/\d{1,2}/\d{4})?\s*(?P<value>\d+(?:\.\d+)?)",
    ),
    (
        "SLR",
        r"(?:Statutory Liquidity Ratio|SLR)\s+(?:Per cent(?: per annum)?\s+)?(?P<date>[A-Za-z]+/\d{1,2}/\d{4})?\s*(?P<value>\d+(?:\.\d+)?)",
    ),
    (
        "MSF",
        r"(?:Marginal Standing Facility|MSF)(?: Rate)?\s+(?:Per cent per annum\s+)?(?P<date>[A-Za-z]+/\d{1,2}/\d{4})?\s*(?P<value>\d+(?:\.\d+)?)",
    ),
    (
        "10-year Government Security",
        r"10[\-\s]?year (?:Government (?:of India )?Securit(?:y|ies)|G[\-\s]?Sec)(?: yield)?\s+(?:Per cent per annum\s+)?(?P<date>[A-Za-z]+/\d{1,2}/\d{4})?\s*(?P<value>\d+(?:\.\d+)?)",
    ),
    (
        "5-year Government Security",
        r"5[\-\s]?year (?:Government (?:of India )?Securit(?:y|ies)|G[\-\s]?Sec)(?: yield)?\s+(?:Per cent per annum\s+)?(?P<date>[A-Za-z]+/\d{1,2}/\d{4})?\s*(?P<value>\d+(?:\.\d+)?)",
    ),
)
_REJECTED_INSTRUMENTS = frozenset(
    {
        "bank_rate",
        "mclr",
        "repo_rate",
        "reverse_repo",
        "crr",
        "slr",
        "msf",
        "sdf",
        "policy_rate",
        "inflation",
        "cpi",
        "wpi",
        "corporate_bond",
    }
)
_GOVERNMENT_YIELD = frozenset(
    {
        "treasury_bill",
        "g_sec",
        "goi_dated_security",
    }
)


@dataclass(frozen=True, slots=True)
class RbiRateObservation:
    instrument: str
    instrument_kind: str
    maturity: str
    value: Decimal
    unit: str
    currency: str
    observation_date: date | None
    source: str
    source_url: str
    evidence_locator: str
    raw_value: str
    classification: str
    rejection_reason: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument,
            "instrument_kind": self.instrument_kind,
            "maturity": self.maturity,
            "value": str(self.value),
            "unit": self.unit,
            "currency": self.currency,
            "observation_date": None
            if self.observation_date is None
            else self.observation_date.isoformat(),
            "source": self.source,
            "source_url": self.source_url,
            "evidence_locator": self.evidence_locator,
            "raw_value": self.raw_value,
            "classification": self.classification,
            "rejection_reason": self.rejection_reason,
        }


@dataclass(frozen=True, slots=True)
class RbiRiskFreeResult:
    status: str
    field: str
    value: Decimal | None
    unit: str | None
    currency: str | None
    instrument: str | None
    maturity: str | None
    as_of: date | None
    source: str
    source_type: str
    source_url: str
    document_date: date | None
    evidence_locator: str | None
    retrieved_at: datetime | None
    identity_status: str
    semantic_status: str
    freshness_status: str
    confidence: str | None
    maturity_policy: str
    binding_status: str
    http_status: int | None
    content_type: str | None
    observations: tuple[RbiRateObservation, ...]
    evidence: tuple[EvidenceItem, ...]
    conflict: dict[str, Any] | None
    timings: dict[str, float]
    detail: str
    valuation_date: date | None = None
    wacc_input: dict[str, Any] | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "field": self.field,
            "value": None if self.value is None else str(self.value),
            "unit": self.unit,
            "currency": self.currency,
            "instrument": self.instrument,
            "maturity": self.maturity,
            "as_of": None if self.as_of is None else self.as_of.isoformat(),
            "source": self.source,
            "source_type": self.source_type,
            "source_url": self.source_url,
            "document_date": None
            if self.document_date is None
            else self.document_date.isoformat(),
            "evidence_locator": self.evidence_locator,
            "retrieved_at": None if self.retrieved_at is None else self.retrieved_at.isoformat(),
            "identity_status": self.identity_status,
            "semantic_status": self.semantic_status,
            "freshness_status": self.freshness_status,
            "confidence": self.confidence,
            "maturity_policy": self.maturity_policy,
            "binding_status": self.binding_status,
            "http_status": self.http_status,
            "content_type": self.content_type,
            "observations": [item.to_public_dict() for item in self.observations],
            "conflict": None if self.conflict is None else dict(self.conflict),
            "timings": dict(self.timings),
            "detail": self.detail,
            "valuation_date": None
            if self.valuation_date is None
            else self.valuation_date.isoformat(),
            "wacc_input": None if self.wacc_input is None else dict(self.wacc_input),
            "data_class": "OBSERVED_FACT",
        }


def classify_rbi_instrument(label: str) -> tuple[str, str]:
    """Return (instrument_kind, classification). Never relabel a policy rate as rf."""
    text = re.sub(r"\s+", " ", str(label or "")).strip().lower()
    if "reverse repo" in text:
        return "reverse_repo", "REJECTED_AS_RISK_FREE"
    if re.search(r"\brepo rate\b", text) or text.startswith("policy repo"):
        return "repo_rate", "REJECTED_AS_RISK_FREE"
    if "cash reserve" in text or re.search(r"\bcrr\b", text):
        return "crr", "REJECTED_AS_RISK_FREE"
    if "statutory liquidity" in text or re.search(r"\bslr\b", text):
        return "slr", "REJECTED_AS_RISK_FREE"
    if re.search(r"\bmsf\b", text) or "marginal standing" in text:
        return "msf", "REJECTED_AS_RISK_FREE"
    if "standing deposit" in text or re.search(r"\bsdf\b", text):
        return "sdf", "REJECTED_AS_RISK_FREE"
    if "bank rate" in text:
        return "bank_rate", "REJECTED_AS_RISK_FREE"
    if "mclr" in text:
        return "mclr", "REJECTED_AS_RISK_FREE"
    if "inflation" in text or re.search(r"\bcpi\b", text) or re.search(r"\bwpi\b", text):
        return "inflation", "REJECTED_AS_RISK_FREE"
    if "corporate bond" in text:
        return "corporate_bond", "REJECTED_AS_RISK_FREE"
    if "treasury bill" in text or re.search(r"\bt[\-\s]?bill", text):
        return "treasury_bill", "GOVERNMENT_YIELD_CANDIDATE"
    if "10-year" in text or "10 year" in text:
        return "g_sec", "GOVERNMENT_YIELD_CANDIDATE"
    if "5-year" in text or "5 year" in text:
        return "g_sec", "GOVERNMENT_YIELD_CANDIDATE"
    if "government security" in text or "g-sec" in text or "gsec" in text:
        return "g_sec", "GOVERNMENT_YIELD_CANDIDATE"
    if "dated security" in text or "goi" in text:
        return "goi_dated_security", "GOVERNMENT_YIELD_CANDIDATE"
    return "unknown", "REJECTED_AS_RISK_FREE"


def binding_decision(
    *,
    instrument_kind: str,
    maturity: str,
    required_maturity: str | None = RBI_RISK_FREE_REQUIRED_MATURITY,
    maturity_policy: str = RBI_RISK_FREE_MATURITY_POLICY,
) -> str:
    """Whether a government-yield observation may enter WACC as risk_free_rate."""
    status = evaluate_risk_free_binding(
        instrument_kind=instrument_kind,
        maturity=maturity,
        required_maturity=required_maturity,
        maturity_policy=maturity_policy,
    )
    if status == "POLICY_MISMATCH":
        return "REJECTED"
    return status


def parse_rbi_date(raw: str | None) -> date | None:
    text = str(raw or "").strip()
    if not text:
        return None
    iso = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if iso:
        try:
            return date.fromisoformat(iso.group(1))
        except ValueError:
            return None
    slash = re.search(
        r"\b([A-Za-z]+)/(\d{1,2})/(\d{4})\b",
        text,
    )
    if slash:
        month = _MONTHS.get(slash.group(1).lower())
        if month:
            try:
                return date(int(slash.group(3)), month, int(slash.group(2)))
            except ValueError:
                return None
    named = re.search(
        r"\b([A-Za-z]{3,9})\s+(\d{1,2}),\s+(\d{4})\b",
        text,
    )
    if named:
        month = _MONTHS.get(named.group(1).lower())
        if month:
            try:
                return date(int(named.group(3)), month, int(named.group(2)))
            except ValueError:
                return None
    return None


def normalize_percent_per_annum(raw: str) -> Decimal | None:
    text = str(raw or "").strip().replace(",", "")
    if not text:
        return None
    try:
        amount = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    if amount > 1:
        return amount / Decimal("100")
    return amount


def observation_freshness(
    *,
    observation_date: date | None,
    valuation_date: date,
    max_age_days: int = RBI_RISK_FREE_FRESHNESS_DAYS,
) -> str:
    """CURRENT / STALE / UNKNOWN. retrieved_at is not as_of."""
    if observation_date is None:
        return "UNKNOWN"
    if observation_date > valuation_date:
        return "REVIEW_REQUIRED"
    if (valuation_date - observation_date).days > max_age_days:
        return "STALE"
    return "CURRENT"


def _plain_text(html: str) -> str:
    text = str(html or "")
    for src, dst in _HTML_UNESCAPE.items():
        text = text.replace(src, dst)
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


def extract_rbi_interest_rates(
    document_text: str,
    *,
    source_url: str,
) -> tuple[RbiRateObservation, ...]:
    """Deterministic labeled-row extraction. No positional guessing across unknown tables."""
    cleaned = sanitize_document_text(document_text)
    plain = _plain_text(cleaned)
    found: list[RbiRateObservation] = []
    seen: set[str] = set()
    for label, pattern in _LABELED_ROWS:
        match = re.search(pattern, plain, flags=re.IGNORECASE)
        if match is None:
            continue
        raw = match.group("value")
        kind, classification = classify_rbi_instrument(label)
        if kind in seen:
            continue
        value = normalize_percent_per_annum(raw)
        if value is None:
            continue
        maturity = _maturity_for(label, kind)
        rejection = None
        if classification == "REJECTED_AS_RISK_FREE":
            rejection = f"{label} is not a DCF risk-free government-security yield"
        found.append(
            RbiRateObservation(
                instrument=label,
                instrument_kind=kind,
                maturity=maturity,
                value=value,
                unit="decimal",
                currency="INR",
                observation_date=parse_rbi_date(match.groupdict().get("date")),
                source="RBI",
                source_url=source_url,
                evidence_locator=label,
                raw_value=raw,
                classification=classification,
                rejection_reason=rejection,
            )
        )
        seen.add(kind)
    return tuple(found)


def _maturity_for(label: str, kind: str) -> str:
    lowered = label.lower()
    if "91" in lowered:
        return "91-day"
    if "182" in lowered:
        return "182-day"
    if "364" in lowered:
        return "364-day"
    if "10-year" in lowered or "10 year" in lowered:
        return "10-year"
    if "5-year" in lowered or "5 year" in lowered:
        return "5-year"
    if kind == "treasury_bill":
        return "UNSPECIFIED"
    if kind == "g_sec":
        return "UNSPECIFIED"
    return "NOT_APPLICABLE"


def _skipped(
    listing: SecurityListing,
    *,
    detail: str,
    timings: dict[str, float],
    valuation_date: date | None = None,
) -> RbiRiskFreeResult:
    return RbiRiskFreeResult(
        status="SKIPPED_MOCK",
        field="risk_free_rate",
        value=None,
        unit=None,
        currency=listing.currency,
        instrument=None,
        maturity=None,
        as_of=None,
        source="RBI",
        source_type="regulator",
        source_url=RBI_NSDP_URL,
        document_date=None,
        evidence_locator=None,
        retrieved_at=None,
        identity_status="UNKNOWN",
        semantic_status="UNKNOWN",
        freshness_status="UNKNOWN",
        confidence=None,
        maturity_policy=RBI_RISK_FREE_MATURITY_POLICY,
        binding_status=RBI_RISK_FREE_MATURITY_POLICY,
        http_status=None,
        content_type=None,
        observations=(),
        evidence=(),
        conflict=None,
        timings=timings,
        detail=detail,
        valuation_date=valuation_date,
    )


def _failure(
    listing: SecurityListing,
    *,
    status: str,
    detail: str,
    timings: dict[str, float],
    source_url: str = RBI_NSDP_URL,
    retrieved_at: datetime | None = None,
    http_status: int | None = None,
    content_type: str | None = None,
    observations: tuple[RbiRateObservation, ...] = (),
    evidence: tuple[EvidenceItem, ...] = (),
    identity_status: str = "UNKNOWN",
    semantic_status: str = "FAIL",
    freshness_status: str = "UNKNOWN",
    document_date: date | None = None,
    valuation_date: date | None = None,
    conflict: dict[str, Any] | None = None,
    as_of: date | None = None,
    instrument: str | None = None,
    maturity: str | None = None,
    value: Decimal | None = None,
    binding_status: str = "REJECTED",
) -> RbiRiskFreeResult:
    return RbiRiskFreeResult(
        status=status,
        field="risk_free_rate",
        value=value,
        unit=None if value is None else "decimal",
        currency=listing.currency,
        instrument=instrument,
        maturity=maturity,
        as_of=as_of,
        source="RBI",
        source_type="regulator",
        source_url=source_url,
        document_date=document_date,
        evidence_locator=instrument,
        retrieved_at=retrieved_at,
        identity_status=identity_status,
        semantic_status=semantic_status,
        freshness_status=freshness_status,
        confidence=None,
        maturity_policy=RBI_RISK_FREE_MATURITY_POLICY,
        binding_status=binding_status,
        http_status=http_status,
        content_type=content_type,
        observations=observations,
        evidence=evidence,
        conflict=conflict,
        timings=timings,
        detail=detail,
        valuation_date=valuation_date,
    )


def acquire_rbi_risk_free(
    listing: SecurityListing,
    *,
    valuation_date: date | None = None,
    document_text: str | None = None,
    retrieve_fn: Callable[[str], DocumentRecord | RetrievalFailure | bytes] | None = None,
    judge: EvidenceJudge | None = None,
    mode: str = "LIVE",
    claimed_value: str | None = None,
    claimed_source_url: str | None = None,
    now: datetime | None = None,
) -> RbiRiskFreeResult:
    """Retrieve the RBI NSDP interest-rate page and judge labeled observations.

    Company identity is stamped on evidence so the listing matches. The URL
    and extractor do not branch on ticker, company, or ISIN.
    """
    timings = {
        "dns_connect": 0.0,
        "http": 0.0,
        "extraction": 0.0,
        "evidence_judge": 0.0,
        "dsp_wacc": 0.0,
    }
    as_of_day = valuation_date or (now or utc_now()).date()
    if mode != "LIVE" and document_text is None and retrieve_fn is None:
        return _skipped(
            listing,
            detail="RBI HTTP skipped in MOCK unless document_text or retrieve_fn is supplied",
            timings=timings,
            valuation_date=as_of_day,
        )
    url = RBI_NSDP_URL
    claimed_url = str(claimed_source_url or "").strip()
    if claimed_url:
        claimed_class = classify_source_url(claimed_url, source_type="regulator")
        if claimed_class != "primary" or "rbi.org.in" not in claimed_url.lower():
            return _failure(
                listing,
                status="REJECTED",
                detail="AI locator is not an approved RBI URL",
                timings=timings,
                source_url=claimed_url,
                valuation_date=as_of_day,
                identity_status="FAIL",
            )
        url = claimed_url
    retrieved_at = now or utc_now()
    http_status: int | None = None
    content_type: str | None = None
    payload_text = document_text
    document_date: date | None = None
    if payload_text is None:
        t0 = perf_counter()
        record = _retrieve(url, listing=listing, retrieve_fn=retrieve_fn)
        timings["http"] = perf_counter() - t0
        timings["dns_connect"] = timings["http"]
        if isinstance(record, RetrievalFailure):
            return _failure(
                listing,
                status="UNAVAILABLE",
                detail=record.reason,
                timings=timings,
                source_url=url,
                retrieved_at=retrieved_at,
                http_status=record.http_status,
                valuation_date=as_of_day,
                identity_status="FAIL" if "unapproved" in record.reason.lower() else "UNKNOWN",
            )
        http_status = record.http_status
        content_type = record.content_type
        retrieved_at = record.retrieved_at
        if record.content_type.split(";", 1)[0].strip().lower() not in _ALLOWED_HTML_TYPES:
            return _failure(
                listing,
                status="REJECTED",
                detail=f"unexpected content type {record.content_type}",
                timings=timings,
                source_url=url,
                retrieved_at=retrieved_at,
                http_status=http_status,
                content_type=content_type,
                valuation_date=as_of_day,
            )
        payload_text = record.payload.decode("utf-8", errors="replace")
        document_date = parse_rbi_date(record.document_date) if record.document_date else None
    t1 = perf_counter()
    if document_date is None:
        document_date = parse_rbi_date(_plain_text(payload_text))
        publish = re.search(
            r"Date of Publish\s*:\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})",
            _plain_text(payload_text),
            flags=re.IGNORECASE,
        )
        if publish:
            document_date = parse_rbi_date(publish.group(1)) or document_date
    observations = extract_rbi_interest_rates(payload_text, source_url=url)
    timings["extraction"] = perf_counter() - t1
    if not observations:
        return _failure(
            listing,
            status="UNKNOWN",
            detail="no labeled RBI interest-rate observation extracted",
            timings=timings,
            source_url=url,
            retrieved_at=retrieved_at,
            http_status=http_status,
            content_type=content_type,
            document_date=document_date,
            valuation_date=as_of_day,
            semantic_status="UNKNOWN",
        )

    expected_ccy = str(listing.currency or "INR").upper()
    judged = EvidenceJudge() if judge is None else judge
    evidence_rows: list[EvidenceItem] = []
    t2 = perf_counter()
    government = tuple(
        item for item in observations if item.classification == "GOVERNMENT_YIELD_CANDIDATE"
    )
    rejected_rows = tuple(
        item for item in observations if item.classification == "REJECTED_AS_RISK_FREE"
    )
    selected = government[0] if len(government) == 1 else None
    conflict: dict[str, Any] | None = None
    if len(government) > 1:
        conflict = {
            "status": "REVIEW_REQUIRED",
            "detail": "multiple government-yield observations are not averaged",
            "instruments": [item.instrument for item in government],
        }
    for item in observations:
        evidence_rows.append(
            judged.promote(
                _observation_evidence(
                    listing,
                    item,
                    retrieved_at=retrieved_at,
                    document_date=document_date,
                    valuation_date=as_of_day,
                    expected_currency=expected_ccy,
                ),
                production=False,
            )
        )
    timings["evidence_judge"] = perf_counter() - t2

    if expected_ccy != "INR":
        return _failure(
            listing,
            status="REJECTED",
            detail="risk-free currency is INR; silent FX conversion is not performed",
            timings=timings,
            source_url=url,
            retrieved_at=retrieved_at,
            http_status=http_status,
            content_type=content_type,
            observations=observations,
            evidence=tuple(evidence_rows),
            document_date=document_date,
            valuation_date=as_of_day,
            identity_status="PASS",
            semantic_status="FAIL",
        )

    if selected is None:
        detail = (
            "RBI observations retrieved; no unique government-yield candidate"
            if government
            else "RBI page has no government-security yield that can be a risk-free input"
        )
        if rejected_rows and not government:
            detail = (
                "RBI policy/bank rates (repo, bank rate, MCLR, CRR, SLR) are not "
                "DCF risk-free inputs"
            )
        return _failure(
            listing,
            status="REJECTED" if not government else "REVIEW_REQUIRED",
            detail=detail if conflict is None else str(conflict["detail"]),
            timings=timings,
            source_url=url,
            retrieved_at=retrieved_at,
            http_status=http_status,
            content_type=content_type,
            observations=observations,
            evidence=tuple(evidence_rows),
            document_date=document_date,
            valuation_date=as_of_day,
            identity_status="PASS",
            semantic_status="FAIL" if not government else "REVIEW_REQUIRED",
            conflict=conflict,
            binding_status="REVIEW_REQUIRED" if government else "REJECTED",
        )

    freshness = observation_freshness(
        observation_date=selected.observation_date,
        valuation_date=as_of_day,
    )
    bind = binding_decision(
        instrument_kind=selected.instrument_kind,
        maturity=selected.maturity,
    )
    if selected.currency != "INR":
        return _failure(
            listing,
            status="REJECTED",
            detail="RBI observation currency is not INR",
            timings=timings,
            source_url=url,
            retrieved_at=retrieved_at,
            http_status=http_status,
            content_type=content_type,
            observations=observations,
            evidence=tuple(evidence_rows),
            document_date=document_date,
            valuation_date=as_of_day,
            identity_status="PASS",
            semantic_status="FAIL",
            instrument=selected.instrument,
            maturity=selected.maturity,
            as_of=selected.observation_date,
            value=selected.value,
        )
    if freshness == "REVIEW_REQUIRED":
        return _failure(
            listing,
            status="REJECTED",
            detail="observation_date is after valuation_date",
            timings=timings,
            source_url=url,
            retrieved_at=retrieved_at,
            http_status=http_status,
            content_type=content_type,
            observations=observations,
            evidence=tuple(evidence_rows),
            document_date=document_date,
            valuation_date=as_of_day,
            identity_status="PASS",
            semantic_status="FAIL",
            freshness_status="FAIL",
            instrument=selected.instrument,
            maturity=selected.maturity,
            as_of=selected.observation_date,
            value=selected.value,
            binding_status="REJECTED",
        )
    if freshness == "STALE":
        return _failure(
            listing,
            status="RESEARCH_REQUIRED",
            detail="STALE; RBI observation older than forensic freshness window",
            timings=timings,
            source_url=url,
            retrieved_at=retrieved_at,
            http_status=http_status,
            content_type=content_type,
            observations=observations,
            evidence=tuple(evidence_rows),
            document_date=document_date,
            valuation_date=as_of_day,
            identity_status="PASS",
            semantic_status="PASS",
            freshness_status="FAIL",
            instrument=selected.instrument,
            maturity=selected.maturity,
            as_of=selected.observation_date,
            value=selected.value,
            binding_status="REJECTED",
        )
    if freshness == "UNKNOWN":
        return _failure(
            listing,
            status="UNKNOWN",
            detail="observation date UNKNOWN; retrieved_at is not as_of",
            timings=timings,
            source_url=url,
            retrieved_at=retrieved_at,
            http_status=http_status,
            content_type=content_type,
            observations=observations,
            evidence=tuple(evidence_rows),
            document_date=document_date,
            valuation_date=as_of_day,
            identity_status="PASS",
            semantic_status="PASS",
            freshness_status="UNKNOWN",
            instrument=selected.instrument,
            maturity=selected.maturity,
            value=selected.value,
            binding_status="REVIEW_REQUIRED",
        )

    if claimed_value not in {None, ""}:
        try:
            claimed = Decimal(str(claimed_value))
        except (InvalidOperation, ValueError):
            claimed = None
        if claimed is not None and claimed != selected.value:
            conflict = record_source_clash(
                field="risk_free_rate",
                primary_url=url,
                primary_value=str(selected.value),
                research_url=claimed_url or url,
                research_value=str(claimed),
            )
            conflict["status"] = "PRIMARY_AUTHORITY_RETAINED"
            conflict["detail"] = "AI-claimed rate discarded; RBI extraction is primary"

    component = {
        "field": "risk_free_rate",
        "value": str(selected.value),
        "unit": "decimal",
        "currency": "INR",
        "instrument": selected.instrument,
        "maturity": selected.maturity,
        "as_of": None if selected.observation_date is None else selected.observation_date.isoformat(),
        "source": "RBI",
        "source_type": "regulator",
        "source_url": url,
        "document_date": None if document_date is None else document_date.isoformat(),
        "evidence_locator": selected.evidence_locator,
        "retrieved_at": retrieved_at.isoformat(),
        "identity_status": "PASS",
        "semantic_status": "PASS",
        "freshness_status": "PASS",
        "confidence": "high",
        "maturity_policy": RBI_RISK_FREE_MATURITY_POLICY,
        "binding_status": bind,
    }
    detail = (
        f"RBI {selected.instrument} is a labeled {selected.instrument_kind} yield "
        f"(maturity {selected.maturity}); DCF tenor policy is {RBI_RISK_FREE_MATURITY_POLICY}"
    )
    wacc_input = None
    status = "RETRIEVED"
    if bind == "BOUND":
        wacc_input = {
            "field": "risk_free_rate",
            "value": str(selected.value),
            "evidence_ids": tuple(item.evidence_id for item in evidence_rows if item.field == "risk_free_rate"),
        }
        status = "VERIFIED_INPUT"
        detail = f"{detail}; bound as DSP risk_free_rate input"
    else:
        detail = f"{detail}; not bound as WACC risk_free_rate"
    return RbiRiskFreeResult(
        status=status,
        field="risk_free_rate",
        value=selected.value,
        unit="decimal",
        currency="INR",
        instrument=selected.instrument,
        maturity=selected.maturity,
        as_of=selected.observation_date,
        source="RBI",
        source_type="regulator",
        source_url=url,
        document_date=document_date,
        evidence_locator=selected.evidence_locator,
        retrieved_at=retrieved_at,
        identity_status="PASS",
        semantic_status="PASS",
        freshness_status="CURRENT",
        confidence="high",
        maturity_policy=RBI_RISK_FREE_MATURITY_POLICY,
        binding_status=bind,
        http_status=http_status,
        content_type=content_type,
        observations=observations,
        evidence=tuple(evidence_rows),
        conflict=conflict,
        timings=timings,
        detail=detail,
        valuation_date=as_of_day,
        wacc_input=wacc_input,
    )


def _retrieve(
    url: str,
    *,
    listing: SecurityListing,
    retrieve_fn: Callable[[str], DocumentRecord | RetrievalFailure | bytes] | None,
) -> DocumentRecord | RetrievalFailure:
    if retrieve_fn is not None:
        result = retrieve_fn(url)
        if isinstance(result, (DocumentRecord, RetrievalFailure)):
            return result
        payload = result
        return DocumentRecord(
            url=url,
            retrieved_at=utc_now(),
            http_status=200,
            content_type="text/html",
            content_length=len(payload),
            document_hash="",
            payload=payload,
            company_isin=listing.isin,
            company_mic=listing.mic,
            final_url=url,
        )
    return retrieve_approved_https(
        url,
        isin=listing.isin,
        mic=listing.mic,
        source_type="regulator",
    )


def _observation_evidence(
    listing: SecurityListing,
    item: RbiRateObservation,
    *,
    retrieved_at: datetime,
    document_date: date | None,
    valuation_date: date,
    expected_currency: str,
) -> EvidenceItem:
    semantic_kind = item.instrument_kind
    semantic = "PASS" if item.classification == "GOVERNMENT_YIELD_CANDIDATE" else "FAIL"
    if item.currency.upper() != expected_currency:
        semantic = "FAIL"
    freshness = observation_freshness(
        observation_date=item.observation_date,
        valuation_date=valuation_date,
    )
    if freshness == "STALE":
        freshness_status = "FAIL"
        freshness_label = "STALE"
    elif freshness == "CURRENT":
        freshness_status = "PASS"
        freshness_label = "CURRENT"
    elif freshness == "REVIEW_REQUIRED":
        freshness_status = "FAIL"
        freshness_label = "REFRESH_REQUIRED"
    else:
        freshness_status = "UNKNOWN"
        freshness_label = "UNKNOWN"
    bind = binding_decision(instrument_kind=item.instrument_kind, maturity=item.maturity)
    if item.classification == "GOVERNMENT_YIELD_CANDIDATE" and bind != "BOUND":
        field = "rbi_interest_rate_observation"
        semantic_kind = item.instrument_kind
        semantic = "PASS" if semantic == "PASS" else semantic
    else:
        field = "risk_free_rate"
        semantic_kind = item.instrument_kind
        if item.classification != "GOVERNMENT_YIELD_CANDIDATE":
            semantic = "FAIL"
    return EvidenceItem(
        evidence_id=new_evidence_id(),
        company=listing.company_name,
        ticker=listing.ticker,
        isin=listing.isin,
        mic=listing.mic,
        field=field,
        value=str(item.value),
        as_of=item.observation_date,
        retrieved_at=retrieved_at,
        source="RBI",
        source_type="regulator",
        source_url=item.source_url,
        document_date=document_date or item.observation_date,
        evidence_locator=item.evidence_locator,
        currency=item.currency,
        unit=item.unit,
        statement_basis=None,
        agent=RBI_AGENT,
        identity_status="PASS",
        semantic_status=semantic,
        freshness_status=freshness_status,
        corporate_action_status="PASS",
        confidence="high",
        stage="RAW",
        status="UNKNOWN",
        mode="LIVE",
        semantic_kind=semantic_kind,
        freshness_label=freshness_label,
        authority_tier="TIER_1A",
        raw_value=item.raw_value,
        raw_unit="percent_per_annum",
    )


def merge_rbi_into_dataset_evidence(
    evidence: tuple[EvidenceItem, ...],
    rbi: RbiRiskFreeResult,
) -> tuple[EvidenceItem, ...]:
    """Append judged RBI rows. Bound risk_free_rate only if binding_status is BOUND."""
    extra = rbi.evidence
    if rbi.binding_status != "BOUND":
        extra = tuple(
            item
            for item in extra
            if not (item.field == "risk_free_rate" and item.status == "VERIFIED")
        )
    return evidence + extra
