"""Controlled single-architecture research mesh.

PLAN → DISCOVER → RETRIEVE → EXTRACT → NORMALIZE → RECONCILE → VERIFY

Reuses ResearchPlan, acquire_planned_fields, EvidenceJudge, and source policy.
Does not create a second research framework. Agents research; DSP judges.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from time import perf_counter
from typing import Any

from data_engine.official_research.agent_port import ResearchAgentPort, ResearchContext
from data_engine.official_research.evidence_identity import dedupe_evidence
from data_engine.official_research.field_acquisition import acquire_planned_fields
from data_engine.official_research.judge import EvidenceJudge
from data_engine.official_research.models import (
    EvidenceItem,
    ResearchClaim,
    ResearchRequest,
    ResearchResult,
    new_evidence_id,
    utc_now,
)
from data_engine.official_research.nse_mcp import NSE_MCP_COMMERCIAL_STATUS, redact_mcp_text
from data_engine.official_research.provider_router import (
    RouterInputs,
    estimate_token_cost,
    select_research_agent,
)
from data_engine.official_research.research_failures import (
    ResearchFailure,
    classify_openai_failure,
    is_transport_failure,
)
from data_engine.official_research.research_plan import build_research_plan
from data_engine.official_research.research_trace import (
    MESH_STEPS,
    CostRecord,
    ResearchTrace,
    ToolCallRecord,
)
from data_engine.official_research.tool_policy import (
    classify_tool_authority,
    nse_mcp_allowed_tool_names,
)
from data_engine.security_master import SecurityMasterService
from data_engine.security_master.models import SecurityListing

__all__ = ["MeshRun", "run_research_mesh"]


class MeshRun:
    def __init__(
        self,
        result: ResearchResult,
        trace: ResearchTrace,
        listing: SecurityListing | None,
        plan,
        acquisition,
    ) -> None:
        self.result = result
        self.trace = trace
        self.listing = listing
        self.plan = plan
        self.acquisition = acquisition
        self.nse_mcp_commercial_status = NSE_MCP_COMMERCIAL_STATUS


def run_research_mesh(
    request: ResearchRequest,
    *,
    listing: SecurityListing | None = None,
    context: ResearchContext | None = None,
    agent: ResearchAgentPort | None = None,
    candidates: Mapping[str, Sequence[EvidenceItem]] | None = None,
    document_text: str | None = None,
    document_url: str | None = None,
    tool_calls: Sequence[dict[str, Any]] = (),
    availability: dict[str, bool] | None = None,
    router_inputs: RouterInputs | None = None,
    production: bool = False,
    judge: EvidenceJudge | None = None,
) -> MeshRun:
    """One canonical mesh. Agent output is RAW. Judge is the only verifier."""
    started = utc_now()
    t0 = perf_counter()
    timings: dict[str, float] = {name.lower(): 0.0 for name in MESH_STEPS}
    context = context or ResearchContext(listing=listing, production=production)
    judge = judge or EvidenceJudge()
    request_id = request.request_id or new_evidence_id()

    t = perf_counter()
    identity, identity_failure = resolve_research_identity(request, listing=listing)
    timings["plan"] = 0.0
    if identity is None:
        trace = ResearchTrace(
            request_id=request_id,
            security_identity="UNRESOLVED",
            plan_id="",
            agent_provider=None,
            model=None,
            started_at=started,
        )
        trace.add_step("PLAN", status="REJECT", started_at=started, detail="identity unresolved")
        for name in MESH_STEPS[1:]:
            trace.add_step(name, status="SKIPPED", started_at=utc_now(), detail="identity gate")
        trace.errors.append(identity_failure or "SECURITY_NOT_FOUND")
        trace.completed_at = utc_now()
        result = ResearchResult(
            identity_status="UNKNOWN",
            isin=request.isin,
            mic=request.mic,
            company=request.company,
            ticker=request.ticker,
            evidence=(),
            price=None,
            claims=(),
            unresolved=(identity_failure or "SECURITY_NOT_FOUND",),
            mode=request.mode,
            status="REJECT",
            failures=(identity_failure or "SECURITY_NOT_FOUND",),
            research_started_at=started,
            research_finished_at=trace.completed_at,
            research_trace=trace,
            research_agents=0,
            limitations=("identity unresolved",),
            provenance="security_master",
        )
        return MeshRun(result, trace, None, None, None)

    plan = build_research_plan(identity, request)
    timings["plan"] = perf_counter() - t
    allowed_tools = nse_mcp_allowed_tool_names(plan)
    inputs = router_inputs or RouterInputs(
        availability=availability or {"openai": agent.available() if agent else False},
        capabilities={"openai": ("mcp", "search")},
        required_capabilities=("mcp",) if "eod_close" in plan.requested_fields else (),
        preferred_model=context.preferred_model,
    )
    decision = select_research_agent(inputs)
    trace = ResearchTrace(
        request_id=request_id,
        security_identity=identity.listing_id,
        plan_id=plan.request_id,
        agent_provider=decision.provider,
        model=decision.model_label or (agent.model_label if agent else None),
        started_at=started,
        independent_agents=decision.independent_agents,
    )
    trace.add_step("PLAN", status="COMPLETE", started_at=started, detail=plan.status)

    agent_result: ResearchResult | None = None
    agent_evidence: tuple[EvidenceItem, ...] = ()
    t = perf_counter()
    if (
        agent is not None
        and agent.available()
        and not production
        and decision.provider is not None
    ):
        try:
            agent_result = agent.research(request, plan, context)
            agent_evidence = agent_result.evidence
            if agent_result.failures:
                for code in agent_result.failures:
                    if is_transport_failure(code):
                        trace.errors.append(code)
                    else:
                        trace.errors.append(code)
        except ResearchFailure as exc:
            trace.errors.append(exc.code)
    elif decision.provider is None:
        trace.errors.append("OPENAI_UNAVAILABLE")
    timings["discover"] = perf_counter() - t

    t = perf_counter()
    for call in tool_calls:
        name = str(call.get("name") or "unknown")
        url = str(call.get("source_url") or call.get("url") or "")
        authority = classify_tool_authority(name, url)
        response = redact_mcp_text(str(call.get("response") or call.get("output") or ""))
        trace.tool_calls.append(
            ToolCallRecord(
                tool_name=name,
                arguments=dict(call.get("arguments") or {}),
                timestamp=utc_now(),
                response=response[:500],
                provider=str(call.get("provider") or decision.provider or "nse_mcp"),
                source=url,
                evidence_locator=str(call.get("evidence_locator") or name),
                authority=authority,
            )
        )
        if name not in allowed_tools and not name.startswith("mock_"):
            trace.decisions.append(f"tool {name} not in plan allow-list")
    timings["retrieve"] = perf_counter() - t

    assumption_claims = tuple(
        ResearchClaim(
            field="user_assumption",
            value=None,
            source_url=None,
            document_locator="user-input",
            agent="user",
            notes=text[:300],
            verification_status="REJECT",
        )
        for text in context.user_assumptions
    )
    injected_claims = tuple(
        ResearchClaim(
            field="injected_source",
            value=None,
            source_url=url,
            document_locator="injected",
            agent="user",
            notes="injected source is not authority",
            verification_status="REJECT",
        )
        for url in context.injected_sources
    )

    t = perf_counter()
    merged_candidates: dict[str, tuple[EvidenceItem, ...]] = {
        field: tuple(items) for field, items in (candidates or {}).items()
    }
    for item in agent_evidence:
        if item.source_type in {"llm", "agent_claim"}:
            continue
        merged_candidates.setdefault(item.field, ())
        merged_candidates[item.field] = merged_candidates[item.field] + (item,)
    timings["extract"] = perf_counter() - t

    t = perf_counter()
    acquisition = acquire_planned_fields(
        identity,
        request,
        candidates=merged_candidates,
        document_text=document_text,
        document_url=document_url,
        production=production,
        judge=judge,
    )
    timings["normalize"] = acquisition.timings.get("normalize", 0.0)
    timings["reconcile"] = acquisition.timings.get("reconcile", 0.0)
    timings["verify"] = acquisition.timings.get("verify", 0.0)
    _ = t

    raw_ledger = tuple(acquisition.evidence) + tuple(
        item for item in agent_evidence if item.source_type in {"llm", "agent_claim"}
    )
    ledger = dedupe_evidence(raw_ledger)
    verified = tuple(item for item in ledger if item.stage == "VERIFIED" and item.status == "VERIFIED")
    for item in ledger:
        if item.agent in {"openai_nse_mcp", "gemini_find", "chatgpt_verify"} and item.status == "VERIFIED":
            trace.decisions.append("AI_VERIFIED_BLOCKED")
    promoted = []
    for item in ledger:
        if item.stage == "RAW" and item.source_type in {"llm", "agent_claim"}:
            judged = judge.promote(item, production=production)
            promoted.append(judged)
            if judged.status == "VERIFIED":
                trace.decisions.append("AI_BYPASS_REJECTED")
        else:
            promoted.append(item)
    ledger = dedupe_evidence(tuple(promoted))
    verified = tuple(item for item in ledger if item.stage == "VERIFIED" and item.status == "VERIFIED")

    for name, status in (
        ("DISCOVER", "COMPLETE" if agent_result or tool_calls or document_text else "EMPTY"),
        ("RETRIEVE", "COMPLETE" if tool_calls or document_text or merged_candidates else "EMPTY"),
        ("EXTRACT", "COMPLETE"),
        ("NORMALIZE", "COMPLETE"),
        ("RECONCILE", "COMPLETE"),
        ("VERIFY", "COMPLETE"),
    ):
        ids = tuple(item.evidence_id for item in ledger if item.field)
        trace.add_step(name, status=status, started_at=utc_now(), evidence_ids=ids[:8])

    usage = None
    if agent_result is not None and isinstance(agent_result.research_trace, dict):
        usage = agent_result.research_trace.get("usage")
    latency_ms = (perf_counter() - t0) * 1000
    input_tokens = None
    output_tokens = None
    if isinstance(usage, dict):
        input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens")
        output_tokens = usage.get("output_tokens") or usage.get("completion_tokens")
        try:
            input_tokens = int(input_tokens) if input_tokens is not None else None
            output_tokens = int(output_tokens) if output_tokens is not None else None
        except (TypeError, ValueError):
            input_tokens = None
            output_tokens = None
    trace.cost = CostRecord(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        tool_calls=len(trace.tool_calls),
        latency_ms=latency_ms,
        estimated_cost=estimate_token_cost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_token_usd=inputs.input_token_usd,
            output_token_usd=inputs.output_token_usd,
        ),
        model=trace.model,
    )
    trace.evidence_ids = [item.evidence_id for item in ledger]
    trace.timings = timings
    trace.completed_at = utc_now()
    trace.decisions.append(f"independent_agents={decision.independent_agents}")
    if decision.independent_agents <= 1:
        trace.decisions.append("no_manufactured_consensus")
    trace.decisions.append(f"nse_mcp_commercial={NSE_MCP_COMMERCIAL_STATUS}")

    claims = assumption_claims + injected_claims
    if agent_result is not None:
        claims = claims + agent_result.claims

    failures = list(acquisition.unknown_fields)
    if identity_failure:
        failures.append(identity_failure)
    failures.extend(trace.errors)

    result = ResearchResult(
        identity_status="VERIFIED",
        isin=identity.isin,
        mic=identity.mic,
        company=identity.company_name,
        ticker=identity.ticker,
        evidence=ledger,
        price=None if acquisition.dataset is None else acquisition.dataset.price,
        claims=claims,
        unresolved=tuple(acquisition.unknown_fields) + tuple(acquisition.conflicts),
        mode=request.mode,
        plan=plan,
        verified_fields=tuple(item.field for item in verified),
        unknown_fields=acquisition.unknown_fields,
        conflicts=acquisition.conflicts,
        refresh_required=acquisition.refresh_required,
        sources_consulted=("security_master", "evidence_judge")
        + (("research_agent",) if agent_result else ()),
        failures=tuple(dict.fromkeys(failures)),
        research_started_at=started,
        research_finished_at=trace.completed_at,
        status="COMPLETE" if verified or acquisition.unknown_fields else "INCOMPLETE",
        provider=decision.provider,
        model_label=trace.model,
        evidence_ids=tuple(item.evidence_id for item in ledger),
        research_trace=trace,
        limitations=("AI narrative is not financial authority", "NSE MCP COMMERCIAL_USE_PENDING"),
        provenance="official_research_mesh",
        research_agents=decision.independent_agents,
    )
    return MeshRun(result, trace, identity, plan, acquisition)


def openai_transport_from_agent_error(error: str | None) -> str:
    return classify_openai_failure(error or "unavailable")


def resolve_research_identity(
    request: ResearchRequest,
    *,
    listing: SecurityListing | None = None,
) -> tuple[SecurityListing | None, str | None]:
    """Never silently substitute another company."""
    if listing is not None:
        if request.isin and request.isin.strip().upper() != listing.isin:
            return None, "SECURITY_AMBIGUOUS"
        if request.ticker and request.ticker.strip().upper() != listing.ticker:
            return None, "SECURITY_AMBIGUOUS"
        return listing, None
    query = request.ticker or request.company or request.isin or ""
    resolved = SecurityMasterService().resolve(
        query,
        exchange=request.exchange,
        isin=request.isin,
        mic=request.mic,
    )
    if resolved.status == "RESOLVED" and resolved.identity is not None:
        if request.ticker and resolved.identity.ticker != request.ticker.strip().upper():
            return None, "SECURITY_AMBIGUOUS"
        return resolved.identity, None
    if resolved.status == "AMBIGUOUS":
        return None, "SECURITY_AMBIGUOUS"
    if resolved.status == "UNSUPPORTED":
        return None, "UNSUPPORTED_SECURITY"
    if resolved.status == "REJECTED":
        return None, "SECURITY_UNKNOWN"
    return None, "SECURITY_NOT_FOUND"
