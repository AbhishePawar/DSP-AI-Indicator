"""Parse Gemini generateContent grounding metadata.

Official REST fields (v1beta GenerateContentResponse):

- tools[].googleSearch — current Google Search grounding tool
- tools[].googleSearchRetrieval — older Gemini 1.5 retrieval tool
- candidates[].groundingMetadata.groundingChunks[].web.uri
- candidates[].groundingMetadata.webSearchQueries

This module does not call HTTP, import vendor SDKs, or construct
ShareCountSnapshot / CanonicalAIDraft.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

__all__ = [
    "GOOGLE_SEARCH_RETRIEVAL_TOOL",
    "GOOGLE_SEARCH_TOOL",
    "GroundedCitation",
    "GroundedWebResearchResult",
    "google_search_tool_for_model",
    "parse_grounded_web_research",
    "parse_json_object",
    "untrusted_extraction_from_grounded_web_research",
]

# Official Tool JSON representation (camelCase REST).
GOOGLE_SEARCH_TOOL: dict[str, dict[str, Any]] = {"googleSearch": {}}
GOOGLE_SEARCH_RETRIEVAL_TOOL: dict[str, dict[str, Any]] = {
    "googleSearchRetrieval": {}
}

_FENCE = re.compile(
    r"```(?:json)?\s*(.*?)\s*```",
    re.IGNORECASE | re.DOTALL,
)

_CLAIM_KEYS = (
    "company_identity",
    "company",
    "ticker",
    "exchange",
    "shares_outstanding",
    "claimed_share_count",
    "unit",
    "as_of",
    "as_of_date",
    "source_name",
    "source_url",
    "source_reference",
    "source_type",
    "evidence_excerpt",
    "supporting_excerpt",
    "evidence_reference",
    "retrieved_at",
    "fact_id",
    "claim_type",
    "explanation",
)


@dataclass(frozen=True, slots=True)
class GroundedCitation:
    """Provider-neutral web citation copied from groundingChunks."""

    uri: str
    title: str = ""


@dataclass(frozen=True, slots=True)
class GroundedWebResearchResult:
    """Server-internal grounded parse. Never a public client DTO."""

    status: str
    narrative_text: str | None
    structured: Mapping[str, Any] | None
    citations: tuple[GroundedCitation, ...]
    web_search_queries: tuple[str, ...]
    missing_citations: bool
    malformed: bool
    limitations: tuple[str, ...] = ()

    def to_private_dict(self) -> dict[str, Any]:
        """Operator/test view. Omits credentials, prompts, tokens, model."""
        return {
            "status": self.status,
            "has_narrative": bool(self.narrative_text),
            "has_structured": self.structured is not None,
            "citation_count": len(self.citations),
            "missing_citations": self.missing_citations,
            "malformed": self.malformed,
            "limitations": list(self.limitations),
        }


def google_search_tool_for_model(model_label: str) -> dict[str, dict[str, Any]]:
    """Select the documented Google Search tool for the configured model."""
    label = (model_label or "").strip().lower()
    if "1.5" in label:
        return dict(GOOGLE_SEARCH_RETRIEVAL_TOOL)
    return dict(GOOGLE_SEARCH_TOOL)


def parse_json_object(text: str | None) -> Mapping[str, Any] | None:
    """Parse a JSON object from model text. Fail closed on non-objects."""
    if text is None:
        return None
    raw = text.strip()
    if not raw:
        return None
    fenced = _FENCE.search(raw)
    if fenced is not None:
        raw = fenced.group(1).strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, Mapping):
        return dict(parsed)
    if isinstance(parsed, list):
        return {"web_claims": parsed}
    return None


def parse_grounded_web_research(
    payload: object,
    *,
    narrative_text: str | None,
    status: str,
    limitations: Sequence[str] = (),
) -> GroundedWebResearchResult:
    """Copy citations and structured JSON. Does not invent share counts."""
    citations = _citations_from_payload(payload)
    queries = _web_search_queries(payload)
    structured = parse_json_object(narrative_text)
    malformed = bool(narrative_text) and structured is None
    missing = len(citations) == 0
    if malformed:
        status = "malformed"
    return GroundedWebResearchResult(
        status=status,
        narrative_text=narrative_text,
        structured=structured,
        citations=citations,
        web_search_queries=queries,
        missing_citations=missing,
        malformed=malformed,
        limitations=tuple(str(item) for item in limitations if str(item).strip()),
    )


def untrusted_extraction_from_grounded_web_research(
    result: GroundedWebResearchResult,
) -> dict[str, Any]:
    """Build the CanonicalAIDraft.untrusted_extraction envelope.

    Output remains untrusted. Share counts are copied only when present
    in model JSON. Grounding URIs are preserved; they are not snapshots.
    """
    claims = _claims_from_structured(result.structured, result.citations)
    return {
        "web_claims": claims,
        "grounding_citations": [
            {"source_url": item.uri, "source_name": item.title}
            for item in result.citations
            if item.uri
        ],
        "missing_citations": result.missing_citations,
        "malformed": result.malformed,
        "trusted": False,
        "may_create_snapshot": False,
        "may_influence_calculation": False,
        "claim_type": "CURRENT_OUTSTANDING",
    }


def _claims_from_structured(
    structured: Mapping[str, Any] | None,
    citations: tuple[GroundedCitation, ...],
) -> list[dict[str, Any]]:
    if structured is None:
        return []
    raw_rows = structured.get("web_claims")
    if raw_rows is None and (
        structured.get("source_url") or structured.get("source_reference")
    ):
        raw_rows = (structured,)
    if not isinstance(raw_rows, (list, tuple)):
        return []
    claims: list[dict[str, Any]] = []
    for row in raw_rows:
        copied = _copy_claim(row, citations)
        if copied is not None:
            claims.append(copied)
    return claims


def _copy_claim(
    row: object,
    citations: tuple[GroundedCitation, ...],
) -> dict[str, Any] | None:
    if not isinstance(row, Mapping):
        return None
    claim: dict[str, Any] = {}
    for key in _CLAIM_KEYS:
        if key in row:
            claim[key] = row[key]
    url = _text(claim.get("source_url") or claim.get("source_reference"))
    if not url and len(citations) == 1 and citations[0].uri:
        url = citations[0].uri
        claim["source_url"] = url
        if not _text(claim.get("source_name")) and citations[0].title:
            claim["source_name"] = citations[0].title
    if url:
        claim["source_url"] = url
    claim["trusted"] = False
    claim["may_create_snapshot"] = False
    claim["claim_type"] = _text(claim.get("claim_type")) or "CURRENT_OUTSTANDING"
    return claim


def _citations_from_payload(payload: object) -> tuple[GroundedCitation, ...]:
    if not isinstance(payload, Mapping):
        return ()
    found: list[GroundedCitation] = []
    seen: set[str] = set()
    for candidate in _candidates(payload):
        metadata = candidate.get("groundingMetadata")
        if isinstance(metadata, Mapping):
            for chunk in metadata.get("groundingChunks") or ():
                citation = _citation_from_chunk(chunk)
                if citation is None or citation.uri in seen:
                    continue
                seen.add(citation.uri)
                found.append(citation)
        citation_meta = candidate.get("citationMetadata")
        if isinstance(citation_meta, Mapping):
            for source in citation_meta.get("citationSources") or ():
                citation = _citation_from_source(source)
                if citation is None or citation.uri in seen:
                    continue
                seen.add(citation.uri)
                found.append(citation)
    return tuple(found)


def _citation_from_chunk(chunk: object) -> GroundedCitation | None:
    if not isinstance(chunk, Mapping):
        return None
    web = chunk.get("web")
    if isinstance(web, Mapping):
        uri = _text(web.get("uri"))
        if uri:
            return GroundedCitation(uri=uri, title=_text(web.get("title")))
    retrieved = chunk.get("retrievedContext")
    if isinstance(retrieved, Mapping):
        uri = _text(retrieved.get("uri"))
        if uri:
            return GroundedCitation(uri=uri, title=_text(retrieved.get("title")))
    return None


def _citation_from_source(source: object) -> GroundedCitation | None:
    if not isinstance(source, Mapping):
        return None
    uri = _text(source.get("uri") or source.get("source_uri"))
    if not uri:
        return None
    return GroundedCitation(uri=uri, title=_text(source.get("title")))


def _web_search_queries(payload: object) -> tuple[str, ...]:
    if not isinstance(payload, Mapping):
        return ()
    queries: list[str] = []
    for candidate in _candidates(payload):
        metadata = candidate.get("groundingMetadata")
        if not isinstance(metadata, Mapping):
            continue
        for item in metadata.get("webSearchQueries") or ():
            text = _text(item)
            if text:
                queries.append(text)
    return tuple(queries)


def _candidates(payload: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    raw = payload.get("candidates") or ()
    if not isinstance(raw, (list, tuple)):
        return ()
    return tuple(item for item in raw if isinstance(item, Mapping))


def _text(value: object) -> str:
    if value is None or isinstance(value, bool):
        return ""
    if not isinstance(value, str):
        return ""
    return value.strip()
