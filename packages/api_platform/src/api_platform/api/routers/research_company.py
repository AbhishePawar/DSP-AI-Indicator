"""Canonical research HTTP boundary.

POST /api/v1/research/company (and unversioned /research/company).

The router owns authentication and the public DTO only. AI execution,
ResearchPackage construction, provider calls, and DSP validation live in the
application service so private research internals cannot leak through HTTP.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from api_platform.api.dependencies import require_authenticated_actor
from api_platform.api.research_company_schemas import (
    AI_EXECUTION_BLOCKED_MESSAGE,
    AI_EXECUTION_UNAVAILABLE_MESSAGE,
    AI_VALIDATION_FAILED_MESSAGE,
    AiExecutionState,
    PublicResearchReportHttp,
    ResearchCompanyOutcome,
    ResearchCompanyRequest,
    ResearchCompanyResponse,
)
from api_platform.api.research_company_service import execute_research_company

router = APIRouter(tags=["research"])

_ResearchActor = dict[str, Any]


@router.post(
    "/research/company",
    response_model=ResearchCompanyResponse,
)
def research_company(
    body: ResearchCompanyRequest,
    request: Request,
    _actor: _ResearchActor = Depends(require_authenticated_actor),  # noqa: B008
) -> ResearchCompanyResponse:
    """Run the authenticated canonical DSP → OpenAI research path."""
    correlation_id = getattr(request.state, "request_id", None)
    state = getattr(request.app.state, "api", None)
    platform = getattr(state, "platform", None)
    if platform is None:
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

    execution = execute_research_company(
        platform=platform,
        ticker=body.ticker,
        exchange=body.exchange,
        company=body.company,
    )

    if execution.ok and execution.report is not None:
        report = PublicResearchReportHttp.model_validate(execution.report)
        return ResearchCompanyResponse(
            ok=True,
            api_version="v1",
            correlation_id=correlation_id,
            analysis_id=None,
            ai_execution_state=AiExecutionState.AI_EXECUTED,
            outcome=ResearchCompanyOutcome.SUCCESS,
            report=report,
            limitations=list(execution.limitations),
            errors=[],
        )

    if execution.state == AiExecutionState.AI_UNAVAILABLE.value:
        default_message = AI_EXECUTION_UNAVAILABLE_MESSAGE
        state_value = AiExecutionState.AI_UNAVAILABLE
        outcome = ResearchCompanyOutcome.AI_UNAVAILABLE
    else:
        default_message = AI_VALIDATION_FAILED_MESSAGE
        state_value = AiExecutionState.AI_VALIDATION_FAILED
        outcome = ResearchCompanyOutcome.AI_VALIDATION_FAILED

    return ResearchCompanyResponse(
        ok=False,
        api_version="v1",
        correlation_id=correlation_id,
        analysis_id=None,
        ai_execution_state=state_value,
        outcome=outcome,
        report=None,
        limitations=list(execution.limitations) or [default_message],
        errors=list(execution.errors) or [default_message],
    )
