"""Per-agent HTTP helpers. Never log credentials."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from data_engine.multi_agent_research.agents import (
    AgentFailureClass,
    classify_http_agent_failure,
)


@dataclass(frozen=True, slots=True)
class AgentHttpResult:
    status_code: int | None
    body_text: str
    payload: dict[str, object] | None
    failure: AgentFailureClass
    timed_out: bool
    detail: str


def request_json(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    json_body: dict[str, Any] | None,
    timeout_seconds: float,
) -> AgentHttpResult:
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.request(
                method,
                url,
                headers=headers,
                json=json_body,
            )
    except httpx.TimeoutException:
        return AgentHttpResult(
            status_code=None,
            body_text="",
            payload=None,
            failure=AgentFailureClass.TIMEOUT,
            timed_out=True,
            detail="timeout",
        )
    except httpx.HTTPError as exc:
        return AgentHttpResult(
            status_code=None,
            body_text="",
            payload=None,
            failure=AgentFailureClass.TRANSPORT_FAILURE,
            timed_out=False,
            detail=type(exc).__name__,
        )

    text = response.text or ""
    payload: dict[str, object] | None
    try:
        raw = response.json()
        payload = raw if isinstance(raw, dict) else None
    except ValueError:
        payload = None
        if 200 <= response.status_code < 300:
            return AgentHttpResult(
                status_code=response.status_code,
                body_text=text,
                payload=None,
                failure=AgentFailureClass.MALFORMED_RESPONSE,
                timed_out=False,
                detail="response JSON was not an object",
            )

    failure = classify_http_agent_failure(
        response.status_code,
        body_text=text,
    )
    if 200 <= response.status_code < 300:
        if payload is None and not text.strip():
            failure = AgentFailureClass.EMPTY_RESPONSE
        elif failure is AgentFailureClass.NONE:
            failure = AgentFailureClass.NONE
    return AgentHttpResult(
        status_code=response.status_code,
        body_text=text,
        payload=payload,
        failure=failure,
        timed_out=False,
        detail=f"http_{response.status_code}",
    )
