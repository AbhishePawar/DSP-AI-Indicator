"""Canonical research HTTP boundary — STEP 4I blocked stub.

POST /api/v1/research/company (and unversioned /research/company).

Does not execute AI, build a ResearchPackage, generate a private prompt,
validate AI output, or return PublicResearchReport. Production AI remains
fail-closed.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from api_platform.api.dependencies import require_authenticated_actor
from api_platform.api.research_company_schemas import (
    AI_EXECUTION_BLOCKED_MESSAGE,
    AiExecutionState,
    ResearchCompanyOutcome,
    ResearchCompanyRequest,
    ResearchCompanyResponse,
)

router = APIRouter(tags=["research"])

_ResearchActor = dict[str, Any]


@router.post(
    "/research/company",
    response_model=ResearchCompanyResponse,
    status_code=503,
)
def research_company(
    body: ResearchCompanyRequest,
    request: Request,
    _actor: _ResearchActor = Depends(require_authenticated_actor),  # noqa: B008
) -> ResearchCompanyResponse:
    """Establish the canonical research HTTP boundary while AI is blocked.

    Validates ``ResearchCompanyRequest`` and authenticates the actor, then
    returns ``AI_EXECUTION_BLOCKED`` with ``report=null``. Does not call
    providers, assemble research, or fabricate a report.
    """
    # Request is schema-validated only. STEP 4I does not research the ticker.
    _validated_ticker = body.ticker
    del _validated_ticker
    correlation_id = getattr(request.state, "request_id", None)
    return ResearchCompanyResponse(
        ok=False,
        api_version="v1",
        correlation_id=correlation_id,
        analysis_id=None,
        ai_execution_state=AiExecutionState.AI_EXECUTION_BLOCKED,
        outcome=ResearchCompanyOutcome.AI_EXECUTION_BLOCKED,
        report=None,
        limitations=[AI_EXECUTION_BLOCKED_MESSAGE],
        errors=[AI_EXECUTION_BLOCKED_MESSAGE],
    )
