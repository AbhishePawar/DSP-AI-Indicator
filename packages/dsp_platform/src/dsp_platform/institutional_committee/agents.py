"""Independent agent reviews over distributed context (EPIC-A005).

Agents explain existing evidence only — no calculations, valuation math,
scoring, or fabricated conclusions.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from dsp_platform.institutional_committee.citations import citation
from dsp_platform.institutional_committee.context import section_available
from dsp_platform.institutional_committee.models import (
    UNAVAILABLE_MESSAGE,
    AgentReview,
    CommitteeContext,
    freeze_mapping,
)

__all__ = [
    "AGENT_SPECS",
    "confidence_from_coverage",
    "review_agent",
]

AgentFn = Callable[[CommitteeContext], AgentReview]


def confidence_from_coverage(*, available: int, total: int) -> str:
    """Categorical confidence from evidence coverage — not a numeric score."""
    if total <= 0 or available <= 0:
        return "unavailable"
    if available == total:
        return "high"
    if available >= max(1, total // 2):
        return "medium"
    return "low"


def _section_citations(
    ctx: CommitteeContext,
    agent_id: str,
    sections: tuple[str, ...],
) -> list[Mapping[str, Any]]:
    cites: list[Mapping[str, Any]] = []
    for name in sections:
        row = ctx.section_index.get(name) if isinstance(ctx.section_index, Mapping) else None
        available = isinstance(row, Mapping) and bool(row.get("available"))
        cites.append(
            citation(
                source_kind="research_object",
                section=name,
                path=f"research_object.{name}",
                available=available,
                agent_id=agent_id,
                symbol=ctx.subject,
                label=f"research_object/{name}",
            )
        )
    return cites


def _base_review(
    *,
    agent_id: str,
    agent_name: str,
    focus_sections: tuple[str, ...],
    ctx: CommitteeContext,
    findings: list[str],
    stance: str,
    extra_citations: list[Mapping[str, Any]] | None = None,
) -> AgentReview:
    available_count = sum(
        1 for s in focus_sections if section_available(ctx.section_index, s)
    )
    confidence = confidence_from_coverage(
        available=available_count, total=len(focus_sections)
    )
    if stance != "unavailable" and available_count == 0 and not extra_citations:
        stance = "unavailable"
        confidence = "unavailable"
        findings = [UNAVAILABLE_MESSAGE]
        summary = UNAVAILABLE_MESSAGE
    elif stance == "unavailable":
        summary = UNAVAILABLE_MESSAGE
        if not findings:
            findings = [UNAVAILABLE_MESSAGE]
    else:
        summary = (
            f"{agent_name} reviewed {available_count}/{len(focus_sections)} "
            f"focus sections for {ctx.subject}."
        )
    cites = _section_citations(ctx, agent_id, focus_sections)
    if extra_citations:
        cites.extend(extra_citations)
    if not cites:
        cites.append(
            citation(
                source_kind="institutional_committee",
                section="review",
                path=f"committee.{agent_id}",
                available=False,
                agent_id=agent_id,
                symbol=ctx.subject,
            )
        )
    return AgentReview(
        agent_id=agent_id,
        agent_name=agent_name,
        stance=stance,
        confidence=confidence,
        summary=summary,
        findings=tuple(findings),
        focus_sections=focus_sections,
        citations=tuple(cites),
        provenance=freeze_mapping(
            {
                "source": "institutional_committee",
                "agent_id": agent_id,
                "via": "committee_context",
                "providers_called": False,
                "engines_called": False,
            }
        )
        or freeze_mapping({}),
    )


def _finding_for_section(ctx: CommitteeContext, name: str) -> str:
    row = ctx.section_index.get(name)
    if not isinstance(row, Mapping) or not row.get("available"):
        return f"{name}: {UNAVAILABLE_MESSAGE}"
    status = row.get("status") or "ok"
    return f"{name}: available (status={status})."


def _review_lens(
    *,
    agent_id: str,
    agent_name: str,
    focus_sections: tuple[str, ...],
    ctx: CommitteeContext,
    caution_if_missing: tuple[str, ...] = (),
) -> AgentReview:
    findings = [_finding_for_section(ctx, s) for s in focus_sections]
    available = [s for s in focus_sections if section_available(ctx.section_index, s)]
    missing_critical = [
        s for s in caution_if_missing if not section_available(ctx.section_index, s)
    ]
    if not available:
        stance = "unavailable"
    elif missing_critical:
        stance = "cautionary"
        findings.append(
            "Critical focus evidence missing: " + ", ".join(missing_critical) + "."
        )
    else:
        stance = "supportive"
    return _base_review(
        agent_id=agent_id,
        agent_name=agent_name,
        focus_sections=focus_sections,
        ctx=ctx,
        findings=findings,
        stance=stance,
    )


def review_buffett(ctx: CommitteeContext) -> AgentReview:
    # Durable business quality + MoS evidence (pass-through availability only)
    return _review_lens(
        agent_id="buffett",
        agent_name="Buffett Agent",
        focus_sections=("business_quality", "margin_of_safety", "identity"),
        ctx=ctx,
        caution_if_missing=("business_quality", "margin_of_safety"),
    )


def review_graham(ctx: CommitteeContext) -> AgentReview:
    return _review_lens(
        agent_id="graham",
        agent_name="Graham Agent",
        focus_sections=("margin_of_safety", "valuation", "financial_statements"),
        ctx=ctx,
        caution_if_missing=("margin_of_safety", "financial_statements"),
    )


def review_lynch(ctx: CommitteeContext) -> AgentReview:
    return _review_lens(
        agent_id="lynch",
        agent_name="Lynch Agent",
        focus_sections=("identity", "market_data", "recommendation"),
        ctx=ctx,
        caution_if_missing=("identity",),
    )


def review_quality(ctx: CommitteeContext) -> AgentReview:
    return _review_lens(
        agent_id="quality",
        agent_name="Quality Agent",
        focus_sections=("business_quality", "explainability"),
        ctx=ctx,
        caution_if_missing=("business_quality",),
    )


def review_risk(ctx: CommitteeContext) -> AgentReview:
    return _review_lens(
        agent_id="risk",
        agent_name="Risk Agent",
        focus_sections=("risk", "scenarios", "corporate_actions"),
        ctx=ctx,
        caution_if_missing=("risk",),
    )


def review_governance(ctx: CommitteeContext) -> AgentReview:
    findings: list[str] = []
    focus = ("audit", "explainability", "institutional_report")
    for s in focus:
        findings.append(_finding_for_section(ctx, s))
    extra: list[Mapping[str, Any]] = []
    if ctx.report is not None:
        extra.append(
            citation(
                source_kind="institutional_report",
                section="report",
                path="institutional_report",
                available=True,
                agent_id="governance",
                ref_id=str(ctx.report.get("report_id") or "") or None,
            )
        )
    available = [s for s in focus if section_available(ctx.section_index, s)]
    if not available:
        stance = "unavailable"
    elif not section_available(ctx.section_index, "audit"):
        stance = "cautionary"
        findings.append("Audit section unavailable in research object.")
    else:
        stance = "supportive"
    return _base_review(
        agent_id="governance",
        agent_name="Governance Agent",
        focus_sections=focus,
        ctx=ctx,
        findings=findings,
        stance=stance,
        extra_citations=extra,
    )


def review_valuation(ctx: CommitteeContext) -> AgentReview:
    # Reports presence of valuation/MoS sections only — never computes values.
    return _review_lens(
        agent_id="valuation",
        agent_name="Valuation Agent",
        focus_sections=("valuation", "margin_of_safety"),
        ctx=ctx,
        caution_if_missing=("valuation", "margin_of_safety"),
    )


def review_devils_advocate(ctx: CommitteeContext) -> AgentReview:
    findings: list[str] = []
    extra: list[Mapping[str, Any]] = []
    caution = False

    # Conflicts from diffs
    for diff in ctx.diffs:
        summary = (
            diff.get("change_summary")
            if isinstance(diff.get("change_summary"), Mapping)
            else {}
        )
        if summary.get("identical_content") is False:
            caution = True
            did = str(diff.get("diff_id") or "diff")
            findings.append(f"Research diff {did} reports non-identical content.")
            extra.append(
                citation(
                    source_kind="research_diff",
                    section="change_summary",
                    path="research_diff.change_summary",
                    available=True,
                    agent_id="devils_advocate",
                    ref_id=did,
                )
            )

    # Monitoring alerts
    if ctx.monitoring_result is not None:
        alerts = ctx.monitoring_result.get("alerts") or []
        active = [
            a
            for a in alerts
            if isinstance(a, Mapping) and a.get("severity") in {"watch", "important", "unavailable"}
        ]
        if active:
            caution = True
            findings.append(f"Monitoring reports {len(active)} active alert(s).")
            extra.append(
                citation(
                    source_kind="research_monitoring",
                    section="alerts",
                    path="research_monitoring.alerts",
                    available=True,
                    agent_id="devils_advocate",
                    ref_id=str(ctx.monitoring_result.get("result_id") or "") or None,
                )
            )

    # Portfolio missing research
    if ctx.portfolio_intelligence is not None:
        missing = ctx.portfolio_intelligence.get("missing_research") or []
        if isinstance(missing, list) and missing:
            caution = True
            findings.append(
                f"Portfolio intelligence lists {len(missing)} missing research link(s)."
            )
            extra.append(
                citation(
                    source_kind="portfolio_intelligence",
                    section="missing_research",
                    path="portfolio_intelligence.missing_research",
                    available=True,
                    agent_id="devils_advocate",
                    ref_id=str(ctx.portfolio_intelligence.get("result_id") or "")
                    or None,
                )
            )

    # Core section gaps
    for name in ("risk", "margin_of_safety", "business_quality"):
        if not section_available(ctx.section_index, name):
            caution = True
            findings.append(f"Core section gap: {name}: {UNAVAILABLE_MESSAGE}")
            extra.append(
                citation(
                    source_kind="research_object",
                    section=name,
                    path=f"research_object.{name}",
                    available=False,
                    agent_id="devils_advocate",
                    symbol=ctx.subject,
                )
            )

    focus = ("risk", "margin_of_safety", "business_quality")
    if not findings and not extra:
        findings = [
            "No conflict signals found in supplied diffs, monitoring, or portfolio gaps."
        ]
        stance = "supportive"
        # still cite focus sections
    elif caution:
        stance = "cautionary"
    else:
        stance = "supportive"

    # If literally no sources at all
    if not any(ctx.source_flags.values()):
        stance = "unavailable"
        findings = [UNAVAILABLE_MESSAGE]

    return _base_review(
        agent_id="devils_advocate",
        agent_name="Devil's Advocate Agent",
        focus_sections=focus,
        ctx=ctx,
        findings=findings,
        stance=stance,
        extra_citations=extra,
    )


AGENT_SPECS: tuple[tuple[str, str, AgentFn], ...] = (
    ("buffett", "Buffett Agent", review_buffett),
    ("graham", "Graham Agent", review_graham),
    ("lynch", "Lynch Agent", review_lynch),
    ("quality", "Quality Agent", review_quality),
    ("risk", "Risk Agent", review_risk),
    ("governance", "Governance Agent", review_governance),
    ("valuation", "Valuation Agent", review_valuation),
    ("devils_advocate", "Devil's Advocate Agent", review_devils_advocate),
)


def review_agent(agent_id: str, ctx: CommitteeContext) -> AgentReview:
    for aid, _name, fn in AGENT_SPECS:
        if aid == agent_id:
            return fn(ctx)
    raise ValueError(f"unknown agent_id {agent_id!r}")
