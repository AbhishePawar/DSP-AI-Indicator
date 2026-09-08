"""Claude / Anthropic live research agent. Optional.

Chat LanguageModelPort remains ``llm_adapters.anthropic_adapter`` (copilot).
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

from data_engine.multi_agent_research.agents import (
    AgentCapabilityState,
    AgentFailureClass,
    AgentRole,
    AgentRunResult,
)
from data_engine.multi_agent_research.contracts import ResearchRequest
from llm_adapters.research.claims import claims_from_model_output
from llm_adapters.research.http import request_json
from llm_adapters.research.qualification import (
    AgentQualification,
    LiveQualificationStatus,
)

_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"
_DEFAULT_MODEL = "claude-3-5-sonnet-20241022"


def _api_key() -> str:
    return (
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("DSP_AI_ANTHROPIC_API_KEY")
        or ""
    ).strip()


class ClaudeLiveResearchAgent:
    """INDEPENDENT REVIEW port. Optional. Absence must not block."""

    role = AgentRole.CLAUDE
    timeout_seconds = 45.0

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._api_key = (api_key if api_key is not None else _api_key()).strip()
        self.model_label = (
            model
            or os.environ.get("DSP_AI_ANTHROPIC_MODEL")
            or os.environ.get("ANTHROPIC_MODEL")
            or _DEFAULT_MODEL
        ).strip()
        if timeout_seconds is not None:
            self.timeout_seconds = timeout_seconds
        self.capability_state = (
            AgentCapabilityState.LIVE if self._api_key else AgentCapabilityState.UNKNOWN
        )

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def probe(self) -> AgentQualification:
        if not self._api_key:
            return AgentQualification(
                agent=self.role,
                status=LiveQualificationStatus.NOT_CONFIGURED,
                configured=False,
                model=self.model_label,
                http_status=None,
                failure=AgentFailureClass.AGENT_UNAVAILABLE,
                detail=(
                    "No Anthropic/Claude application credential in env or "
                    "Secret Manager; CLAUDE=UNAVAILABLE is allowed"
                ),
            )
        result = request_json(
            method="POST",
            url=_MESSAGES_URL,
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": _ANTHROPIC_VERSION,
                "Content-Type": "application/json",
            },
            json_body={
                "model": self.model_label,
                "max_tokens": 32,
                "messages": [{"role": "user", "content": "ping"}],
            },
            timeout_seconds=self.timeout_seconds,
        )
        if result.failure is AgentFailureClass.NONE:
            return AgentQualification(
                agent=self.role,
                status=LiveQualificationStatus.LIVE_AVAILABLE_BUT_UNQUALIFIED,
                configured=True,
                model=self.model_label,
                http_status=result.status_code,
                failure=AgentFailureClass.NONE,
                detail="Anthropic Messages reachable; not primary-evidence qualified",
            )
        status = LiveQualificationStatus.UNKNOWN
        if result.failure is AgentFailureClass.AUTH_FAILURE:
            status = LiveQualificationStatus.AUTH_FAILURE
        elif result.failure is AgentFailureClass.RATE_LIMITED:
            status = LiveQualificationStatus.RATE_LIMITED
        elif result.failure is AgentFailureClass.MODEL_NOT_FOUND:
            status = LiveQualificationStatus.MODEL_NOT_FOUND
        elif result.failure is AgentFailureClass.TIMEOUT:
            status = LiveQualificationStatus.TIMEOUT
        return AgentQualification(
            agent=self.role,
            status=status,
            configured=True,
            model=self.model_label,
            http_status=result.status_code,
            failure=result.failure,
            detail=result.detail,
        )

    def research(self, request: ResearchRequest) -> AgentRunResult:
        if not self._api_key:
            return AgentRunResult(
                agent=self.role,
                capability_state=AgentCapabilityState.UNKNOWN,
                failure=AgentFailureClass.AGENT_UNAVAILABLE,
                claims=(),
                detail="CLAUDE=UNAVAILABLE: ANTHROPIC_API_KEY missing",
            )
        result = request_json(
            method="POST",
            url=_MESSAGES_URL,
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": _ANTHROPIC_VERSION,
                "Content-Type": "application/json",
            },
            json_body={
                "model": self.model_label,
                "max_tokens": 512,
                "temperature": 0.0,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Independent review only. Challenge unsupported "
                            f"claims. Identity {request.ticker} {request.isin} "
                            f"{request.mic}."
                        ),
                    }
                ],
            },
            timeout_seconds=self.timeout_seconds,
        )
        if result.failure is not AgentFailureClass.NONE:
            return AgentRunResult(
                agent=self.role,
                capability_state=AgentCapabilityState.LIVE,
                failure=result.failure,
                claims=(),
                detail=result.detail,
            )
        text = ""
        if result.payload:
            content = result.payload.get("content") or []
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text += str(block.get("text") or "")
        claims = claims_from_model_output(
            request=request,
            agent="claude",
            text=text,
            payload=None,
            retrieved_at=datetime.now(tz=UTC),
        )
        if not claims:
            return AgentRunResult(
                agent=self.role,
                capability_state=AgentCapabilityState.LIVE,
                failure=AgentFailureClass.EVIDENCE_INSUFFICIENT,
                claims=(),
                detail="EVIDENCE_INSUFFICIENT: Claude returned no primary claim",
            )
        return AgentRunResult(
            agent=self.role,
            capability_state=AgentCapabilityState.LIVE,
            failure=AgentFailureClass.NONE,
            claims=claims,
            detail=f"anthropic messages model={self.model_label}",
        )
