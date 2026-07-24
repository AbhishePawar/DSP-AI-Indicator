"""Illustrative EvidenceInterpreter implementations (C3.4 — no engine wiring)."""

from __future__ import annotations

from industry.enums import (
    ApplicabilityLevel,
    EvidenceAvailability,
    EvidenceObservationCategory,
    EvidenceObservationConfidence,
    EvidenceObservationSeverity,
)
from industry.evidence_interpreter import (
    EvidenceInterpretation,
    EvidenceInterpretationContext,
    EvidenceObservation,
    IndustryEvidenceInterpreter,
)
from industry.evidence_interpreter_registry import IndustryEvidenceInterpreterRegistry
from industry.evidence_registry import IndustryEvidenceRegistry
from industry.evidence_seeds import seed_example_evidence_registries
from industry.exceptions import IndustryError

__all__ = [
    "EXAMPLE_INTERPRETER_IDS",
    "PlaceholderEvidenceInterpreter",
    "build_example_evidence_interpreters",
    "register_example_evidence_interpreters",
    "seed_example_evidence_interpreter_context",
]

EXAMPLE_INTERPRETER_IDS: tuple[str, ...] = (
    "dsp.interpreter.decision_pack",
    "dsp.interpreter.fundamental",
    "dsp.interpreter.valuation",
    "dsp.interpreter.technical",
)

_PLACEHOLDER_NOTE = (
    "C3.4 illustrative interpreter — no methodology-engine integration; "
    "observations are explicit placeholders only."
)


def _rule_for(
    meta: IndustryEvidenceInterpreter, evidence_id: str
) -> EvidenceInterpretation | None:
    eid = evidence_id.strip().lower()
    for item in meta.interpretations:
        if item.evidence_id == eid:
            return item
    return None


class PlaceholderEvidenceInterpreter:
    """Deterministic stub interpreter. Never calculates or compares."""

    def __init__(self, metadata: IndustryEvidenceInterpreter) -> None:
        self._meta = metadata
        self._supported = frozenset(metadata.evidence_ids)

    def interpreter_metadata(self) -> IndustryEvidenceInterpreter:
        return self._meta

    def supports(
        self, evidence_id: str, context: EvidenceInterpretationContext
    ) -> bool:
        del context
        return evidence_id.strip().lower() in self._supported

    def interpret(
        self, context: EvidenceInterpretationContext
    ) -> EvidenceObservation:
        if not context.methodology_id:
            msg = "missing methodology for interpretation"
            raise IndustryError(msg)
        eid = context.evidence_id
        if not self.supports(eid, context):
            msg = (
                f"interpreter {self._meta.id!r} does not support evidence {eid!r}"
            )
            raise IndustryError(msg)
        rule = _rule_for(self._meta, eid)
        assert rule is not None
        result = context.provider_result
        name = (
            context.evidence_definition.name
            if context.evidence_definition is not None
            else eid
        )
        severity, confidence, category, title, summary, explanation = (
            self._placeholder_copy(name=name, context=context, rule=rule)
        )
        observation_id = (
            f"obs.{self._meta.id}.{context.instrument_key.lower()}.{eid}"
        )
        return EvidenceObservation(
            id=observation_id,
            title=title,
            summary=summary,
            explanation=explanation,
            evidence_refs=(eid,),
            confidence=confidence,
            severity=severity,
            category=category,
            interpreter_id=self._meta.id,
            instrument_key=context.instrument_key,
            methodology_id=context.methodology_id,
            methodology_version=context.methodology_version,
            provider_id=result.provider_id,
            availability=result.availability,
            is_placeholder=True,
            notes=(_PLACEHOLDER_NOTE,),
        )

    def interpret_many(
        self, contexts: tuple[EvidenceInterpretationContext, ...]
    ) -> tuple[EvidenceObservation, ...]:
        return tuple(self.interpret(ctx) for ctx in contexts)

    def _placeholder_copy(
        self,
        *,
        name: str,
        context: EvidenceInterpretationContext,
        rule: EvidenceInterpretation,
    ) -> tuple[
        EvidenceObservationSeverity,
        EvidenceObservationConfidence,
        EvidenceObservationCategory,
        str,
        str,
        str,
    ]:
        availability = context.provider_result.availability
        level = context.applicability_level
        category = rule.category
        if availability is EvidenceAvailability.AVAILABLE:
            severity = rule.default_severity
            confidence = EvidenceObservationConfidence.LOW
            title = f"Provisional reading for {name}"
            summary = (
                f"Placeholder interpretation of available evidence under "
                f"methodology {context.methodology_id}."
            )
            explanation = (
                f"Provider reported AVAILABLE for {context.evidence_id}. "
                f"This illustrative interpreter records a provisional "
                f"observation without calculating metrics or comparing peers. "
                f"Applicability level: {level.value}."
            )
        elif availability is EvidenceAvailability.INSUFFICIENT_DATA:
            severity = EvidenceObservationSeverity.NOTICE
            confidence = EvidenceObservationConfidence.UNKNOWN
            category = EvidenceObservationCategory.AVAILABILITY
            title = f"Insufficient data for {name}"
            summary = (
                "Evidence could not be interpreted because provider data "
                "is insufficient."
            )
            explanation = (
                f"Provider reported INSUFFICIENT_DATA for {context.evidence_id}. "
                f"No fabricated reading is produced. Applicability: {level.value}."
            )
        elif availability is EvidenceAvailability.UNAVAILABLE:
            severity = EvidenceObservationSeverity.CAUTION
            confidence = EvidenceObservationConfidence.UNKNOWN
            category = EvidenceObservationCategory.AVAILABILITY
            title = f"Unavailable evidence for {name}"
            summary = "Evidence source is unavailable under the current context."
            explanation = (
                f"Provider reported UNAVAILABLE for {context.evidence_id}. "
                f"Interpretation records the gap only."
            )
        elif availability is EvidenceAvailability.NOT_APPLICABLE:
            severity = EvidenceObservationSeverity.INFO
            confidence = EvidenceObservationConfidence.MEDIUM
            category = EvidenceObservationCategory.METHODOLOGY
            title = f"Not applicable: {name}"
            summary = "Evidence is outside this provider path for the instrument."
            explanation = (
                f"Provider reported NOT_APPLICABLE for {context.evidence_id}."
            )
        elif availability is EvidenceAvailability.ERROR:
            severity = EvidenceObservationSeverity.WARNING
            confidence = EvidenceObservationConfidence.UNKNOWN
            category = EvidenceObservationCategory.LIMITATION
            title = f"Provider error for {name}"
            summary = "Interpretation limited by provider error."
            err = context.provider_result.error_message or "unspecified error"
            explanation = (
                f"Provider reported ERROR for {context.evidence_id}: {err}."
            )
        else:
            severity = EvidenceObservationSeverity.NOTICE
            confidence = EvidenceObservationConfidence.UNKNOWN
            title = f"Unresolved evidence for {name}"
            summary = "No deterministic interpretation path for availability state."
            explanation = f"Unhandled availability {availability.value}."

        if level is ApplicabilityLevel.UNSUPPORTED:
            severity = EvidenceObservationSeverity.CAUTION
            category = EvidenceObservationCategory.METHODOLOGY
            title = f"Unsupported under methodology: {name}"
            summary = (
                "Methodology marks this evidence unsupported; observation "
                "records methodology policy only."
            )
            explanation = (
                f"Applicability is UNSUPPORTED for {context.evidence_id} under "
                f"{context.methodology_id}@{context.methodology_version}."
            )
        return severity, confidence, category, title, summary, explanation


def build_example_evidence_interpreters() -> tuple[
    PlaceholderEvidenceInterpreter, ...
]:
    return (
        PlaceholderEvidenceInterpreter(
            IndustryEvidenceInterpreter(
                id="dsp.interpreter.decision_pack",
                name="DecisionPack Interpreter",
                version="1.0.0",
                description=(
                    "Future interpreter for DecisionPack-sourced evidence."
                ),
                interpretations=(
                    EvidenceInterpretation(
                        evidence_id="dsp.evidence.roe_persistence",
                        category=EvidenceObservationCategory.QUALITY,
                        default_severity=EvidenceObservationSeverity.INFO,
                        notes=("Placeholder — does not read DecisionPack.",),
                    ),
                ),
                notes=("Placeholder only.",),
            )
        ),
        PlaceholderEvidenceInterpreter(
            IndustryEvidenceInterpreter(
                id="dsp.interpreter.fundamental",
                name="Fundamental Interpreter",
                version="1.0.0",
                interpretations=(
                    EvidenceInterpretation(
                        evidence_id="dsp.evidence.roe_persistence",
                        category=EvidenceObservationCategory.QUALITY,
                    ),
                    EvidenceInterpretation(
                        evidence_id="dsp.evidence.nim_stability",
                        category=EvidenceObservationCategory.QUALITY,
                    ),
                ),
                notes=("Placeholder only — no fundamental calculations.",),
            )
        ),
        PlaceholderEvidenceInterpreter(
            IndustryEvidenceInterpreter(
                id="dsp.interpreter.valuation",
                name="Valuation Interpreter",
                version="1.0.0",
                interpretations=(
                    EvidenceInterpretation(
                        evidence_id="dsp.evidence.regulated_cash_flow_visibility",
                        category=EvidenceObservationCategory.VALUATION,
                    ),
                ),
                notes=("Placeholder only — no valuation calculations.",),
            )
        ),
        PlaceholderEvidenceInterpreter(
            IndustryEvidenceInterpreter(
                id="dsp.interpreter.technical",
                name="Technical Interpreter",
                version="1.0.0",
                interpretations=(
                    EvidenceInterpretation(
                        evidence_id="dsp.evidence.roe_persistence",
                        category=EvidenceObservationCategory.OTHER,
                        notes=("Illustrative overlap; routing later.",),
                    ),
                ),
                notes=("Placeholder only — no technical calculations.",),
            )
        ),
    )


def register_example_evidence_interpreters(
    registry: IndustryEvidenceInterpreterRegistry,
) -> IndustryEvidenceInterpreterRegistry:
    for interpreter in build_example_evidence_interpreters():
        registry.register(interpreter)
    return registry


def seed_example_evidence_interpreter_context(
    evidence: IndustryEvidenceRegistry | None = None,
    interpreters: IndustryEvidenceInterpreterRegistry | None = None,
) -> tuple[IndustryEvidenceRegistry, IndustryEvidenceInterpreterRegistry]:
    """Seed evidence definitions + illustrative interpreters."""
    if evidence is None:
        _, evidence_reg = seed_example_evidence_registries()
    else:
        evidence_reg = evidence
    interpreter_reg = interpreters or IndustryEvidenceInterpreterRegistry(
        evidence_reg
    )
    register_example_evidence_interpreters(interpreter_reg)
    return evidence_reg, interpreter_reg
