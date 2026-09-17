"""Governed, provider-neutral research-team coordination for DSP analysis."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from copilot.enums import LanguageModelStatus, UserIntentType
from copilot.models import LanguageModelRequest
from llm_adapters.registry import ProviderRegistry


class ResearchRole(StrEnum):
    FIND = "find"
    VERIFY = "verify"
    ATTACK = "attack"
    REVIEW = "review"


class ResearchAgentStatus(StrEnum):
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_QUOTA = "provider_quota"
    PROVIDER_AUTH_FAILURE = "provider_auth_failure"
    NO_EVIDENCE_FOUND = "no_evidence_found"
    EVIDENCE_REJECTED = "evidence_rejected"
    RESEARCH_COMPLETE = "research_complete"
    IDENTITY_BLOCKED = "identity_blocked"
    NOT_EXECUTED = "not_executed"


@dataclass(frozen=True, slots=True)
class ResearchIdentity:
    company: str
    ticker: str
    exchange: str | None = None
    isin: str | None = None
    mic: str | None = None

    @property
    def resolved(self) -> bool:
        return bool(self.company.strip() and self.ticker.strip() and self.exchange)

    def to_dict(self) -> dict[str, str | None]:
        return {
            "company": self.company.strip() or None,
            "ticker": self.ticker.strip().upper() or None,
            "exchange": self.exchange.strip().upper() if self.exchange else None,
            "isin": self.isin,
            "mic": self.mic,
            "status": "resolved" if self.resolved else "unresolved",
        }


@dataclass(frozen=True, slots=True)
class AgentOutcome:
    role: ResearchRole
    provider: str
    status: ResearchAgentStatus
    configured: bool
    evidence_count: int = 0
    verified_count: int = 0
    limitations: tuple[str, ...] = ()
    audit_reference: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role.value,
            "provider": self.provider,
            "status": self.status.value,
            "configured": self.configured,
            "evidence_count": self.evidence_count,
            "verified_count": self.verified_count,
            "limitations": list(self.limitations),
            "audit_reference": self.audit_reference,
        }


_ROLE_PROVIDERS: tuple[tuple[ResearchRole, str], ...] = (
    (ResearchRole.FIND, "gemini"),
    (ResearchRole.VERIFY, "openai"),
    (ResearchRole.ATTACK, "deepseek"),
    (ResearchRole.REVIEW, "anthropic"),
)


def _classify_result(status: LanguageModelStatus) -> ResearchAgentStatus:
    if status is LanguageModelStatus.PROVIDER_UNAVAILABLE:
        return ResearchAgentStatus.PROVIDER_UNAVAILABLE
    if status is LanguageModelStatus.TIMEOUT:
        return ResearchAgentStatus.PROVIDER_TIMEOUT
    return (
        ResearchAgentStatus.RESEARCH_COMPLETE
        if status is LanguageModelStatus.COMPLETE
        else ResearchAgentStatus.NOT_EXECUTED
    )


class ResearchTeamCoordinator:
    """Runs fixed research roles without granting them authority over DSP math."""

    def __init__(self, registry: ProviderRegistry | None = None) -> None:
        self._registry = registry or ProviderRegistry()

    def run(self, identity: ResearchIdentity) -> dict[str, Any]:
        audit_id = f"research-{uuid.uuid4().hex[:16]}"
        if not identity.resolved:
            outcomes = [
                AgentOutcome(
                    role=role,
                    provider=provider,
                    status=ResearchAgentStatus.IDENTITY_BLOCKED,
                    configured=bool(
                        self._registry.get(provider)
                        and self._registry.get(provider).is_configured()
                    ),
                    limitations=(
                        "Canonical company, ticker, and exchange identity is "
                        "required before research.",
                    ),
                    audit_reference=audit_id,
                ).to_dict()
                for role, provider in _ROLE_PROVIDERS
            ]
            return self._payload(
                identity,
                outcomes,
                ["AI research blocked until security identity is resolved."],
            )

        execute = os.environ.get("DSP_AI_RESEARCH_TEAM_EXECUTE", "0").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        outcomes: list[dict[str, Any]] = []
        limitations: list[str] = []
        for role, provider in _ROLE_PROVIDERS:
            adapter = self._registry.get(provider)
            configured = bool(adapter and adapter.is_configured())
            if not configured:
                status = ResearchAgentStatus.PROVIDER_UNAVAILABLE
                reason = (
                    f"{provider} is not configured; no {role.value} output was used."
                )
            elif not execute:
                status = ResearchAgentStatus.NOT_EXECUTED
                reason = (
                    "Provider execution is disabled for this environment; "
                    "no claim was fabricated."
                )
            else:
                request = LanguageModelRequest(
                    request_id=f"{audit_id}-{role.value}",
                    intent_class=UserIntentType.TRACE_EVIDENCE,
                    prompt_parts=(
                        "Return only source-backed research candidates. Do not "
                        "calculate valuation, financial statements, share counts, "
                        "or recommendations.",
                        f"Identity: {identity.company} ({identity.ticker}) on "
                        f"{identity.exchange}. Role: {role.value}.",
                    ),
                    context_digest_ids=(),
                    provenance=("dsp.research_team.v1", audit_id),
                    constraints=(
                        "No unsupported facts",
                        "Cite authoritative primary sources",
                    ),
                )
                try:
                    result = adapter.invoke(request) if adapter else None
                    status = (
                        _classify_result(result.status)
                        if result
                        else ResearchAgentStatus.PROVIDER_UNAVAILABLE
                    )
                    reason = (
                        result.limitations[0]
                        if result and result.limitations
                        else "Provider returned no evidence."
                    )
                except Exception:  # noqa: BLE001
                    status = ResearchAgentStatus.PROVIDER_TIMEOUT
                    reason = (
                        "Provider invocation failed; authoritative DSP inputs "
                        "were unchanged."
                    )
            limitations.append(reason)
            outcomes.append(
                AgentOutcome(
                    role,
                    provider,
                    status,
                    configured,
                    limitations=(reason,),
                    audit_reference=audit_id,
                ).to_dict()
            )

        return self._payload(identity, outcomes, limitations)

    def _payload(
        self,
        identity: ResearchIdentity,
        outcomes: list[dict[str, Any]],
        limitations: list[str],
    ) -> dict[str, Any]:
        return {
            "version": "dsp.research-team.v1",
            "identity": identity.to_dict(),
            "status": (
                "research_complete"
                if any(
                    item["status"] == ResearchAgentStatus.RESEARCH_COMPLETE.value
                    for item in outcomes
                )
                else "degraded"
            ),
            "agents": outcomes,
            "evidence": {
                "candidate_count": 0,
                "verified_count": 0,
                "rejected_count": 0,
            },
            "limitations": list(dict.fromkeys(limitations)),
            "authority": (
                "EvidenceJudge and FinancialStatementPort/ShareCountPort "
                "remain authoritative."
            ),
        }


def build_research_team_metadata(
    *, ticker: str, company: str, exchange: str | None
) -> dict[str, Any]:
    return ResearchTeamCoordinator().run(
        ResearchIdentity(company=company, ticker=ticker, exchange=exchange)
    )


__all__ = [
    "AgentOutcome",
    "ResearchAgentStatus",
    "ResearchIdentity",
    "ResearchRole",
    "ResearchTeamCoordinator",
    "build_research_team_metadata",
]
