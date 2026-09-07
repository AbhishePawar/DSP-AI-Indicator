"""Client share-research HTTP boundary."""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, Request

from api_platform.api.dependencies import require_authenticated_actor
from api_platform.api.share_research_schemas import (
    ShareResearchHttpRequest,
    ShareResearchHttpResponse,
)
from dsp_platform.share_research import (
    ShareResearchEngine,
    ShareResearchRequest,
    research_shares,
)

router = APIRouter(tags=["share-research"])
_LOG = logging.getLogger("dsp.api.share_research")

_Actor = dict[str, Any]
_ENGINE: ShareResearchEngine | None = None


def redacted_auth_trace(authorization: str) -> tuple[str, int]:
    """Scheme + material length only. Never returns the token."""
    raw = authorization or ""
    if not raw.strip():
        return "none", 0
    scheme, sep, rest = raw.partition(" ")
    if not sep:
        return "unknown", 0
    return (scheme.strip() or "unknown"), len(rest)


def actor_ref(user_id: str) -> str:
    """Redacted actor identifier. Never the raw user id."""
    uid = (user_id or "").strip()
    if not uid:
        return "none"
    return hashlib.sha256(uid.encode("utf-8")).hexdigest()[:12]


def get_share_research_engine() -> ShareResearchEngine:
    global _ENGINE
    if _ENGINE is None:
        from dsp_platform.share_research.gemini import GeminiShareResearchAdapter

        _ENGINE = ShareResearchEngine(gemini=GeminiShareResearchAdapter())
    return _ENGINE


def reset_share_research_engine_for_tests(
    engine: ShareResearchEngine | None,
) -> None:
    global _ENGINE
    _ENGINE = engine


@router.post("/share-research", response_model=ShareResearchHttpResponse)
def share_research(
    body: ShareResearchHttpRequest,
    request: Request,
    _actor: _Actor = Depends(require_authenticated_actor),  # noqa: B008
) -> ShareResearchHttpResponse:
    """Research current outstanding shares. Thin client — no valuation here."""
    request_id = str(getattr(request.state, "request_id", "") or "")
    scheme, material_len = redacted_auth_trace(
        request.headers.get("authorization") or ""
    )
    user = _actor.get("user") if isinstance(_actor.get("user"), dict) else {}
    role = str((user or {}).get("role") or "").strip() or "unknown"
    _LOG.info(
        "share_research_http stage=start request_id=%s ticker=%s exchange=%s "
        "auth_scheme=%s auth_material_len=%s actor_ref=%s actor_role=%s origin=%s",
        request_id,
        body.ticker,
        body.exchange,
        scheme,
        material_len,
        actor_ref(str(_actor.get("user_id") or "")),
        role,
        request.headers.get("origin") or "",
    )
    started = time.perf_counter()
    try:
        result = research_shares(
            ShareResearchRequest(
                ticker=body.ticker,
                exchange=body.exchange,
                company=body.company,
                isin=body.isin,
                force_refresh=body.force_refresh,
            ),
            engine=get_share_research_engine(),
        )
    except Exception as exc:
        _LOG.info(
            "share_research_http stage=error request_id=%s exception_class=%s "
            "latency_ms=%s",
            request_id,
            type(exc).__name__,
            int((time.perf_counter() - started) * 1000),
        )
        raise
    payload = result.to_client_dict()
    limitations = [
        "Gemini research remains untrusted until DSP validation.",
        "Valuation consumes the count only when status is CURRENT.",
    ]
    if payload.get("unresolved_issues"):
        limitations.extend(str(item) for item in payload["unresolved_issues"][:5])
    _LOG.info(
        "share_research_http stage=complete request_id=%s status=%s "
        "gemini_invoked=%s latency_ms=%s",
        request_id,
        payload.get("status"),
        payload.get("gemini_invoked"),
        int((time.perf_counter() - started) * 1000),
    )
    return ShareResearchHttpResponse(
        ok=payload.get("status") == "CURRENT",
        result=payload,
        limitations=limitations,
    )
