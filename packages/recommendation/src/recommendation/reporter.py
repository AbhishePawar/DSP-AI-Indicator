"""Recommendation Reporter — presentation only (G1.3).

Organizes existing engine / report artifacts for presentation.
Never synthesizes options, recalculates confidence, or invents recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from recommendation.engine import EngineResult
from recommendation.enums import ReportingStatus
from recommendation.exceptions import RecommendationError
from recommendation.models import (
    RecommendationConflict,
    RecommendationOption,
    RecommendationRationale,
    RecommendationReport,
    RecommendationScore,
)

__all__ = [
    "CitationSection",
    "RecommendationReporter",
    "ReportMetadata",
    "ReportingContext",
    "ReportingResult",
]

_DEFAULT_SUMMARY_SECTIONS: tuple[str, ...] = (
    "overview",
    "preferred",
    "alternates",
    "confidence",
    "rationales",
    "conflicts",
    "citations",
    "summary",
    "limitations",
)


@dataclass(frozen=True, slots=True)
class CitationSection:
    """Presentation grouping of supporting citation keys — values unchanged."""

    section_key: str
    title: str
    citations: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "citations", tuple(self.citations))


@dataclass(frozen=True, slots=True)
class ReportMetadata:
    """Presentation metadata — descriptive only."""

    recommendation_id: str
    as_of: str
    option_count: int
    score_count: int
    rationale_count: int
    conflict_count: int
    preferred_option_id: str | None
    section_keys: tuple[str, ...]
    portfolio_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "section_keys", tuple(self.section_keys))


@dataclass(frozen=True, slots=True)
class ReportingContext:
    """Inputs for Recommendation presentation.

    Consume ``RecommendationReport`` and/or ``EngineResult`` only.
    Never executes the engine or opens upstream reports.
    """

    report: RecommendationReport | None = None
    engine_result: EngineResult | None = None
    summary_sections: tuple[str, ...] | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.report is None and self.engine_result is None:
            msg = (
                "missing report identity: RecommendationReport or EngineResult required"
            )
            raise RecommendationError(msg)
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
    """Presentation output — immutable, calculation-free."""

    report: RecommendationReport
    status: ReportingStatus
    metadata: ReportMetadata
    preferred_option: RecommendationOption | None
    alternate_options: tuple[RecommendationOption, ...]
    scores: tuple[RecommendationScore, ...]
    rationales: tuple[RecommendationRationale, ...]
    conflicts: tuple[RecommendationConflict, ...]
    citation_sections: tuple[CitationSection, ...]
    summary_sections: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "alternate_options", tuple(self.alternate_options))
        object.__setattr__(self, "scores", tuple(self.scores))
        object.__setattr__(self, "rationales", tuple(self.rationales))
        object.__setattr__(self, "conflicts", tuple(self.conflicts))
        object.__setattr__(self, "citation_sections", tuple(self.citation_sections))
        object.__setattr__(self, "summary_sections", tuple(self.summary_sections))
        object.__setattr__(self, "warnings", tuple(self.warnings))


class RecommendationReporter:
    """Canonical presentation layer for Recommendation Intelligence.

    Formats existing artifacts — never invents recommendations.
    """

    def validate_inputs(self, context: ReportingContext) -> None:
        """Reject invalid presentation inputs."""
        source = self._resolve_source(context)
        if not source.recommendation_id:
            msg = "missing report identity: recommendation_id is required"
            raise RecommendationError(msg)

        if context.engine_result is not None and context.report is not None:
            if (
                context.engine_result.recommendation_id
                != context.report.recommendation_id
            ):
                msg = (
                    "duplicate recommendation ids: EngineResult "
                    f"{context.engine_result.recommendation_id!r} does not match "
                    f"report {context.report.recommendation_id!r}"
                )
                raise RecommendationError(msg)

        self._reject_duplicate_option_ids(source.options)
        self._validate_scores(source.scores)
        self._validate_option_links(source)
        self._validate_conflict_links(source)

        sections = (
            context.summary_sections
            if context.summary_sections is not None
            else _DEFAULT_SUMMARY_SECTIONS
        )
        self._reject_duplicate_summary_sections(sections)

    def report(
        self,
        context: ReportingContext | RecommendationReport | EngineResult,
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
        self._reject_duplicate_summary_sections(sections)

        # Pass-through exact tuples — preserve ordering and Decimal identity.
        options = source.options
        scores = source.scores
        rationales = source.rationales
        conflicts = source.conflicts
        summary = source.summary

        preferred = None
        alternates: list[RecommendationOption] = []
        if source.preferred_option_id is not None:
            for option in options:
                if option.option_id == source.preferred_option_id:
                    preferred = option
                else:
                    alternates.append(option)
            if preferred is None:
                warnings.append(
                    "preferred_option_id present but option missing from report."
                )
                alternates = list(options)
        else:
            if options:
                preferred = options[0]
                alternates = list(options[1:])
            warnings.append("preferred_option_id missing; first option used if any.")

        citation_sections = self._format_citations(source)
        limitations = tuple(
            dict.fromkeys(
                (
                    *source.limitations,
                    *summary.limitation_notes,
                    *ctx.limitations,
                    "RecommendationReport presentation only — "
                    "no synthesis performed by reporter.",
                )
            )
        )

        presented = RecommendationReport(
            recommendation_id=source.recommendation_id,
            summary=summary,
            as_of=source.as_of,
            options=options,
            scores=scores,
            rationales=rationales,
            conflicts=conflicts,
            decision_refs=source.decision_refs,
            comparison_refs=source.comparison_refs,
            portfolio_ref=source.portfolio_ref,
            risk_refs=source.risk_refs,
            research_refs=source.research_refs,
            quantitative_risk_refs=source.quantitative_risk_refs,
            preferred_option_id=source.preferred_option_id,
            limitations=limitations,
        )

        metadata = ReportMetadata(
            recommendation_id=presented.recommendation_id,
            as_of=presented.as_of,
            option_count=len(options),
            score_count=len(scores),
            rationale_count=len(rationales),
            conflict_count=len(conflicts),
            preferred_option_id=presented.preferred_option_id,
            section_keys=sections,
            portfolio_id=(
                None
                if presented.portfolio_ref is None
                else presented.portfolio_ref.portfolio_id
            ),
        )

        status = self._status(options, scores, rationales, preferred)
        if status is ReportingStatus.PARTIAL:
            warnings.append("Report sections are incomplete.")
        if status is ReportingStatus.EMPTY:
            warnings.append("Report contains no recommendation options.")

        return ReportingResult(
            report=presented,
            status=status,
            metadata=metadata,
            preferred_option=preferred,
            alternate_options=tuple(alternates),
            scores=scores,
            rationales=rationales,
            conflicts=conflicts,
            citation_sections=citation_sections,
            summary_sections=sections,
            warnings=tuple(warnings),
        )

    def report_many(
        self,
        contexts: tuple[
            ReportingContext | RecommendationReport | EngineResult, ...
        ],
    ) -> tuple[ReportingResult, ...]:
        """Present many reports; reject duplicate recommendation identities."""
        seen: set[str] = set()
        results: list[ReportingResult] = []
        for item in contexts:
            result = self.report(item)
            rid = result.report.recommendation_id
            if rid in seen:
                msg = f"duplicate recommendation ids: {rid!r}"
                raise RecommendationError(msg)
            seen.add(rid)
            results.append(result)
        return tuple(results)

    def _as_context(
        self,
        context: ReportingContext | RecommendationReport | EngineResult,
    ) -> ReportingContext:
        if isinstance(context, ReportingContext):
            return context
        if isinstance(context, EngineResult):
            return ReportingContext(engine_result=context)
        if isinstance(context, RecommendationReport):
            return ReportingContext(report=context)
        msg = "invalid reporting input"
        raise RecommendationError(msg)

    def _resolve_source(self, context: ReportingContext) -> RecommendationReport:
        if context.engine_result is not None:
            return context.engine_result.report
        if context.report is not None:
            return context.report
        msg = "missing report identity: RecommendationReport or EngineResult required"
        raise RecommendationError(msg)

    def _format_citations(
        self, source: RecommendationReport
    ) -> tuple[CitationSection, ...]:
        sections: list[CitationSection] = []
        if source.decision_refs:
            sections.append(
                CitationSection(
                    section_key="decision",
                    title="Decision citations",
                    citations=tuple(r.citation for r in source.decision_refs),
                )
            )
        if source.comparison_refs:
            sections.append(
                CitationSection(
                    section_key="comparison",
                    title="Comparison citations",
                    citations=tuple(r.citation for r in source.comparison_refs),
                )
            )
        if source.portfolio_ref is not None:
            sections.append(
                CitationSection(
                    section_key="portfolio",
                    title="Portfolio citations",
                    citations=(source.portfolio_ref.citation,),
                )
            )
        if source.risk_refs:
            sections.append(
                CitationSection(
                    section_key="risk",
                    title="Qualitative risk citations",
                    citations=tuple(r.citation for r in source.risk_refs),
                )
            )
        if source.research_refs:
            sections.append(
                CitationSection(
                    section_key="research",
                    title="Research citations",
                    citations=tuple(r.citation for r in source.research_refs),
                )
            )
        if source.quantitative_risk_refs:
            sections.append(
                CitationSection(
                    section_key="quantitative_risk",
                    title="Quantitative risk citations",
                    citations=tuple(
                        r.citation for r in source.quantitative_risk_refs
                    ),
                )
            )
        return tuple(sections)

    def _status(
        self,
        options: tuple[RecommendationOption, ...],
        scores: tuple[RecommendationScore, ...],
        rationales: tuple[RecommendationRationale, ...],
        preferred: RecommendationOption | None,
    ) -> ReportingStatus:
        if not options and not scores and not rationales:
            return ReportingStatus.EMPTY
        if not options or not scores or not rationales or preferred is None:
            return ReportingStatus.PARTIAL
        return ReportingStatus.COMPLETE

    def _reject_duplicate_option_ids(
        self, options: tuple[RecommendationOption, ...]
    ) -> None:
        seen: set[str] = set()
        for option in options:
            if option.option_id in seen:
                msg = f"duplicate recommendation ids: option {option.option_id!r}"
                raise RecommendationError(msg)
            seen.add(option.option_id)

    def _reject_duplicate_summary_sections(self, sections: tuple[str, ...]) -> None:
        seen: set[str] = set()
        for section in sections:
            key = section.strip().lower()
            if not key:
                msg = "duplicate summary sections: empty section key"
                raise RecommendationError(msg)
            if key in seen:
                msg = f"duplicate summary sections: {key!r}"
                raise RecommendationError(msg)
            seen.add(key)

    def _validate_scores(self, scores: tuple[RecommendationScore, ...]) -> None:
        for score in scores:
            if not score.provenance:
                msg = f"missing provenance: score {score.score_id!r}"
                raise RecommendationError(msg)
            if not score.method_id or not score.method_id.strip():
                msg = f"missing method_id: score {score.score_id!r}"
                raise RecommendationError(msg)
            if not score.unit or not score.unit.strip():
                msg = f"missing units: score {score.score_id!r}"
                raise RecommendationError(msg)
            if isinstance(score.value, bool) or not isinstance(score.value, Decimal):
                msg = f"invalid Decimal values: score {score.score_id!r}"
                raise RecommendationError(msg)

    def _validate_option_links(self, source: RecommendationReport) -> None:
        rationale_ids = {r.rationale_id for r in source.rationales}
        known_citations = self._known_citations(source)
        for option in source.options:
            for rid in option.supporting_rationale_refs:
                if rid not in rationale_ids:
                    msg = (
                        f"broken rationale refs: option {option.option_id!r} "
                        f"references missing rationale {rid!r}"
                    )
                    raise RecommendationError(msg)
            for key in option.supporting_report_refs:
                if key not in known_citations:
                    msg = (
                        f"broken citation refs: option {option.option_id!r} "
                        f"references unknown citation {key!r}"
                    )
                    raise RecommendationError(msg)

    def _validate_conflict_links(self, source: RecommendationReport) -> None:
        option_ids = {o.option_id for o in source.options}
        known_citations = self._known_citations(source)
        for conflict in source.conflicts:
            for oid in conflict.option_refs:
                if oid not in option_ids:
                    msg = (
                        f"broken citation refs: conflict {conflict.conflict_id!r} "
                        f"references missing option {oid!r}"
                    )
                    raise RecommendationError(msg)
            for key in conflict.report_refs:
                if key not in known_citations:
                    msg = (
                        f"broken citation refs: conflict {conflict.conflict_id!r} "
                        f"references unknown citation {key!r}"
                    )
                    raise RecommendationError(msg)

    def _known_citations(self, source: RecommendationReport) -> frozenset[str]:
        keys: set[str] = set()
        for ref in source.decision_refs:
            keys.add(ref.citation)
        for ref in source.comparison_refs:
            keys.add(ref.citation)
        if source.portfolio_ref is not None:
            keys.add(source.portfolio_ref.citation)
        for ref in source.risk_refs:
            keys.add(ref.citation)
        for ref in source.research_refs:
            keys.add(ref.citation)
        for ref in source.quantitative_risk_refs:
            keys.add(ref.citation)
        return frozenset(keys)
