"""Deterministic validation of Gemini share-research output."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlparse

from dsp_platform.current_outstanding_protocol.ledger import classify_exchange_event
from dsp_platform.share_count_refresh import InstrumentIdentity
from dsp_platform.share_research.models import (
    ShareResearchCheck,
    ShareResearchCorporateAction,
    ShareResearchSource,
)
from dsp_platform.share_research.policy import classify_source_url

__all__ = [
    "ValidatedGeminiResearch",
    "parse_gemini_payload",
    "validate_gemini_research",
]

_FORBIDDEN_CLAIM = (
    "weighted average",
    "free float",
    "free-float",
    "authorized share",
    "authorised share",
    "market cap",
    "implied shares",
    "diluted shares",
    "intrinsic value",
    "margin of safety",
    "discounted cash",
    "investment recommendation",
    "buy/sell",
)
_EQUIVALENT_MIC = frozenset({"XNSE", "XBOM"})


class ValidatedGeminiResearch:
    def __init__(
        self,
        *,
        shares: Decimal | None,
        as_of: date | None,
        claimed_current_through: date | None,
        sources: tuple[ShareResearchSource, ...],
        actions: tuple[ShareResearchCorporateAction, ...],
        identity_check: ShareResearchCheck,
        cross_check: ShareResearchCheck,
        corporate_action_check: ShareResearchCheck,
        issues: tuple[str, ...],
        evidence: tuple[str, ...],
        confidence: str,
        share_count_effect: str,
        ca_coverage_start: date | None,
        ca_coverage_end: date | None,
        ca_pagination_exhausted: bool,
        company: str,
        ticker: str,
        isin: str,
        exchange: str,
        mic: str,
    ) -> None:
        self.shares = shares
        self.as_of = as_of
        self.claimed_current_through = claimed_current_through
        self.sources = sources
        self.actions = actions
        self.identity_check = identity_check
        self.cross_check = cross_check
        self.corporate_action_check = corporate_action_check
        self.issues = issues
        self.evidence = evidence
        self.confidence = confidence
        self.share_count_effect = share_count_effect
        self.ca_coverage_start = ca_coverage_start
        self.ca_coverage_end = ca_coverage_end
        self.ca_pagination_exhausted = ca_pagination_exhausted
        self.company = company
        self.ticker = ticker
        self.isin = isin
        self.exchange = exchange
        self.mic = mic


def parse_gemini_payload(raw: object) -> dict[str, Any] | None:
    if isinstance(raw, Mapping):
        return {str(key).upper(): value for key, value in raw.items()}
    text = str(raw or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return {str(key).upper(): value for key, value in payload.items()}


def validate_gemini_research(
    payload: Mapping[str, Any],
    *,
    identity: InstrumentIdentity,
    extra_issuer_hosts: frozenset[str],
) -> ValidatedGeminiResearch:
    issues: list[str] = []
    claimed_company = str(_get(payload, "COMPANY") or "").strip()
    company = claimed_company or identity.issuer or identity.symbol
    ticker = str(_get(payload, "TICKER") or "").strip().upper()
    isin = str(_get(payload, "ISIN") or "").strip().upper()
    exchange = str(_get(payload, "EXCHANGE") or "").strip().upper()
    mic = str(_get(payload, "MIC") or "").strip().upper()
    identity_check = _identity_check(
        identity,
        ticker=ticker,
        isin=isin,
        exchange=exchange,
        mic=mic,
        company=claimed_company,
        issues=issues,
    )
    shares = _parse_shares(_get(payload, "OUTSTANDING_SHARES"), issues)
    as_of = _parse_date(_get(payload, "AS_OF"), issues, field="AS_OF")
    claimed_through = _parse_date(
        _get(payload, "CURRENT_THROUGH"), issues, field="CURRENT_THROUGH"
    )
    urls = _collect_urls(payload)
    sources = tuple(
        _source_from_url(url, extra_issuer_hosts=extra_issuer_hosts) for url in urls
    )
    accepted = [row for row in sources if row.accepted]
    rejected = [row for row in sources if not row.accepted]
    if rejected:
        issues.append("secondary or unapproved sources were rejected")
    if len(accepted) < 1:
        issues.append("no approved primary source URL")
        cross = ShareResearchCheck.FAIL
    elif len(accepted) < 2:
        issues.append("cross-check requires a second approved primary source")
        cross = ShareResearchCheck.FAIL
    else:
        cross = ShareResearchCheck.PASS
    blob = " ".join(str(item) for item in (_get(payload, "EVIDENCE") or ()))
    lowered = blob.casefold()
    if any(token in lowered for token in _FORBIDDEN_CLAIM):
        issues.append("claim language is not current outstanding shares")
        shares = None
    actions, ca_check, effect = _actions_from_payload(payload, issues)
    evidence = tuple(
        str(item) for item in _as_list(_get(payload, "EVIDENCE")) if str(item).strip()
    )
    coverage_start = _parse_date(_get(payload, "CA_COVERAGE_START"), issues, field="CA_COVERAGE_START")
    coverage_end = _parse_date(_get(payload, "CA_COVERAGE_END"), issues, field="CA_COVERAGE_END")
    exhausted = _truthy(_get(payload, "CA_PAGINATION_EXHAUSTED"))
    confidence = str(_get(payload, "CONFIDENCE") or "LOW").strip().upper() or "LOW"
    return ValidatedGeminiResearch(
        shares=shares,
        as_of=as_of,
        claimed_current_through=claimed_through,
        sources=sources,
        actions=actions,
        identity_check=identity_check,
        cross_check=cross,
        corporate_action_check=ca_check,
        issues=tuple(issues),
        evidence=evidence,
        confidence=confidence if confidence in {"HIGH", "MEDIUM", "LOW"} else "LOW",
        share_count_effect=effect,
        ca_coverage_start=coverage_start,
        ca_coverage_end=coverage_end,
        ca_pagination_exhausted=exhausted,
        company=company,
        ticker=ticker or identity.symbol,
        isin=isin or identity.isin,
        exchange=exchange or identity.exchange,
        mic=mic or identity.mic,
    )


def _identity_check(
    identity: InstrumentIdentity,
    *,
    ticker: str,
    isin: str,
    exchange: str,
    mic: str,
    company: str,
    issues: list[str],
) -> ShareResearchCheck:
    wanted_ticker = identity.symbol.strip().upper()
    wanted_isin = identity.isin.strip().upper()
    wanted_exchange = identity.exchange.strip().upper()
    wanted_mic = identity.mic.strip().upper()
    if ticker and ticker != wanted_ticker:
        issues.append("Gemini ticker does not match requested identity")
        return ShareResearchCheck.FAIL
    if isin and isin != wanted_isin:
        issues.append("Gemini ISIN does not match requested identity")
        return ShareResearchCheck.FAIL
    if mic and wanted_mic and not _mics_ok(mic, wanted_mic):
        issues.append("Gemini MIC does not match requested identity")
        return ShareResearchCheck.FAIL
    if (
        exchange
        and wanted_exchange
        and exchange != wanted_exchange
        and not _mics_ok(
            mic or wanted_mic,
            wanted_mic,
        )
    ):
        issues.append("Gemini exchange does not match requested identity")
        return ShareResearchCheck.FAIL
    if not _company_tokens_match(company, identity.issuer):
        issues.append("Gemini company does not match requested identity")
        return ShareResearchCheck.FAIL
    if not wanted_isin:
        issues.append("requested identity is missing ISIN")
        return ShareResearchCheck.FAIL
    return ShareResearchCheck.PASS


_COMPANY_STOPWORDS = frozenset(
    {
        "limited",
        "ltd",
        "inc",
        "corp",
        "corporation",
        "plc",
        "the",
        "and",
        "of",
        "company",
        "services",
        "industries",
        "bank",
    }
)


def _company_tokens(text: str) -> set[str]:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
    return {
        token
        for token in cleaned.split()
        if len(token) >= 4 and token not in _COMPANY_STOPWORDS
    }


def _company_tokens_match(claimed: str, issuer: str) -> bool:
    if not claimed.strip() or not issuer.strip():
        return True
    left = _company_tokens(claimed)
    right = _company_tokens(issuer)
    if not left or not right:
        return True
    return bool(left & right)


def _mics_ok(left: str, right: str) -> bool:
    if left == right:
        return True
    return {left, right} <= _EQUIVALENT_MIC


def _actions_from_payload(
    payload: Mapping[str, Any], issues: list[str]
) -> tuple[tuple[ShareResearchCorporateAction, ...], ShareResearchCheck, str]:
    raw = _get(payload, "CORPORATE_ACTIONS_FOUND") or ()
    if raw in (None, "", "NONE", "none"):
        raw = ()
    rows = _as_list(raw)
    actions: list[ShareResearchCorporateAction] = []
    unresolved = False
    changing = False
    for item in rows:
        if isinstance(item, str):
            blob = item
            consideration = None
            effective = None
        elif isinstance(item, Mapping):
            blob = str(
                item.get("description")
                or item.get("DESCRIPTION")
                or item.get("subject")
                or ""
            )
            consideration = str(
                item.get("consideration") or item.get("CONSIDERATION") or ""
            ) or None
            effective = _parse_date(
                item.get("effective_date") or item.get("EFFECTIVE_DATE"),
                issues,
                field="effective_date",
            )
            if consideration:
                blob = f"{blob} {consideration}"
        else:
            continue
        kind, changes = classify_exchange_event(blob)
        if changes is None:
            unresolved = True
        if changes is True:
            changing = True
        actions.append(
            ShareResearchCorporateAction(
                action_type=kind,
                description=blob,
                effective_date=effective,
                changes_outstanding_shares=changes,
                consideration=consideration,
            )
        )
    if unresolved:
        issues.append("corporate action remains unclassified or consideration unknown")
        return tuple(actions), ShareResearchCheck.UNRESOLVED, "UNRESOLVED"
    if changing:
        return tuple(actions), ShareResearchCheck.PASS, "SHARE_COUNT_CHANGING"
    return tuple(actions), ShareResearchCheck.PASS, "NONE"


def _source_from_url(
    url: str, *, extra_issuer_hosts: frozenset[str]
) -> ShareResearchSource:
    accepted, reason = classify_source_url(url, extra_issuer_hosts=extra_issuer_hosts)
    host = (urlparse(url).hostname or "").lower()
    return ShareResearchSource(
        url=url, label=host or url, accepted=accepted, reason=reason
    )


def _collect_urls(payload: Mapping[str, Any]) -> tuple[str, ...]:
    found: list[str] = []
    for key in (
        "SOURCE_URLS",
        "NEW_PRIMARY_SOURCE_1",
        "NEW_PRIMARY_SOURCE_2",
        "CA_SOURCE_URL",
        "STORED_SOURCE",
    ):
        for item in _as_list(_get(payload, key)):
            if isinstance(item, Mapping):
                text = str(item.get("url") or item.get("URL") or "").strip()
            else:
                text = str(item or "").strip()
            if text.startswith("https://") and text not in found:
                found.append(text)
    return tuple(found)


def _parse_shares(raw: object, issues: list[str]) -> Decimal | None:
    if raw in (None, "", "null", "NULL"):
        return None
    try:
        value = Decimal(str(raw).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        issues.append("outstanding shares are malformed")
        return None
    if not value.is_finite() or value <= 0 or value != value.to_integral_value():
        issues.append("outstanding shares must be a positive whole number")
        return None
    return value


def _parse_date(raw: object, issues: list[str], *, field: str) -> date | None:
    if raw in (None, "", "null", "NULL"):
        return None
    text = str(raw).strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        issues.append(f"{field} is not an ISO date")
        return None


def _get(payload: Mapping[str, Any], key: str) -> object:
    if key in payload:
        return payload[key]
    return payload.get(key)


def _as_list(raw: object) -> list[object]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, (list, tuple)):
        return list(raw)
    return [raw]


def _truthy(raw: object) -> bool:
    if isinstance(raw, bool):
        return raw
    return str(raw or "").strip().lower() in {"true", "yes", "1"}
