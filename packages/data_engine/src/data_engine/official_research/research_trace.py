"""Structured research trace. Secrets must never be stored."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from data_engine.official_research.nse_mcp import redact_mcp_text
from data_engine.official_research.models import utc_now

__all__ = [
    "CostRecord",
    "MESH_STEPS",
    "ResearchStep",
    "ResearchTrace",
    "ToolCallRecord",
    "redact_trace_text",
]

MESH_STEPS: tuple[str, ...] = (
    "PLAN",
    "DISCOVER",
    "RETRIEVE",
    "EXTRACT",
    "NORMALIZE",
    "RECONCILE",
    "VERIFY",
)


def redact_trace_text(text: str) -> str:
    return redact_mcp_text(str(text or ""))


@dataclass(frozen=True, slots=True)
class ToolCallRecord:
    tool_name: str
    arguments: dict[str, Any]
    timestamp: datetime
    response: str
    provider: str
    source: str
    evidence_locator: str | None
    authority: str


@dataclass(frozen=True, slots=True)
class CostRecord:
    input_tokens: int | None
    output_tokens: int | None
    tool_calls: int
    latency_ms: float
    estimated_cost: float | None
    model: str | None = None


@dataclass(frozen=True, slots=True)
class ResearchStep:
    name: str
    status: str
    started_at: datetime
    completed_at: datetime
    detail: str = ""
    evidence_ids: tuple[str, ...] = ()


@dataclass
class ResearchTrace:
    request_id: str
    security_identity: str
    plan_id: str
    agent_provider: str | None
    model: str | None
    steps: list[ResearchStep] = field(default_factory=list)
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=utc_now)
    completed_at: datetime | None = None
    cost: CostRecord | None = None
    independent_agents: int = 0
    timings: dict[str, float] = field(default_factory=dict)

    def add_step(
        self,
        name: str,
        *,
        status: str,
        started_at: datetime,
        detail: str = "",
        evidence_ids: tuple[str, ...] = (),
    ) -> None:
        if name not in MESH_STEPS:
            raise ValueError(f"unknown mesh step {name}")
        self.steps.append(
            ResearchStep(
                name=name,
                status=status,
                started_at=started_at,
                completed_at=utc_now(),
                detail=redact_trace_text(detail)[:500],
                evidence_ids=evidence_ids,
            )
        )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "security_identity": self.security_identity,
            "plan_id": self.plan_id,
            "agent_provider": self.agent_provider,
            "model": self.model,
            "independent_agents": self.independent_agents,
            "steps": [step.name for step in self.steps],
            "step_status": {step.name: step.status for step in self.steps},
            "tool_calls": [
                {
                    "tool_name": item.tool_name,
                    "arguments": item.arguments,
                    "timestamp": item.timestamp.isoformat(),
                    "response": redact_trace_text(item.response)[:500],
                    "provider": item.provider,
                    "source": item.source,
                    "evidence_locator": item.evidence_locator,
                    "authority": item.authority,
                }
                for item in self.tool_calls
            ],
            "evidence_ids": list(self.evidence_ids),
            "decisions": list(self.decisions),
            "errors": [redact_trace_text(item) for item in self.errors],
            "started_at": self.started_at.isoformat(),
            "completed_at": None
            if self.completed_at is None
            else self.completed_at.isoformat(),
            "timings": dict(self.timings),
            "cost": None
            if self.cost is None
            else {
                "input_tokens": self.cost.input_tokens,
                "output_tokens": self.cost.output_tokens,
                "tool_calls": self.cost.tool_calls,
                "latency_ms": self.cost.latency_ms,
                "estimated_cost": self.cost.estimated_cost,
                "model": self.cost.model,
            },
        }
