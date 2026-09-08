"""Multi-agent research orchestrator (SIMPLE-14H).

Security Master → agents → whitelist → RAW evidence → reconciliation →
quality gate. AI consensus is never treated as proof.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from data_engine.data_states import (
    DataState,
    QualityDecision,
    apply_quality_gate,
)
from data_engine.multi_agent_research.agents import (
    AgentCapabilityState,
    AgentFailureClass,
    AgentRole,
    AgentRunResult,
    ResearchAgentPort,
    UnavailableResearchAgent,
)
from data_engine.multi_agent_research.contracts import (
    AUTHORITATIVE_FINANCIAL_FIELDS,
    EvidenceRecord,
    ResearchRequest,
)
from data_engine.multi_agent_research.injection import scan_untrusted_text
from data_engine.multi_agent_research.reconciliation import (
    AgreementReport,
    ReconciliationResult,
    compare_agents,
    reconcile_field,
)
from data_engine.multi_agent_research.source_urls import classify_source_url
from data_engine.security_identity import (
    IdentityStatus,
    SecurityIdentity,
    SecurityIdentityPort,
    default_security_master,
    resolve_security_identity,
)
from data_engine.source_policy import (
    SourceDecision,
    SourceTier,
    classify_source,
    is_ai_agent_source,
)

__all__ = [
    "DEFAULT_AGENT_CAPABILITIES",
    "ResearchOutcomeStatus",
    "ResearchRunResult",
    "ResearchOrchestrator",
    "default_unavailable_agents",
]


class ResearchOutcomeStatus(StrEnum):
    RESEARCH_COMPLETE = "RESEARCH_COMPLETE"
    RESEARCH_PARTIAL = "RESEARCH_PARTIAL"
    RESEARCH_UNAVAILABLE = "RESEARCH_UNAVAILABLE"
    IDENTITY_BLOCKED = "IDENTITY_BLOCKED"


# SIMPLE-11: production Gemini generateContent did not yield usable output.
# Do not retry those models from this module.
DEFAULT_AGENT_CAPABILITIES: dict[AgentRole, AgentCapabilityState] = {
    AgentRole.GEMINI: AgentCapabilityState.EXTERNAL_BLOCKER,
    AgentRole.CHATGPT: AgentCapabilityState.STUB,
    AgentRole.DEEP_SEARCH: AgentCapabilityState.STUB,
    AgentRole.CLAUDE: AgentCapabilityState.STUB,
}


@dataclass(frozen=True, slots=True)
class ResearchRunResult:
    status: ResearchOutcomeStatus
    request: ResearchRequest | None
    identity: SecurityIdentity
    agent_results: tuple[AgentRunResult, ...]
    evidence: tuple[EvidenceRecord, ...]
    reconciled: tuple[ReconciliationResult, ...]
    agreement: AgreementReport | None
    verified_fields: tuple[str, ...]
    detail: str

    def agent_status_map(self) -> dict[str, str]:
        return {row.agent.value: row.failure.value for row in self.agent_results}


def default_unavailable_agents() -> dict[AgentRole, ResearchAgentPort]:
    return {
        AgentRole.GEMINI: UnavailableResearchAgent(
            AgentRole.GEMINI,
            capability_state=AgentCapabilityState.EXTERNAL_BLOCKER,
            failure=AgentFailureClass.MODEL_NOT_FOUND,
            detail=(
                "GEMINI_CAPABILITY=EXTERNAL_BLOCKER "
                "(SIMPLE-11 generateContent unusable)"
            ),
        ),
        AgentRole.CHATGPT: UnavailableResearchAgent(
            AgentRole.CHATGPT,
            capability_state=AgentCapabilityState.STUB,
            detail="ChatGPT research agent not live-qualified",
        ),
        AgentRole.DEEP_SEARCH: UnavailableResearchAgent(
            AgentRole.DEEP_SEARCH,
            capability_state=AgentCapabilityState.STUB,
            detail="Deep Search research agent not live-qualified",
        ),
        AgentRole.CLAUDE: UnavailableResearchAgent(
            AgentRole.CLAUDE,
            capability_state=AgentCapabilityState.STUB,
            detail="CLAUDE=UNAVAILABLE (optional independent review)",
        ),
    }


class ResearchOrchestrator:
    """Provider-neutral research dispatcher. Does not call DSP engines."""

    def __init__(
        self,
        *,
        agents: dict[AgentRole, ResearchAgentPort] | None = None,
        security_master: SecurityIdentityPort | None = None,
        now: datetime | None = None,
    ) -> None:
        self._agents = agents if agents is not None else default_unavailable_agents()
        self._master = security_master or default_security_master()
        self._now = now

    def run(
        self,
        *,
        ticker: str,
        exchange: str | None = None,
        isin: str | None = None,
        mic: str | None = None,
        company: str | None = None,
        requested_fields: tuple[str, ...] = (),
        requested_as_of: str = "",
        research_purpose: str = "research",
        vendor_hints: dict[str, str] | None = None,
    ) -> ResearchRunResult:
        identity = self._master.resolve(
            ticker=ticker,
            exchange=exchange,
            isin=isin,
            mic=mic,
            company=company,
            vendor_hints=vendor_hints,
        )
        created = self._now or datetime.now(tz=UTC)
        request = ResearchRequest.from_identity(
            identity,
            requested_fields=requested_fields or ("shares_outstanding",),
            requested_as_of=requested_as_of,
            research_purpose=research_purpose,
            created_at=created,
        )
        if identity.status in {
            IdentityStatus.AMBIGUOUS,
            IdentityStatus.UNSUPPORTED,
            IdentityStatus.REJECTED,
        }:
            return ResearchRunResult(
                status=ResearchOutcomeStatus.IDENTITY_BLOCKED,
                request=request,
                identity=identity,
                agent_results=(),
                evidence=(),
                reconciled=(),
                agreement=None,
                verified_fields=(),
                detail=f"security master {identity.status.value}: {identity.detail}",
            )
        if identity.status is IdentityStatus.UNKNOWN and not identity.ticker:
            return ResearchRunResult(
                status=ResearchOutcomeStatus.IDENTITY_BLOCKED,
                request=request,
                identity=identity,
                agent_results=(),
                evidence=(),
                reconciled=(),
                agreement=None,
                verified_fields=(),
                detail=f"security master {identity.status.value}: {identity.detail}",
            )

        agent_results = tuple(
            self._dispatch(role, request)
            for role in (
                AgentRole.GEMINI,
                AgentRole.CHATGPT,
                AgentRole.DEEP_SEARCH,
                AgentRole.CLAUDE,
            )
        )
        evidence = self._claims_to_evidence(request, identity, agent_results)
        fields = requested_fields or tuple(dict.fromkeys(e.field for e in evidence))
        reconciled = tuple(
            reconcile_field(evidence, field=name, requested_as_of=requested_as_of)
            for name in fields
        )
        agreement = compare_agents(evidence) if evidence else None
        verified = self._promote(identity, evidence, reconciled)
        live_ok = [r for r in agent_results if r.ok]
        if not live_ok and not evidence:
            status = ResearchOutcomeStatus.RESEARCH_UNAVAILABLE
            detail = "RESEARCH_UNAVAILABLE: all agents failed; no evidence fabricated"
        elif any(not r.ok for r in agent_results):
            status = ResearchOutcomeStatus.RESEARCH_PARTIAL
            detail = "RESEARCH_PARTIAL: some agents unavailable; provenance preserved"
        else:
            status = ResearchOutcomeStatus.RESEARCH_COMPLETE
            detail = "agents returned candidates; verification is independent"
        return ResearchRunResult(
            status=status,
            request=request,
            identity=identity,
            agent_results=agent_results,
            evidence=evidence,
            reconciled=reconciled,
            agreement=agreement,
            verified_fields=verified,
            detail=detail,
        )

    def _dispatch(self, role: AgentRole, request: ResearchRequest) -> AgentRunResult:
        agent = self._agents.get(role)
        if agent is None:
            return UnavailableResearchAgent(role).research(request)
        return agent.research(request)

    def _claims_to_evidence(
        self,
        request: ResearchRequest,
        identity: SecurityIdentity,
        agent_results: tuple[AgentRunResult, ...],
    ) -> tuple[EvidenceRecord, ...]:
        rows: list[EvidenceRecord] = []
        for result in agent_results:
            for claim in result.claims:
                notes: list[str] = []
                injection = scan_untrusted_text(
                    " ".join(
                        [
                            claim.candidate_value,
                            claim.source_url,
                            claim.evidence_locator,
                        ]
                    )
                )
                if injection.suspect:
                    notes.append("prompt_injection_treated_as_data")
                source_tier, source_decision = classify_source(claim.source)
                url = classify_source_url(
                    claim.source_url,
                    declared_source_type=claim.source_type,
                )
                if is_ai_agent_source(claim.source):
                    notes.append("AI agent cannot be the authoritative source")
                if source_decision is SourceDecision.REJECT:
                    notes.append(f"source_policy={source_tier.value}")
                if url.decision is SourceDecision.REJECT:
                    notes.append(url.detail)
                if (
                    request.isin
                    and request.mic
                    and (claim.isin != request.isin or claim.mic != request.mic)
                ):
                    notes.append("claim identity diverges from security master")
                rows.append(
                    EvidenceRecord.from_claim(
                        claim,
                        identity_status=identity.status.value,
                        semantic_status="CANDIDATE",
                        freshness_status="UNKNOWN",
                        corporate_action_status="UNKNOWN",
                        data_state=DataState.RAW_PROVIDER_DATA,
                        injection_suspect=injection.suspect,
                        notes=tuple(notes),
                    )
                )
        return tuple(rows)

    def _promote(
        self,
        identity: SecurityIdentity,
        evidence: tuple[EvidenceRecord, ...],
        reconciled: tuple[ReconciliationResult, ...],
    ) -> tuple[str, ...]:
        accepted_fields = {
            row.field
            for row in reconciled
            if row.status.value == "ACCEPT"
            and row.data_state is DataState.RECONCILED_DATA
        }
        verified: list[str] = []
        by_field: dict[str, list[EvidenceRecord]] = {}
        for row in evidence:
            by_field.setdefault(row.field, []).append(row)
        identity_ok = identity.status is IdentityStatus.RESOLVED
        for field_name, rows in by_field.items():
            if field_name not in accepted_fields:
                continue
            primary = [
                r
                for r in rows
                if classify_source(r.source)[0] is SourceTier.PRIMARY
                and r.source_url
                and r.document_date
                and r.evidence_locator
                and not is_ai_agent_source(r.source)
            ]
            if not primary:
                continue
            sample = primary[0]
            gate = apply_quality_gate(
                source=sample.source,
                has_evidence=True,
                identity_ok=identity_ok,
                agent=None,
                authoritative_financial=field_name in AUTHORITATIVE_FINANCIAL_FIELDS,
            )
            if (
                gate.decision is QualityDecision.ACCEPT
                and gate.state is DataState.VERIFIED_DATA
            ):
                verified.append(field_name)
        return tuple(verified)


def build_request_from_master(
    *,
    ticker: str,
    exchange: str | None = None,
    isin: str | None = None,
    mic: str | None = None,
    company: str | None = None,
    requested_fields: tuple[str, ...] = (),
    requested_as_of: str = "",
    research_purpose: str = "research",
) -> tuple[SecurityIdentity, ResearchRequest]:
    identity = resolve_security_identity(
        ticker=ticker,
        exchange=exchange,
        isin=isin,
        mic=mic,
        company=company,
    )
    request = ResearchRequest.from_identity(
        identity,
        requested_fields=requested_fields,
        requested_as_of=requested_as_of,
        research_purpose=research_purpose,
        created_at=datetime.now(tz=UTC),
    )
    return identity, request
