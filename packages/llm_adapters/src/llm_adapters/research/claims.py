"""Parse candidate claims from untrusted model text.

Grounding URLs are preferred over model-declared sources. The agent name
is never written as an authoritative source.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from uuid import uuid4

from data_engine.multi_agent_research.contracts import ResearchClaim, ResearchRequest
from data_engine.multi_agent_research.source_urls import classify_source_url
from data_engine.source_policy import SourceTier, classify_source, is_ai_agent_source

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def _extract_grounding_uris(payload: dict[str, object] | None) -> tuple[str, ...]:
    if not payload:
        return ()
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return ()
    first = candidates[0]
    if not isinstance(first, dict):
        return ()
    meta = first.get("groundingMetadata") or first.get("grounding_metadata")
    if not isinstance(meta, dict):
        return ()
    uris: list[str] = []
    chunks = meta.get("groundingChunks") or meta.get("grounding_chunks") or []
    if isinstance(chunks, list):
        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue
            web = chunk.get("web") or {}
            if isinstance(web, dict):
                uri = str(web.get("uri") or web.get("url") or "").strip()
                if uri:
                    uris.append(uri)
    return tuple(uris)


def _first_json_object(text: str) -> dict[str, object] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        match = _JSON_BLOCK.search(raw)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None


def _source_from_url(url: str) -> tuple[str, str]:
    classified = classify_source_url(url)
    if classified.tier is SourceTier.PRIMARY:
        host = classified.host
        if "nseindia" in host:
            return "nse", "PRIMARY_EXCHANGE"
        if "bseindia" in host:
            return "bse", "PRIMARY_EXCHANGE"
        if "sebi" in host:
            return "sebi", "PRIMARY_REGULATOR"
        return "company_filing", classified.host_class.value
    if classified.tier is SourceTier.SECONDARY:
        return "yahoo_finance", "SECONDARY"
    return "", classified.host_class.value


def claims_from_model_output(
    *,
    request: ResearchRequest,
    agent: str,
    text: str,
    payload: dict[str, object] | None,
    retrieved_at: datetime | None = None,
) -> tuple[ResearchClaim, ...]:
    now = retrieved_at or datetime.now(tz=UTC)
    grounding = _extract_grounding_uris(payload)
    parsed = _first_json_object(text) or {}
    field = str(
        parsed.get("field")
        or (request.requested_fields[0] if request.requested_fields else "")
    ).strip()
    value = str(parsed.get("candidate_value") or parsed.get("value") or "").strip()
    declared_source = str(parsed.get("source") or "").strip()
    declared_url = str(parsed.get("source_url") or "").strip()
    source_url = grounding[0] if grounding else declared_url
    source, source_type = _source_from_url(source_url)
    if not source:
        source = declared_source
        source_type = str(parsed.get("source_type") or "UNKNOWN")
    if is_ai_agent_source(source) or classify_source(source)[0] is SourceTier.AI_AGENT:
        source = source or agent
        source_type = "AI_AGENT"
    if not field or not value:
        return ()
    return (
        ResearchClaim(
            claim_id=f"cl_{uuid4().hex[:12]}",
            research_request_id=request.research_request_id,
            company=request.company,
            ticker=request.ticker,
            isin=request.isin,
            mic=request.mic,
            field=field,
            candidate_value=value,
            unit=str(parsed.get("unit") or ""),
            currency=str(parsed.get("currency") or ""),
            period=str(parsed.get("period") or ""),
            as_of=str(parsed.get("as_of") or request.requested_as_of),
            agent=agent,
            source=source,
            source_type=source_type,
            source_url=source_url,
            document_date=str(parsed.get("document_date") or ""),
            evidence_locator=str(parsed.get("evidence_locator") or ""),
            retrieved_at=now,
            agent_confidence=None,
            exchange=request.exchange,
        ),
    )
