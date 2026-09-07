"""Client share-research HTTP boundary."""

from __future__ import annotations

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

_Actor = dict[str, Any]
_ENGINE: ShareResearchEngine | None = None


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
    del request
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
    payload = result.to_client_dict()
    limitations = [
        "Gemini research remains untrusted until DSP validation.",
        "Valuation consumes the count only when status is CURRENT.",
    ]
    if payload.get("unresolved_issues"):
        limitations.extend(str(item) for item in payload["unresolved_issues"][:5])
    return ShareResearchHttpResponse(
        ok=payload.get("status") == "CURRENT",
        result=payload,
        limitations=limitations,
    )
