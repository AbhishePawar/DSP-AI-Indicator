"""Committee orchestrator (EPIC-A005)."""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from dsp_platform.institutional_committee.citations import build_committee_citations
from dsp_platform.institutional_committee.consensus import (
    build_committee_summary,
    build_consensus,
    build_minority_opinions,
)
from dsp_platform.institutional_committee.context import distribute_committee_context
from dsp_platform.institutional_committee.models import (
    COMMITTEE_SCHEMA_VERSION,
    COMMITTEE_SERVICE_VERSION,
    CommitteeReport,
    freeze_mapping,
    utc_now,
)
from dsp_platform.institutional_committee.registry import get_agent_registry
from dsp_platform.institutional_committee.serde import committee_report_to_dict
from dsp_platform.institutional_committee.validation import (
    InstitutionalCommitteeValidationError,
    validate_committee_report,
)

__all__ = [
    "COMMITTEE_SERVICE_VERSION",
    "CommitteeOrchestrator",
    "run_institutional_committee",
]


class CommitteeOrchestrator:
    """Deterministic multi-agent review over supplied immutable artifacts."""

    def run(
        self,
        *,
        subject: str,
        research_object: Mapping[str, Any] | None = None,
        report: Mapping[str, Any] | None = None,
        snapshots: Mapping[str, Any] | list[Any] | None = None,
        diffs: Mapping[str, Any] | list[Any] | None = None,
        copilot_response: Mapping[str, Any] | None = None,
        portfolio_intelligence: Mapping[str, Any] | None = None,
        monitoring_result: Mapping[str, Any] | None = None,
        workspace: Mapping[str, Any] | None = None,
        report_id: str | None = None,
        created_at: str | None = None,
    ) -> CommitteeReport:
        subject_norm = str(subject or "").strip()
        if not subject_norm:
            raise InstitutionalCommitteeValidationError("subject is required")

        ctx = distribute_committee_context(
            subject=subject_norm,
            research_object=research_object,
            report=report,
            snapshots=snapshots,
            diffs=diffs,
            copilot_response=copilot_response,
            portfolio_intelligence=portfolio_intelligence,
            monitoring_result=monitoring_result,
            workspace=workspace,
        )

        reviews = get_agent_registry().review_all(ctx)
        consensus = build_consensus(reviews)
        minority = build_minority_opinions(reviews, consensus)
        summary = build_committee_summary(
            subject=ctx.subject,
            reviews=reviews,
            consensus=consensus,
            minority_opinions=minority,
        )

        all_cites = [c for r in reviews for c in r.citations]
        citations = build_committee_citations(all_cites)

        created = created_at or utc_now().isoformat()
        rid = report_id or str(uuid.uuid4())

        provenance = {
            "source": "institutional_committee",
            "service_version": COMMITTEE_SERVICE_VERSION,
            "providers_called": False,
            "engines_called": False,
            "calculations_performed": False,
            "scoring_performed": False,
            "sources_present": dict(ctx.source_flags),
            "agent_order": [r.agent_id for r in reviews],
        }
        audit = {
            "report_id": rid,
            "created_at": created,
            "subject": ctx.subject,
            "agent_count": len(reviews),
            "minority_count": len(minority),
            "citation_count": len(citations),
            "consensus_stance": consensus.get("stance"),
        }
        limitations = (
            "Agents explain cited evidence only — no new research.",
            "No valuation math, scoring, optimisation, or recommendations.",
            "No providers or engines executed.",
            "Consensus is majority stance among usable reviews; ties prefer cautionary.",
        )

        result = CommitteeReport(
            report_id=rid,
            schema_version=COMMITTEE_SCHEMA_VERSION,
            service_version=COMMITTEE_SERVICE_VERSION,
            created_at=created,
            subject=ctx.subject,
            context=freeze_mapping(ctx.to_dict()) or freeze_mapping({}),
            reviews=reviews,
            consensus=consensus,
            minority_opinions=minority,
            committee_summary=summary,
            citations=citations,
            provenance=freeze_mapping(provenance) or freeze_mapping({}),
            audit=freeze_mapping(audit) or freeze_mapping({}),
            limitations=limitations,
        )
        validate_committee_report(result)
        return result


def run_institutional_committee(**kwargs: Any) -> dict[str, Any]:
    report = CommitteeOrchestrator().run(**kwargs)
    return committee_report_to_dict(report)
