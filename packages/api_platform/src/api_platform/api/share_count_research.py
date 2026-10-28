"""Evidence-grounded share-count fallback using official NSE data and AI adapters.

This adapter is invoked only when the authenticated quote provider omits shares.
The models may interpret a retrieved official record; they cannot supply an
unsupported number. Any retrieval, citation, freshness, or agreement failure
returns None so the valuation path remains fail-closed.
"""
from __future__ import annotations

import http.cookiejar
import json
import math
import re
from datetime import date, datetime
from typing import Any
from urllib.parse import quote
from urllib.request import HTTPCookieProcessor, Request, build_opener

from dsp_platform import ShareCountResearchEvidence
from llm_adapters import AdapterBackedAIProvider, build_default_registry

_NSE_HOME = "https://www.nseindia.com/"
_NSE_API = "https://www.nseindia.com/api/quote-equity"
_MAX_RESPONSE_BYTES = 256_000
_MAX_AGE_DAYS = 120
_COUNT_KEYS = (
    "issuedSize",
    "totalNoOfShares",
    "totalNumberOfShares",
    "totalSharesOutstanding",
    "totalEquityShares",
    "totalPaidUpEquityShares",
)


def _fetch_nse_record(symbol: str) -> tuple[str, str] | None:
    """Return bounded official NSE JSON and its exact source URL."""
    ticker = symbol.strip().upper()
    if not re.fullmatch(r"[A-Z0-9&._-]{1,32}", ticker):
        return None
    jar = http.cookiejar.CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; DSP-AI-Indicator/1.0; research)",
        "Accept": "application/json,text/plain,*/*",
        "Referer": _NSE_HOME,
        "Connection": "close",
    }
    try:
        warm = Request(_NSE_HOME, headers={**headers, "Accept": "text/html,*/*"})
        with opener.open(warm, timeout=8) as response:
            response.read(256_000)
        url = f"{_NSE_API}?symbol={quote(ticker, safe='')}"
        req = Request(url, headers=headers)
        with opener.open(req, timeout=8) as response:
            if response.geturl().split("?", 1)[0] != _NSE_API:
                return None
            raw = response.read(_MAX_RESPONSE_BYTES + 1)
        if len(raw) > _MAX_RESPONSE_BYTES:
            return None
        text = raw.decode("utf-8", errors="strict")
        payload = json.loads(text)
        if not isinstance(payload, dict) or not payload:
            return None
        info = payload.get("info")
        security = payload.get("securityInfo")
        metadata = payload.get("metadata")
        if (
            not isinstance(info, dict)
            or str(info.get("symbol") or "").upper() != ticker
        ):
            return None
        if not isinstance(security, dict) or not isinstance(metadata, dict):
            return None
        issued_size = security.get("issuedSize")
        if isinstance(issued_size, bool) or not isinstance(issued_size, (int, float)):
            return None
        if not math.isfinite(float(issued_size)) or float(issued_size) <= 0:
            return None
        if not _as_date(metadata.get("lastUpdateTime")):
            return None
        return text, url
    except Exception:  # noqa: BLE001 - external source must fail closed
        return None


def _json_completion(
    provider: AdapterBackedAIProvider, prompt: str
) -> dict[str, Any] | None:
    try:
        result = provider.complete(
            prompt_parts=(prompt,),
            evidence_catalog=(),
        )
        if result.status != "complete" or not result.text:
            return None
        text = result.text.strip()
        if text.startswith("```"):
            text = re.sub(r"^\`\`\`(?:json)?\s*|\s*\`\`\`$", "", text, flags=re.I)
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except Exception:  # noqa: BLE001 - provider failures must not interrupt analysis
        return None


def _as_date(value: Any) -> date | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        pass
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _evidence_is_grounded(
    result: dict[str, Any],
    source_text: str,
    ticker: str,
    expected_as_of: date | None = None,
) -> tuple[float, date] | None:
    if str(result.get("ticker") or "").strip().upper() != ticker:
        return None
    excerpt = result.get("evidence_excerpt")
    if not isinstance(excerpt, str) or len(excerpt.strip()) < 8:
        return None
    excerpt = excerpt.strip()
    if excerpt not in source_text:
        return None
    # Require an explicit company-level total-share field in the quoted source.
    key_pattern = "|".join(re.escape(key) for key in _COUNT_KEYS)
    match = re.search(
        rf'(?i)(?:{key_pattern})["\']?\s*[:=]\s*["\']?([0-9][0-9,]*(?:\.\d+)?)',
        excerpt,
    )
    if not match:
        return None
    try:
        quoted_count = float(match.group(1).replace(",", ""))
        model_count = float(result.get("shares_outstanding"))
    except (TypeError, ValueError):
        return None
    if (
        isinstance(result.get("shares_outstanding"), bool)
        or not math.isfinite(quoted_count)
        or not math.isfinite(model_count)
        or quoted_count <= 0
        or model_count <= 0
        or abs(model_count - quoted_count) / quoted_count > 0.000001
    ):
        return None
    as_of = _as_date(result.get("as_of"))
    if (
        as_of is None
        or as_of > date.today()
        or (date.today() - as_of).days > _MAX_AGE_DAYS
        or (expected_as_of is not None and as_of != expected_as_of)
    ):
        return None
    return quoted_count, as_of


def build_share_count_researcher():
    """Build a callback around configured Gemini/OpenAI adapters, or return None."""
    try:
        registry = build_default_registry()
        if registry.config.provider_mode == "deterministic":
            return None
        gemini = registry.get("gemini")
        openai = registry.get("openai")
        if (
            gemini is None
            or openai is None
            or not gemini.is_configured()
            or not openai.is_configured()
        ):
            return None
        providers = (
            AdapterBackedAIProvider(gemini),
            AdapterBackedAIProvider(openai),
        )
    except Exception:  # noqa: BLE001 - optional AI adapters are not mandatory to boot
        return None

    def research(ticker: str, company_name: str | None, exchange: str | None):
        symbol = ticker.strip().upper()
        fetched = _fetch_nse_record(symbol)
        if fetched is None:
            return None
        source_text, source_url = fetched
        try:
            source_payload = json.loads(source_text)
            source_date = _as_date(
                (source_payload.get("metadata") or {}).get("lastUpdateTime")
            )
            source_count = (source_payload.get("securityInfo") or {}).get("issuedSize")
        except (TypeError, ValueError, AttributeError):
            return None
        if source_date is None or source_count is None:
            return None
        # Avoid sending an unbounded source payload to an LLM.
        prompt = (
            "Read the official NSE quote-equity JSON below. The authoritative field "
            "for issued equity shares is securityInfo.issuedSize. Return that exact "
            "number, not market cap, promoter shares, weighted-average EPS shares, "
            "or fully diluted shares. Return JSON only with keys ticker, "
            "shares_outstanding, as_of, evidence_excerpt. evidence_excerpt MUST be "
            "copied verbatim from the JSON and include the exact issuedSize key and "
            "numeric value. as_of must match metadata.lastUpdateTime's calendar date. "
            "If the field is absent or ambiguous, return null for shares_outstanding.\n"
            f"Expected ticker: {symbol}\nCompany: {company_name or 'unknown'}\n"
            f"Exchange: {exchange or 'NSE'}\nSource URL: {source_url}\n"
            f"Source JSON:\n{source_text}"
        )
        parsed = [_json_completion(provider, prompt) for provider in providers]
        if any(item is None for item in parsed):
            return None
        grounded = [
            _evidence_is_grounded(item, source_text, symbol, source_date)
            if item is not None
            else None
            for item in parsed
        ]
        valid = [item for item in grounded if item is not None]
        if not valid:
            return None
        # The official field is deterministic; one AI verifier may be unavailable
        # (e.g. provider quota). If both return grounded evidence, they must agree.
        count_a, date_a = valid[0]
        if abs(count_a - float(source_count)) > 0.000001:
            return None
        if len(valid) > 1:
            count_b, date_b = valid[1]
            if (
                date_a != date_b
                or abs(count_a - count_b) / max(count_a, count_b) > 0.000001
            ):
                return None
        return ShareCountResearchEvidence(
            ticker=symbol,
            shares_outstanding=count_a,
            source=(
                "NSE quote-equity securityInfo.issuedSize; "
                "independently verified by Gemini and OpenAI"
            ),
            evidence_url=source_url,
            as_of=date_a.isoformat(),
        )

    return research


__all__ = ["build_share_count_researcher"]
