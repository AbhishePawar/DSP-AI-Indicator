"""Bounded generic research loop. Terminates; never infinite retry."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from data_engine.official_research.company_sources import resolve_company_sources
from data_engine.official_research.forensic_artifacts import is_promotable_artifact
from data_engine.official_research.models import ResearchRequest, utc_now
from data_engine.official_research.research_failures import ResearchFailure
from data_engine.official_research.research_plan import ResearchPlan, build_research_plan
from data_engine.official_research.source_policy import SourcePolicy, classify_source_url
from data_engine.security_master.models import SecurityListing

__all__ = ["MAX_RESEARCH_LOOPS", "ResearchLoopResult", "run_research_loop"]

MAX_RESEARCH_LOOPS = 2


@dataclass(frozen=True, slots=True)
class ResearchLoopResult:
    plan: ResearchPlan
    sources_consulted: tuple[str, ...]
    discovered_urls: tuple[str, ...]
    iterations: int
    stopped_reason: str
    started_at: datetime
    finished_at: datetime
    failures: tuple[ResearchFailure, ...]


def run_research_loop(
    listing: SecurityListing,
    request: ResearchRequest,
    *,
    existing_verified: tuple[str, ...] = (),
    stale_fields: tuple[str, ...] = (),
    artifact_path: str | None = None,
    policy: SourcePolicy | None = None,
) -> ResearchLoopResult:
    """Identity → plan → existing evidence → discover missing sources.

    Does not download in this loop. Retrieval stays in acquire_primary_documents.
    Stale forensic artifacts cannot enter.
    """
    started = utc_now()
    if artifact_path:
        assert not is_promotable_artifact(artifact_path)
    policy = policy or SourcePolicy()
    sources = resolve_company_sources(listing)
    plan = build_research_plan(
        listing,
        request,
        existing_verified=existing_verified,
        stale_fields=stale_fields,
        sources=sources,
        artifact_path=artifact_path,
    )
    consulted: list[str] = ["security_master"]
    discovered: list[str] = []
    failures = list(plan.failures)
    iterations = 0
    stopped = "complete" if plan.status == "COMPLETE" else "evidence unavailable"
    while iterations < MAX_RESEARCH_LOOPS and plan.missing_fields:
        iterations += 1
        consulted.append("company_source_registry")
        consulted.append("nse_primary")
        for url in sources.candidate_urls:
            kind = classify_source_url(url)
            if kind in {"forbidden", "secondary"}:
                continue
            if kind == "unknown":
                kind = classify_source_url(url, source_type="company_ir")
            if kind == "approved_research" and not policy.may_cross_check(url):
                continue
            if kind not in {"primary", "approved_research"}:
                continue
            discovered.append(url)
        for url in (
            sources.investor_relations_url,
            sources.annual_report_url,
            sources.financial_results_url,
        ):
            if url and url not in discovered:
                kind = classify_source_url(url, source_type="company_ir")
                if kind == "primary":
                    discovered.append(url)
        if sources.nse_announcements_url:
            discovered.append(sources.nse_announcements_url)
        if sources.nse_financial_results_url:
            discovered.append(sources.nse_financial_results_url)
        if not discovered:
            failures.append(
                ResearchFailure(
                    "PRIMARY_SOURCE_UNAVAILABLE",
                    "no primary locator; approved research cannot substitute as VERIFIED",
                )
            )
            stopped = "primary unavailable"
            break
        if not plan.missing_fields:
            stopped = "complete"
            break
        stopped = "evidence unavailable"
        break
    finished = utc_now()
    return ResearchLoopResult(
        plan=plan,
        sources_consulted=tuple(dict.fromkeys(consulted)),
        discovered_urls=tuple(dict.fromkeys(discovered)),
        iterations=iterations,
        stopped_reason=stopped,
        started_at=started,
        finished_at=finished,
        failures=tuple(failures),
    )
