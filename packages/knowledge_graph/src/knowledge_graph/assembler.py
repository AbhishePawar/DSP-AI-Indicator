"""Knowledge Graph Assembler — construction / citation bind only (I1.1).

Builds immutable GraphProfile (+ KnowledgeGraphReport skeleton) with empty
graph collections and validated anchors. Never infers relationships,
traverses, calculates lineage, or queries.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ValidationError

from knowledge_graph.enums import AssemblyStatus
from knowledge_graph.exceptions import KnowledgeGraphError
from knowledge_graph.models import (
    GraphIdentity,
    GraphMetadata,
    GraphProfile,
    GraphSummary,
    KnowledgeGraphReport,
)
from knowledge_graph.refs import (
    AnalysisReference,
    ComparisonReference,
    DecisionReference,
    IndustryEvidenceReference,
    PortfolioReference,
    QuantitativeRiskReference,
    RecommendationReference,
    ResearchReference,
    RiskReference,
    WorkflowReference,
)
from knowledge_graph.validation import assert_unique_graph_ids

__all__ = [
    "AssemblyContext",
    "AssemblyResult",
    "KnowledgeGraphAssembler",
]


@dataclass(frozen=True, slots=True)
class AssemblyContext:
    """Inputs for deterministic GraphProfile / report skeleton construction."""

    identity: GraphIdentity
    metadata: GraphMetadata
    recommendation_refs: tuple[RecommendationReference, ...]
    workflow_refs: tuple[WorkflowReference, ...]
    analysis_refs: tuple[AnalysisReference, ...] = ()
    decision_refs: tuple[DecisionReference, ...] = ()
    industry_evidence_refs: tuple[IndustryEvidenceReference, ...] = ()
    comparison_refs: tuple[ComparisonReference, ...] = ()
    portfolio_refs: tuple[PortfolioReference, ...] = ()
    risk_refs: tuple[RiskReference, ...] = ()
    research_refs: tuple[ResearchReference, ...] = ()
    quantitative_risk_refs: tuple[QuantitativeRiskReference, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.identity is None:
            msg = "identity is required"
            raise ValidationError(msg)
        if self.metadata is None:
            msg = "metadata is required"
            raise ValidationError(msg)
        object.__setattr__(
            self, "recommendation_refs", tuple(self.recommendation_refs)
        )
        object.__setattr__(self, "workflow_refs", tuple(self.workflow_refs))
        object.__setattr__(self, "analysis_refs", tuple(self.analysis_refs))
        object.__setattr__(self, "decision_refs", tuple(self.decision_refs))
        object.__setattr__(
            self, "industry_evidence_refs", tuple(self.industry_evidence_refs)
        )
        object.__setattr__(self, "comparison_refs", tuple(self.comparison_refs))
        object.__setattr__(self, "portfolio_refs", tuple(self.portfolio_refs))
        object.__setattr__(self, "risk_refs", tuple(self.risk_refs))
        object.__setattr__(self, "research_refs", tuple(self.research_refs))
        object.__setattr__(
            self, "quantitative_risk_refs", tuple(self.quantitative_risk_refs)
        )
        object.__setattr__(
            self, "notes", tuple(n.strip() for n in self.notes if n.strip())
        )


@dataclass(frozen=True, slots=True)
class AssemblyResult:
    """Assembler output — structural profile / report skeleton only."""

    profile: GraphProfile
    report: KnowledgeGraphReport
    status: AssemblyStatus
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "warnings", tuple(self.warnings))


class KnowledgeGraphAssembler:
    """Canonical constructor for immutable Knowledge Graph skeletons.

    Construction and reference validation only — no inference or traversal.
    """

    def validate_inputs(self, context: AssemblyContext) -> None:
        """Reject invalid assembly inputs before construction."""
        if context.identity is None:
            msg = "missing GraphIdentity"
            raise KnowledgeGraphError(msg)
        if not context.identity.graph_id:
            msg = "missing GraphIdentity: empty graph_id"
            raise KnowledgeGraphError(msg)
        if not context.identity.graph_name:
            msg = "missing GraphIdentity: empty graph_name"
            raise KnowledgeGraphError(msg)
        if context.metadata is None:
            msg = "missing GraphMetadata"
            raise KnowledgeGraphError(msg)
        if not context.metadata.corpus_id:
            msg = "missing GraphMetadata: empty corpus_id"
            raise KnowledgeGraphError(msg)
        if not context.metadata.as_of:
            msg = "missing GraphMetadata: empty as_of"
            raise KnowledgeGraphError(msg)

        if not context.recommendation_refs:
            msg = (
                "missing Recommendation anchor: at least one "
                "RecommendationReference required"
            )
            raise KnowledgeGraphError(msg)
        if not context.workflow_refs:
            msg = (
                "missing Workflow anchor: at least one WorkflowReference required"
            )
            raise KnowledgeGraphError(msg)

        self._validate_ref_group("recommendation_refs", context.recommendation_refs)
        self._validate_ref_group("workflow_refs", context.workflow_refs)
        self._validate_ref_group("analysis_refs", context.analysis_refs)
        self._validate_ref_group("decision_refs", context.decision_refs)
        self._validate_ref_group(
            "industry_evidence_refs", context.industry_evidence_refs
        )
        self._validate_ref_group("comparison_refs", context.comparison_refs)
        self._validate_ref_group("portfolio_refs", context.portfolio_refs)
        self._validate_ref_group("risk_refs", context.risk_refs)
        self._validate_ref_group("research_refs", context.research_refs)
        self._validate_ref_group(
            "quantitative_risk_refs", context.quantitative_risk_refs
        )

    def assemble(self, context: AssemblyContext) -> AssemblyResult:
        """Construct immutable profile and empty KnowledgeGraphReport skeleton."""
        self.validate_inputs(context)

        warnings: list[str] = []
        optional_coverage = sum(
            1
            for group in (
                context.analysis_refs,
                context.decision_refs,
                context.industry_evidence_refs,
                context.comparison_refs,
                context.portfolio_refs,
                context.risk_refs,
                context.research_refs,
                context.quantitative_risk_refs,
            )
            if group
        )
        if optional_coverage == 0:
            warnings.append(
                "optional upstream refs absent; skeleton cites anchors only."
            )

        summary = GraphSummary(
            node_count=0,
            edge_count=0,
            relationship_count=0,
            evidence_link_count=0,
            lineage_count=0,
            limitation_notes=(
                "Assembly skeleton only — empty nodes / edges / relationships / "
                "evidence links / lineage. Knowledge Graph Engine (I1.2) "
                "populates graph structure.",
                *context.notes,
            ),
        )

        profile = GraphProfile(
            identity=context.identity,
            metadata=context.metadata,
            nodes=(),
            edges=(),
            relationships=(),
            evidence_links=(),
            lineages=(),
            summary=summary,
            analysis_refs=context.analysis_refs,
            decision_refs=context.decision_refs,
            industry_evidence_refs=context.industry_evidence_refs,
            comparison_refs=context.comparison_refs,
            portfolio_refs=context.portfolio_refs,
            risk_refs=context.risk_refs,
            research_refs=context.research_refs,
            quantitative_risk_refs=context.quantitative_risk_refs,
            recommendation_refs=context.recommendation_refs,
            workflow_refs=context.workflow_refs,
            notes=context.notes,
        )

        report = KnowledgeGraphReport(
            graph_id=context.identity.graph_id,
            summary=summary,
            metadata=context.metadata,
            as_of=context.metadata.as_of,
            nodes=(),
            edges=(),
            relationships=(),
            evidence_links=(),
            lineages=(),
            analysis_refs=context.analysis_refs,
            decision_refs=context.decision_refs,
            industry_evidence_refs=context.industry_evidence_refs,
            comparison_refs=context.comparison_refs,
            portfolio_refs=context.portfolio_refs,
            risk_refs=context.risk_refs,
            research_refs=context.research_refs,
            quantitative_risk_refs=context.quantitative_risk_refs,
            recommendation_refs=context.recommendation_refs,
            workflow_refs=context.workflow_refs,
            limitations=(
                "KnowledgeGraphReport skeleton — no inferred graph content yet.",
                *summary.limitation_notes,
            ),
        )

        status = (
            AssemblyStatus.PARTIAL if warnings else AssemblyStatus.COMPLETE
        )
        return AssemblyResult(
            profile=profile,
            report=report,
            status=status,
            warnings=tuple(warnings),
        )

    def assemble_many(
        self, contexts: tuple[AssemblyContext, ...]
    ) -> tuple[AssemblyResult, ...]:
        """Assemble many contexts; reject duplicate graph identities."""
        assert_unique_graph_ids(
            tuple(ctx.identity.graph_id for ctx in contexts)
        )
        return tuple(self.assemble(context) for context in contexts)

    def _validate_ref_group(self, name: str, refs: tuple[object, ...]) -> None:
        seen_ids: set[str] = set()
        seen_reports: set[str] = set()
        for ref in refs:
            if ref is None:
                msg = f"missing required references: {name} contains None"
                raise KnowledgeGraphError(msg)
            ref_id = getattr(ref, "id", "")
            report_id = getattr(ref, "report_id", "")
            digest = getattr(ref, "digest", "")
            if not ref_id:
                msg = f"broken report ids: {name} missing id"
                raise KnowledgeGraphError(msg)
            if not report_id:
                msg = f"broken report ids: {name} missing report_id"
                raise KnowledgeGraphError(msg)
            if not digest or len(digest) < 8:
                msg = f"broken digests: {name} digest invalid"
                raise KnowledgeGraphError(msg)
            if ref_id in seen_ids:
                msg = f"duplicate report references: {name} id {ref_id!r}"
                raise KnowledgeGraphError(msg)
            if report_id in seen_reports:
                msg = f"duplicate report references: {name} report_id {report_id!r}"
                raise KnowledgeGraphError(msg)
            seen_ids.add(ref_id)
            seen_reports.add(report_id)
