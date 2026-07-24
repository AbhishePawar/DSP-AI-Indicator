"""Knowledge Graph Reporter — presentation only (I1.3).

Organizes existing engine / report artifacts for presentation.
Never constructs topology, derives relationships, generates lineage,
traverses, queries, persists, or mutates engine outputs (may append
presentation-only limitation notes).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from typing import Any

from knowledge_graph.engine import EngineResult, METHOD_TOPOLOGY
from knowledge_graph.enums import ReportingStatus
from knowledge_graph.exceptions import KnowledgeGraphError
from knowledge_graph.models import (
    EvidenceLink,
    GraphEdge,
    GraphMetadata,
    GraphNode,
    GraphProfile,
    GraphRelationship,
    GraphSummary,
    KnowledgeGraphReport,
    Lineage,
)
from knowledge_graph.validation import assert_unique_graph_ids

__all__ = [
    "CategoryCount",
    "CollectionStatistics",
    "KnowledgeGraphReporter",
    "ReportMetadata",
    "ReportingContext",
    "ReportingResult",
    "ValidationStatusView",
]

_DEFAULT_SUMMARY_SECTIONS: tuple[str, ...] = (
    "overview",
    "summary",
    "nodes",
    "edges",
    "relationships",
    "evidence_links",
    "lineage",
    "references",
    "metadata",
    "validation",
    "limitations",
)

_METHOD_PREFIX = "dsp.knowledge_graph.method."


@dataclass(frozen=True, slots=True)
class CategoryCount:
    """Presentation count for one taxonomy category — descriptive only."""

    category: str
    count: int


@dataclass(frozen=True, slots=True)
class CollectionStatistics:
    """Presentation statistics for one graph collection."""

    section_key: str
    title: str
    total: int
    by_category: tuple[CategoryCount, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "by_category", tuple(self.by_category))


@dataclass(frozen=True, slots=True)
class ValidationStatusView:
    """Presentation of structural validation outcomes — not a market score."""

    status: str
    identity_ok: bool
    metadata_present: bool
    method_id_present: bool
    provenance_complete: bool
    anchors_present: bool
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "notes", tuple(self.notes))


@dataclass(frozen=True, slots=True)
class ReportMetadata:
    """Presentation metadata — descriptive only."""

    graph_id: str
    as_of: str
    corpus_id: str
    node_count: int
    edge_count: int
    relationship_count: int
    evidence_link_count: int
    lineage_count: int
    section_keys: tuple[str, ...]
    owner: str | None = None
    method_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "section_keys", tuple(self.section_keys))


@dataclass(frozen=True, slots=True)
class ReportingContext:
    """Inputs for Knowledge Graph presentation.

    Consume ``KnowledgeGraphReport``, ``EngineResult``, and optionally
    ``GraphProfile`` for identity cross-checks. Never runs the engine.
    """

    report: KnowledgeGraphReport | None = None
    engine_result: EngineResult | None = None
    profile: GraphProfile | None = None
    summary_sections: tuple[str, ...] | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            self.report is None
            and self.engine_result is None
            and self.profile is None
        ):
            msg = (
                "missing graph identity: KnowledgeGraphReport, EngineResult, "
                "or GraphProfile required"
            )
            raise KnowledgeGraphError(msg)
        if self.summary_sections is not None:
            object.__setattr__(
                self, "summary_sections", tuple(self.summary_sections)
            )
        object.__setattr__(
            self,
            "limitations",
            tuple(n.strip() for n in self.limitations if n.strip()),
        )


@dataclass(frozen=True, slots=True)
class ReportingResult:
    """Presentation output — immutable, topology-free."""

    report: KnowledgeGraphReport
    status: ReportingStatus
    metadata: ReportMetadata
    summary: GraphSummary
    graph_metadata: GraphMetadata
    node_statistics: CollectionStatistics
    edge_statistics: CollectionStatistics
    relationship_statistics: CollectionStatistics
    evidence_link_statistics: CollectionStatistics
    lineage_statistics: CollectionStatistics
    validation_status: ValidationStatusView
    referenced_reports: tuple[str, ...]
    summary_sections: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "referenced_reports", tuple(self.referenced_reports)
        )
        object.__setattr__(self, "summary_sections", tuple(self.summary_sections))
        object.__setattr__(self, "warnings", tuple(self.warnings))


class KnowledgeGraphReporter:
    """Canonical presentation layer for Knowledge Graph.

    Formats existing artifacts — never constructs or mutates topology.
    """

    def validate_inputs(self, context: ReportingContext) -> None:
        """Reject invalid presentation inputs."""
        source = self._resolve_source(context)
        if not source.graph_id:
            msg = "missing graph identity: graph_id is required"
            raise KnowledgeGraphError(msg)

        if context.engine_result is not None and context.report is not None:
            if context.engine_result.graph_id != context.report.graph_id:
                msg = (
                    "engine/report identity mismatch: EngineResult "
                    f"{context.engine_result.graph_id!r} does not match "
                    f"report {context.report.graph_id!r}"
                )
                raise KnowledgeGraphError(msg)
            if context.engine_result.report.graph_id != context.report.graph_id:
                msg = (
                    "reporter/report mismatch: engine.report "
                    f"{context.engine_result.report.graph_id!r} vs "
                    f"{context.report.graph_id!r}"
                )
                raise KnowledgeGraphError(msg)

        if context.profile is not None:
            if context.profile.graph_id != source.graph_id:
                msg = (
                    "reporter/report mismatch: profile "
                    f"{context.profile.graph_id!r} vs report "
                    f"{source.graph_id!r}"
                )
                raise KnowledgeGraphError(msg)

        if source.metadata is None:
            msg = "missing metadata: GraphMetadata required"
            raise KnowledgeGraphError(msg)

        self._validate_provenance(source)
        self._validate_method_id(source)
        self._validate_references(source)

        sections = (
            context.summary_sections
            if context.summary_sections is not None
            else _DEFAULT_SUMMARY_SECTIONS
        )
        self._reject_duplicate_summary_sections(sections)

    def report(
        self,
        context: ReportingContext | KnowledgeGraphReport | EngineResult | GraphProfile,
    ) -> ReportingResult:
        """Build presentation artifacts from an existing report or engine result."""
        ctx = self._as_context(context)
        self.validate_inputs(ctx)
        source = self._resolve_source(ctx)
        warnings: list[str] = []

        sections = (
            ctx.summary_sections
            if ctx.summary_sections is not None
            else _DEFAULT_SUMMARY_SECTIONS
        )

        summary = source.summary
        graph_metadata = source.metadata

        node_statistics = self._node_statistics(source.nodes)
        edge_statistics = self._edge_statistics(source.edges)
        relationship_statistics = self._relationship_statistics(
            source.relationships
        )
        evidence_link_statistics = self._evidence_link_statistics(
            source.evidence_links
        )
        lineage_statistics = self._lineage_statistics(source.lineages)
        referenced_reports = self._collect_referenced_reports(source)
        method_id = self._extract_method_id(source)

        if not source.nodes:
            warnings.append("no nodes present on report.")
        if summary.node_count == 0:
            warnings.append("summary node_count is zero.")
        if len(source.nodes) != summary.node_count:
            warnings.append("summary node_count does not match nodes collection.")
        if len(source.edges) != summary.edge_count:
            warnings.append("summary edge_count does not match edges collection.")

        validation_status = self._build_validation_status(
            source=source,
            method_id=method_id,
        )

        limitations = tuple(
            dict.fromkeys(
                (
                    *source.limitations,
                    *summary.limitation_notes,
                    *ctx.limitations,
                    "KnowledgeGraphReport presentation only — "
                    "no topology construction performed by reporter.",
                )
            )
        )
        presented_report = replace(source, limitations=limitations)

        metadata = ReportMetadata(
            graph_id=source.graph_id,
            as_of=source.as_of,
            corpus_id=graph_metadata.corpus_id,
            node_count=summary.node_count,
            edge_count=summary.edge_count,
            relationship_count=summary.relationship_count,
            evidence_link_count=summary.evidence_link_count,
            lineage_count=summary.lineage_count,
            section_keys=sections,
            owner=graph_metadata.owner,
            method_id=method_id,
        )

        status = (
            ReportingStatus.PARTIAL if warnings else ReportingStatus.COMPLETE
        )
        if not source.nodes and not source.edges:
            status = ReportingStatus.EMPTY

        return ReportingResult(
            report=presented_report,
            status=status,
            metadata=metadata,
            summary=summary,
            graph_metadata=graph_metadata,
            node_statistics=node_statistics,
            edge_statistics=edge_statistics,
            relationship_statistics=relationship_statistics,
            evidence_link_statistics=evidence_link_statistics,
            lineage_statistics=lineage_statistics,
            validation_status=validation_status,
            referenced_reports=referenced_reports,
            summary_sections=sections,
            warnings=tuple(warnings),
        )

    def report_many(
        self,
        contexts: tuple[
            ReportingContext | KnowledgeGraphReport | EngineResult | GraphProfile,
            ...,
        ],
    ) -> tuple[ReportingResult, ...]:
        """Present many reports; reject duplicate graph identities."""
        resolved: list[ReportingContext] = [self._as_context(item) for item in contexts]
        assert_unique_graph_ids(
            tuple(self._resolve_source(ctx).graph_id for ctx in resolved)
        )
        return tuple(self.report(ctx) for ctx in resolved)

    def _as_context(
        self,
        context: ReportingContext | KnowledgeGraphReport | EngineResult | GraphProfile,
    ) -> ReportingContext:
        if isinstance(context, ReportingContext):
            return context
        if isinstance(context, EngineResult):
            return ReportingContext(engine_result=context)
        if isinstance(context, KnowledgeGraphReport):
            return ReportingContext(report=context)
        if isinstance(context, GraphProfile):
            return ReportingContext(profile=context)
        msg = (
            "ReportingContext, KnowledgeGraphReport, EngineResult, "
            "or GraphProfile required"
        )
        raise KnowledgeGraphError(msg)

    def _resolve_source(self, context: ReportingContext) -> KnowledgeGraphReport:
        if context.engine_result is not None:
            return context.engine_result.report
        if context.report is not None:
            return context.report
        if context.profile is not None:
            return self._report_from_profile(context.profile)
        msg = "missing graph identity: no report source"
        raise KnowledgeGraphError(msg)

    def _report_from_profile(self, profile: GraphProfile) -> KnowledgeGraphReport:
        """Wrap an existing profile for presentation — no topology changes."""
        summary = profile.summary or GraphSummary(
            node_count=len(profile.nodes),
            edge_count=len(profile.edges),
            relationship_count=len(profile.relationships),
            evidence_link_count=len(profile.evidence_links),
            lineage_count=len(profile.lineages),
        )
        return KnowledgeGraphReport(
            graph_id=profile.graph_id,
            summary=summary,
            metadata=profile.metadata,
            as_of=profile.metadata.as_of,
            nodes=profile.nodes,
            edges=profile.edges,
            relationships=profile.relationships,
            evidence_links=profile.evidence_links,
            lineages=profile.lineages,
            analysis_refs=profile.analysis_refs,
            decision_refs=profile.decision_refs,
            industry_evidence_refs=profile.industry_evidence_refs,
            comparison_refs=profile.comparison_refs,
            portfolio_refs=profile.portfolio_refs,
            risk_refs=profile.risk_refs,
            research_refs=profile.research_refs,
            quantitative_risk_refs=profile.quantitative_risk_refs,
            recommendation_refs=profile.recommendation_refs,
            workflow_refs=profile.workflow_refs,
            limitations=profile.notes,
        )

    def _node_statistics(
        self, nodes: tuple[GraphNode, ...]
    ) -> CollectionStatistics:
        return self._category_statistics(
            section_key="nodes",
            title="Node statistics",
            values=tuple(n.category.value for n in nodes),
        )

    def _edge_statistics(
        self, edges: tuple[GraphEdge, ...]
    ) -> CollectionStatistics:
        return self._category_statistics(
            section_key="edges",
            title="Edge statistics",
            values=tuple(e.relationship_category.value for e in edges),
        )

    def _relationship_statistics(
        self, relationships: tuple[GraphRelationship, ...]
    ) -> CollectionStatistics:
        return self._category_statistics(
            section_key="relationships",
            title="Relationship statistics",
            values=tuple(r.category.value for r in relationships),
        )

    def _evidence_link_statistics(
        self, links: tuple[EvidenceLink, ...]
    ) -> CollectionStatistics:
        return self._category_statistics(
            section_key="evidence_links",
            title="Evidence-link statistics",
            values=tuple(link.category.value for link in links),
        )

    def _lineage_statistics(
        self, lineages: tuple[Lineage, ...]
    ) -> CollectionStatistics:
        return self._category_statistics(
            section_key="lineage",
            title="Lineage statistics",
            values=tuple(lin.category.value for lin in lineages),
        )

    def _category_statistics(
        self,
        *,
        section_key: str,
        title: str,
        values: tuple[str, ...],
    ) -> CollectionStatistics:
        counts = Counter(values)
        by_category = tuple(
            CategoryCount(category=key, count=counts[key])
            for key in sorted(counts)
        )
        return CollectionStatistics(
            section_key=section_key,
            title=title,
            total=len(values),
            by_category=by_category,
        )

    def _collect_referenced_reports(
        self, source: KnowledgeGraphReport
    ) -> tuple[str, ...]:
        keys: list[str] = []
        for group in (
            source.analysis_refs,
            source.decision_refs,
            source.industry_evidence_refs,
            source.comparison_refs,
            source.portfolio_refs,
            source.risk_refs,
            source.research_refs,
            source.quantitative_risk_refs,
            source.recommendation_refs,
            source.workflow_refs,
        ):
            for ref in group:
                keys.append(ref.report_id)
        return tuple(dict.fromkeys(keys))

    def _extract_method_id(self, source: KnowledgeGraphReport) -> str | None:
        for item in (
            *source.nodes,
            *source.edges,
            *source.relationships,
            *source.evidence_links,
            *source.lineages,
        ):
            for token in item.provenance:
                if token.startswith(_METHOD_PREFIX):
                    return token
        for note in (*source.limitations, *source.summary.limitation_notes):
            if METHOD_TOPOLOGY in note:
                return METHOD_TOPOLOGY
        return None

    def _build_validation_status(
        self,
        *,
        source: KnowledgeGraphReport,
        method_id: str | None,
    ) -> ValidationStatusView:
        notes: list[str] = []
        identity_ok = bool(source.graph_id)
        metadata_present = source.metadata is not None
        method_id_present = method_id is not None or (
            not source.nodes and not source.edges
        )
        provenance_complete = self._provenance_complete(source)
        anchors_present = bool(
            source.recommendation_refs and source.workflow_refs
        )
        if not method_id_present:
            notes.append("method_id absent from provenance / limitations.")
        if not provenance_complete:
            notes.append("one or more graph elements lack provenance.")
        if not anchors_present:
            notes.append("required recommendation/workflow anchors missing.")
        if (
            identity_ok
            and metadata_present
            and method_id_present
            and provenance_complete
            and anchors_present
        ):
            status = "valid"
        else:
            status = "incomplete"
            notes.append("presentation validation incomplete.")
        return ValidationStatusView(
            status=status,
            identity_ok=identity_ok,
            metadata_present=metadata_present,
            method_id_present=method_id_present,
            provenance_complete=provenance_complete,
            anchors_present=anchors_present,
            notes=tuple(notes),
        )

    def _provenance_complete(self, source: KnowledgeGraphReport) -> bool:
        for item in (
            *source.nodes,
            *source.edges,
            *source.relationships,
            *source.evidence_links,
            *source.lineages,
        ):
            if not item.provenance:
                return False
        return True

    def _validate_provenance(self, source: KnowledgeGraphReport) -> None:
        for item in (
            *source.nodes,
            *source.edges,
            *source.relationships,
            *source.evidence_links,
            *source.lineages,
        ):
            if not item.provenance:
                msg = f"missing provenance: element {self._element_id(item)!r}"
                raise KnowledgeGraphError(msg)

    def _validate_method_id(self, source: KnowledgeGraphReport) -> None:
        if not source.nodes and not source.edges:
            return
        if self._extract_method_id(source) is None:
            msg = "missing method_id: topology method absent from provenance"
            raise KnowledgeGraphError(msg)

    def _validate_references(self, source: KnowledgeGraphReport) -> None:
        for group in (
            source.analysis_refs,
            source.decision_refs,
            source.industry_evidence_refs,
            source.comparison_refs,
            source.portfolio_refs,
            source.risk_refs,
            source.research_refs,
            source.quantitative_risk_refs,
            source.recommendation_refs,
            source.workflow_refs,
        ):
            for ref in group:
                if not ref.id or not ref.report_id or not ref.digest:
                    msg = "broken references: report reference incomplete"
                    raise KnowledgeGraphError(msg)
        if not source.recommendation_refs or not source.workflow_refs:
            msg = "broken references: recommendation and workflow anchors required"
            raise KnowledgeGraphError(msg)

    def _element_id(self, item: Any) -> str:
        for attr in (
            "node_id",
            "edge_id",
            "relationship_id",
            "link_id",
            "lineage_id",
        ):
            value = getattr(item, attr, None)
            if value is not None:
                return str(value)
        return repr(item)

    def _reject_duplicate_summary_sections(self, sections: tuple[str, ...]) -> None:
        seen: set[str] = set()
        for raw in sections:
            key = raw.strip().lower()
            if not key:
                msg = "duplicate report sections: empty section key"
                raise KnowledgeGraphError(msg)
            if key in seen:
                msg = f"duplicate report sections: {raw!r}"
                raise KnowledgeGraphError(msg)
            seen.add(key)
