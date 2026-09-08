"""ChatGPT / OpenAI live research agent.

Chat LanguageModelPort remains ``llm_adapters.openai_adapter`` (copilot).
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

_MODELS_URL = "https://api.openai.com/v1/models"
_CHAT_URL = "https://api.openai.com/v1/chat/completions"
_DEFAULT_MODEL = "gpt-4o-mini"


def _api_key() -> str:
    return (
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("DSP_AI_OPENAI_API_KEY")
        or ""
    ).strip()


class ChatGptLiveResearchAgent:
    """VERIFY port. Independent of Gemini. Not an authoritative source."""

    role = AgentRole.CHATGPT
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
            or os.environ.get("DSP_AI_OPENAI_MODEL")
            or os.environ.get("OPENAI_MODEL")
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
                    "No OpenAI/ChatGPT application credential in env or Secret Manager"
                ),
            )
        result = request_json(
            method="GET",
            url=_MODELS_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json_body=None,
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
                detail="OpenAI /v1/models reachable; not primary-evidence qualified",
            )
        status = LiveQualificationStatus.UNKNOWN
        if result.failure is AgentFailureClass.AUTH_FAILURE:
            status = LiveQualificationStatus.AUTH_FAILURE
        elif result.failure is AgentFailureClass.RATE_LIMITED:
            status = LiveQualificationStatus.RATE_LIMITED
        elif result.failure is AgentFailureClass.TIMEOUT:
            status = LiveQualificationStatus.TIMEOUT
        elif result.failure is AgentFailureClass.TRANSPORT_FAILURE:
            status = LiveQualificationStatus.TRANSPORT_FAILURE
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
                detail="NOT_CONFIGURED: OPENAI_API_KEY missing",
            )
        result = request_json(
            method="POST",
            url=_CHAT_URL,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json_body={
                "model": self.model_label,
                "temperature": 0.0,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Independent verifier. Do not copy Gemini. "
                            "Do not invent identity. You are not a source."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Verify listing identity {request.ticker} "
                            f"ISIN={request.isin} MIC={request.mic}."
                        ),
                    },
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
            choices = result.payload.get("choices") or []
            if isinstance(choices, list) and choices:
                message = choices[0]
                if isinstance(message, dict):
                    body = message.get("message") or {}
                    if isinstance(body, dict):
                        text = str(body.get("content") or "")
        claims = claims_from_model_output(
            request=request,
            agent="chatgpt",
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
                detail="EVIDENCE_INSUFFICIENT: ChatGPT returned no primary claim",
            )
        return AgentRunResult(
            agent=self.role,
            capability_state=AgentCapabilityState.LIVE,
            failure=AgentFailureClass.NONE,
            claims=claims,
            detail=f"openai chat model={self.model_label}",
        )
