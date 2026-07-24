"""AI Copilot Reporter — presentation only (J1.3).

Transforms immutable ExplanationResult into CopilotResponse.
Never generates explanations, invokes LLMs, traverses Knowledge Graph,
mutates reports, executes workflows, persists, or calculates.
"""

from __future__ import annotations

from dataclasses import dataclass

from copilot.conversation import ExplanationInput
from copilot.enums import (
    ConfidenceLevel,
    ExplanationStatus,
    ResponseStatus,
)
from copilot.exceptions import CopilotError
from copilot.explanation import ExplanationResult
from copilot.models import (
    CopilotMetadata,
    CopilotResponse,
    CopilotSummary,
    Explanation,
)
from copilot.validation import assert_unique_copilot_ids

__all__ = [
    "CategoryCount",
    "CollectionStatistics",
    "CopilotReporter",
    "ReportFormatter",
    "ReportingContext",
    "ReportingResult",
    "ResponseFormatter",
    "ResponseMetadata",
    "ResponseMetadataBuilder",
    "ValidationStatusView",
]

_DEFAULT_SECTIONS: tuple[str, ...] = (
    "overview",
    "executive_summary",
    "key_reasons",
    "risks",
    "supporting_evidence",
    "citations",
    "confidence",
    "provenance",
    "metadata",
    "validation",
    "limitations",
)

_PRESENTATION_NOTE = (
    "CopilotResponse presentation only — no explanation generation by reporter."
)


@dataclass(frozen=True, slots=True)
class CategoryCount:
    """Presentation count for one section category — descriptive only."""

    category: str
    count: int


@dataclass(frozen=True, slots=True)
class CollectionStatistics:
    """Presentation statistics for formatted response collections."""

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
    explanation_present: bool
    citations_present: bool
    provenance_complete: bool
    metadata_present: bool
    confidence_valid: bool
    ordering_consistent: bool
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "notes", tuple(self.notes))


@dataclass(frozen=True, slots=True)
class ResponseMetadata:
    """Presentation metadata — descriptive only."""

    copilot_id: str
    as_of: str
    session_id: str
    status: ResponseStatus
    confidence: ConfidenceLevel
    citation_count: int
    reason_count: int
    risk_count: int
    evidence_count: int
    section_keys: tuple[str, ...]
    owner: str | None = None
    method_id: str = "dsp.copilot.method.reporting.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "section_keys", tuple(self.section_keys))


@dataclass(frozen=True, slots=True)
class ReportingContext:
    """Inputs for Copilot presentation.

    Consume ``ExplanationResult`` + ``ExplanationInput`` (+ optional metadata).
    Never runs explanation or conversation engines.
    """

    explanation_result: ExplanationResult
    explanation_input: ExplanationInput
    metadata: CopilotMetadata | None = None
    summary_sections: tuple[str, ...] | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.explanation_result is None:
            msg = "ExplanationResult is required"
            raise CopilotError(msg)
        if self.explanation_input is None:
            msg = "ExplanationInput is required"
            raise CopilotError(msg)
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
    """Presentation output — immutable CopilotResponse plus section views."""

    response: CopilotResponse
    status: ResponseStatus
    metadata: ResponseMetadata
    statistics: CollectionStatistics
    validation_status: ValidationStatusView
    executive_summary: str
    key_reasons: tuple[str, ...]
    risks: tuple[str, ...]
    supporting_evidence: tuple[str, ...]
    citations: tuple[str, ...]
    confidence: ConfidenceLevel
    provenance: tuple[str, ...]
    summary_sections: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "key_reasons", tuple(self.key_reasons))
        object.__setattr__(self, "risks", tuple(self.risks))
        object.__setattr__(
            self, "supporting_evidence", tuple(self.supporting_evidence)
        )
        object.__setattr__(self, "citations", tuple(self.citations))
        object.__setattr__(self, "provenance", tuple(self.provenance))
        object.__setattr__(self, "summary_sections", tuple(self.summary_sections))
        object.__setattr__(self, "warnings", tuple(self.warnings))


class ReportFormatter:
    """Formats ExplanationResult sections into ordered presentation tuples."""

    def format(self, result: ExplanationResult) -> tuple[
        str,
        tuple[str, ...],
        tuple[str, ...],
        tuple[str, ...],
        tuple[str, ...],
        ConfidenceLevel,
        tuple[str, ...],
    ]:
        """Return summary, reasons, risks, evidence, citations, confidence, provenance."""
        if result is None or result.explanation is None:
            msg = "missing explanation"
            raise CopilotError(msg)
        reasons = tuple(dict.fromkeys(r.strip() for r in result.key_reasons if r.strip()))
        risks = tuple(dict.fromkeys(r.strip() for r in result.risks if r.strip()))
        evidence = tuple(
            dict.fromkeys(e.strip() for e in result.supporting_evidence if e.strip())
        )
        citations = tuple(
            dict.fromkeys(c.strip().lower() for c in result.citations if c.strip())
        )
        provenance = tuple(
            dict.fromkeys(p.strip() for p in result.provenance if p.strip())
        )
        summary = result.executive_summary.strip()
        if not summary:
            msg = "missing explanation: empty executive_summary"
            raise CopilotError(msg)
        return (
            summary,
            reasons,
            risks,
            evidence,
            citations,
            result.confidence,
            provenance,
        )


class ResponseMetadataBuilder:
    """Builds presentation ResponseMetadata — no business scoring."""

    def build(
        self,
        *,
        copilot_id: str,
        as_of: str,
        session_id: str,
        status: ResponseStatus,
        confidence: ConfidenceLevel,
        citation_count: int,
        reason_count: int,
        risk_count: int,
        evidence_count: int,
        section_keys: tuple[str, ...],
        owner: str | None = None,
    ) -> ResponseMetadata:
        if not copilot_id.strip():
            msg = "invalid metadata: empty copilot_id"
            raise CopilotError(msg)
        if not as_of.strip():
            msg = "invalid metadata: empty as_of"
            raise CopilotError(msg)
        if confidence not in ConfidenceLevel:
            msg = f"invalid confidence: {confidence!r}"
            raise CopilotError(msg)
        return ResponseMetadata(
            copilot_id=copilot_id.strip().lower(),
            as_of=as_of.strip(),
            session_id=session_id.strip().lower(),
            status=status,
            confidence=confidence,
            citation_count=citation_count,
            reason_count=reason_count,
            risk_count=risk_count,
            evidence_count=evidence_count,
            section_keys=section_keys,
            owner=None if owner is None else owner.strip() or None,
        )


class ResponseFormatter:
    """Assembles immutable CopilotResponse from formatted sections."""

    def format(
        self,
        *,
        explanation_input: ExplanationInput,
        explanation: Explanation,
        metadata: CopilotMetadata,
        status: ResponseStatus,
        summary: CopilotSummary,
        limitations: tuple[str, ...],
    ) -> CopilotResponse:
        bundle = explanation_input.context_bundle
        return CopilotResponse(
            copilot_id=explanation_input.copilot_id,
            summary=summary,
            metadata=metadata,
            as_of=explanation_input.as_of,
            status=status,
            knowledge_graph_ref=bundle.knowledge_graph_ref,
            session_id=explanation_input.session_id,
            intent=explanation_input.intent,
            context_bundle=bundle,
            explanation=explanation,
            analysis_refs=bundle.analysis_refs,
            decision_refs=bundle.decision_refs,
            industry_evidence_refs=bundle.industry_evidence_refs,
            comparison_refs=bundle.comparison_refs,
            portfolio_refs=bundle.portfolio_refs,
            risk_refs=bundle.risk_refs,
            research_refs=bundle.research_refs,
            quantitative_risk_refs=bundle.quantitative_risk_refs,
            recommendation_refs=bundle.recommendation_refs,
            workflow_refs=bundle.workflow_refs,
            limitations=limitations,
        )


class CopilotReporter:
    """Canonical presentation layer for AI Copilot.

    Formats ExplanationResult into CopilotResponse — never explains or invokes LLM.
    """

    def __init__(
        self,
        *,
        report_formatter: ReportFormatter | None = None,
        response_formatter: ResponseFormatter | None = None,
        metadata_builder: ResponseMetadataBuilder | None = None,
    ) -> None:
        self._report_formatter = report_formatter or ReportFormatter()
        self._response_formatter = response_formatter or ResponseFormatter()
        self._metadata_builder = metadata_builder or ResponseMetadataBuilder()

    def validate_inputs(self, context: ReportingContext) -> None:
        """Reject invalid presentation inputs."""
        if context.explanation_result is None:
            msg = "missing explanation"
            raise CopilotError(msg)
        result = context.explanation_result
        if result.explanation is None:
            msg = "missing explanation"
            raise CopilotError(msg)
        if not result.provenance:
            msg = "broken provenance: ExplanationResult provenance empty"
            raise CopilotError(msg)
        if not result.explanation.provenance:
            msg = "broken provenance: Explanation provenance empty"
            raise CopilotError(msg)

        inp = context.explanation_input
        if not inp.copilot_id:
            msg = "invalid metadata: missing copilot_id"
            raise CopilotError(msg)
        if inp.session_id and result.explanation.explanation_id:
            if inp.session_id not in result.explanation.explanation_id:
                msg = (
                    "identity mismatch: ExplanationInput session_id "
                    f"{inp.session_id!r} not reflected in explanation_id"
                )
                raise CopilotError(msg)

        citations = result.citations
        if len(citations) != len(set(citations)):
            msg = "duplicate citations"
            raise CopilotError(msg)
        evidence = result.supporting_evidence
        if len(evidence) != len(set(evidence)):
            msg = "duplicate evidence"
            raise CopilotError(msg)

        if result.confidence not in ConfidenceLevel:
            msg = f"invalid confidence: {result.confidence!r}"
            raise CopilotError(msg)

        metadata = context.metadata or CopilotMetadata(as_of=inp.as_of)
        if not metadata.as_of:
            msg = "invalid metadata: empty as_of"
            raise CopilotError(msg)

        # Factual explanations (non-refusal/clarify) should carry citations.
        if (
            result.status
            not in (ExplanationStatus.REFUSED, ExplanationStatus.CLARIFY)
            and not citations
            and result.status is not ExplanationStatus.EMPTY
        ):
            msg = "missing citations"
            raise CopilotError(msg)

        sections = (
            context.summary_sections
            if context.summary_sections is not None
            else _DEFAULT_SECTIONS
        )
        self._reject_duplicate_sections(sections)

    def report(self, context: ReportingContext) -> ReportingResult:
        """Build presentation CopilotResponse from ExplanationResult."""
        self.validate_inputs(context)
        warnings: list[str] = list(context.explanation_result.warnings)

        (
            executive_summary,
            key_reasons,
            risks,
            supporting_evidence,
            citations,
            confidence,
            provenance,
        ) = self._report_formatter.format(context.explanation_result)

        # Ordering consistency: citations sorted for stable channel payloads.
        ordered_citations = tuple(sorted(citations))
        if ordered_citations != citations:
            warnings.append("citations reordered for stable presentation.")
            citations = ordered_citations

        sections = (
            context.summary_sections
            if context.summary_sections is not None
            else _DEFAULT_SECTIONS
        )
        status = self._map_status(context.explanation_result.status)
        metadata = context.metadata or CopilotMetadata(
            as_of=context.explanation_input.as_of
        )

        response_metadata = self._metadata_builder.build(
            copilot_id=context.explanation_input.copilot_id,
            as_of=context.explanation_input.as_of,
            session_id=context.explanation_input.session_id,
            status=status,
            confidence=confidence,
            citation_count=len(citations),
            reason_count=len(key_reasons),
            risk_count=len(risks),
            evidence_count=len(supporting_evidence),
            section_keys=sections,
            owner=metadata.owner,
        )

        summary = CopilotSummary(
            turn_count=0,
            explanation_count=1,
            citation_count=len(citations),
            session_count=1,
            limitation_notes=tuple(
                dict.fromkeys(
                    (
                        *context.explanation_result.explanation.limitations,
                        *context.limitations,
                    )
                )
            ),
        )
        limitations = tuple(
            dict.fromkeys(
                (
                    *context.explanation_result.explanation.limitations,
                    *context.limitations,
                    _PRESENTATION_NOTE,
                )
            )
        )
        response = self._response_formatter.format(
            explanation_input=context.explanation_input,
            explanation=context.explanation_result.explanation,
            metadata=metadata,
            status=status,
            summary=summary,
            limitations=limitations,
        )

        statistics = CollectionStatistics(
            section_key="response",
            title="Copilot response statistics",
            total=(
                len(key_reasons)
                + len(risks)
                + len(supporting_evidence)
                + len(citations)
            ),
            by_category=(
                CategoryCount("key_reasons", len(key_reasons)),
                CategoryCount("risks", len(risks)),
                CategoryCount("supporting_evidence", len(supporting_evidence)),
                CategoryCount("citations", len(citations)),
            ),
        )
        validation_status = self._validation_view(
            result=context.explanation_result,
            metadata=metadata,
            citations=citations,
            provenance=provenance,
            confidence=confidence,
        )
        if warnings and status is ResponseStatus.COMPLETE:
            status = ResponseStatus.PARTIAL
            # Rebuild response with PARTIAL if needed.
            response = self._response_formatter.format(
                explanation_input=context.explanation_input,
                explanation=context.explanation_result.explanation,
                metadata=metadata,
                status=status,
                summary=summary,
                limitations=limitations,
            )
            response_metadata = self._metadata_builder.build(
                copilot_id=context.explanation_input.copilot_id,
                as_of=context.explanation_input.as_of,
                session_id=context.explanation_input.session_id,
                status=status,
                confidence=confidence,
                citation_count=len(citations),
                reason_count=len(key_reasons),
                risk_count=len(risks),
                evidence_count=len(supporting_evidence),
                section_keys=sections,
                owner=metadata.owner,
            )

        return ReportingResult(
            response=response,
            status=status,
            metadata=response_metadata,
            statistics=statistics,
            validation_status=validation_status,
            executive_summary=executive_summary,
            key_reasons=key_reasons,
            risks=risks,
            supporting_evidence=supporting_evidence,
            citations=citations,
            confidence=confidence,
            provenance=provenance,
            summary_sections=sections,
            warnings=tuple(dict.fromkeys(warnings)),
        )

    def report_many(
        self, contexts: tuple[ReportingContext, ...]
    ) -> tuple[ReportingResult, ...]:
        """Present many results; reject duplicate copilot/session identities."""
        assert_unique_copilot_ids(
            tuple(
                f"{c.explanation_input.copilot_id}:{c.explanation_input.session_id}"
                for c in contexts
            )
        )
        return tuple(self.report(ctx) for ctx in contexts)

    def _map_status(self, status: ExplanationStatus) -> ResponseStatus:
        mapping = {
            ExplanationStatus.COMPLETE: ResponseStatus.COMPLETE,
            ExplanationStatus.PARTIAL: ResponseStatus.PARTIAL,
            ExplanationStatus.REFUSED: ResponseStatus.REFUSED,
            ExplanationStatus.CLARIFY: ResponseStatus.PARTIAL,
            ExplanationStatus.EMPTY: ResponseStatus.EMPTY,
            ExplanationStatus.FAILED: ResponseStatus.FAILED,
        }
        return mapping.get(status, ResponseStatus.FAILED)

    def _validation_view(
        self,
        *,
        result: ExplanationResult,
        metadata: CopilotMetadata,
        citations: tuple[str, ...],
        provenance: tuple[str, ...],
        confidence: ConfidenceLevel,
    ) -> ValidationStatusView:
        notes: list[str] = []
        explanation_present = result.explanation is not None
        citations_present = bool(citations) or result.status in (
            ExplanationStatus.REFUSED,
            ExplanationStatus.CLARIFY,
        )
        provenance_complete = bool(provenance) and bool(
            result.explanation.provenance if result.explanation else ()
        )
        metadata_present = metadata is not None and bool(metadata.as_of)
        confidence_valid = confidence in ConfidenceLevel
        ordering_consistent = citations == tuple(sorted(citations))
        if not explanation_present:
            notes.append("explanation missing.")
        if not citations_present:
            notes.append("citations missing.")
        if not provenance_complete:
            notes.append("provenance incomplete.")
        if not ordering_consistent:
            notes.append("citation ordering inconsistent.")
        status = (
            "valid"
            if (
                explanation_present
                and citations_present
                and provenance_complete
                and metadata_present
                and confidence_valid
                and ordering_consistent
            )
            else "incomplete"
        )
        return ValidationStatusView(
            status=status,
            explanation_present=explanation_present,
            citations_present=citations_present,
            provenance_complete=provenance_complete,
            metadata_present=metadata_present,
            confidence_valid=confidence_valid,
            ordering_consistent=ordering_consistent,
            notes=tuple(notes),
        )

    def _reject_duplicate_sections(self, sections: tuple[str, ...]) -> None:
        seen: set[str] = set()
        for raw in sections:
            key = raw.strip().lower()
            if not key:
                msg = "duplicate report sections: empty section key"
                raise CopilotError(msg)
            if key in seen:
                msg = f"duplicate report sections: {raw!r}"
                raise CopilotError(msg)
            seen.add(key)
