"""Industry Evidence Interpreter tests (C3.4)."""

from __future__ import annotations

import pytest
from core.exceptions import ValidationError

from industry import (
    ApplicabilityLevel,
    EvidenceAvailability,
    EvidenceInterpretation,
    EvidenceInterpretationContext,
    EvidenceObservation,
    EvidenceObservationCategory,
    EvidenceObservationConfidence,
    EvidenceObservationSeverity,
    EvidenceProviderResult,
    IndustryError,
    IndustryEvidenceInterpreter,
    IndustryEvidenceInterpreterRegistry,
    PlaceholderEvidenceInterpreter,
    build_example_evidence_interpreters,
    seed_example_evidence_interpreter_context,
    seed_example_evidence_registries,
)


def _result(
    *,
    evidence_id: str = "dsp.evidence.nim_stability",
    provider_id: str = "dsp.provider.fundamental",
    availability: EvidenceAvailability = EvidenceAvailability.INSUFFICIENT_DATA,
) -> EvidenceProviderResult:
    return EvidenceProviderResult(
        evidence_id=evidence_id,
        provider_id=provider_id,
        availability=availability,
    )


def _ctx(
    *,
    evidence_id: str = "dsp.evidence.nim_stability",
    availability: EvidenceAvailability = EvidenceAvailability.INSUFFICIENT_DATA,
    methodology_id: str = "dsp.methodology.commercial_banking",
) -> EvidenceInterpretationContext:
    return EvidenceInterpretationContext(
        instrument_key="HDFCBANK",
        methodology_id=methodology_id,
        methodology_version="1.0.0",
        provider_result=_result(evidence_id=evidence_id, availability=availability),
        applicability_level=ApplicabilityLevel.REQUIRED,
    )


class TestInterpreterModels:
    def test_duplicate_interpretation_rejected(self) -> None:
        with pytest.raises(ValidationError, match="duplicate interpreter capability"):
            IndustryEvidenceInterpreter(
                id="dsp.interpreter.x",
                name="X",
                version="1.0.0",
                interpretations=(
                    EvidenceInterpretation(evidence_id="dsp.evidence.roe_persistence"),
                    EvidenceInterpretation(evidence_id="dsp.evidence.roe_persistence"),
                ),
            )

    def test_observation_rejects_ranking_language(self) -> None:
        with pytest.raises(ValidationError, match="forbidden term"):
            EvidenceObservation(
                id="obs.bad",
                title="Best reading",
                summary="A summary",
                explanation="An explanation",
                evidence_refs=("dsp.evidence.roe_persistence",),
                confidence=EvidenceObservationConfidence.LOW,
                severity=EvidenceObservationSeverity.INFO,
                category=EvidenceObservationCategory.QUALITY,
                interpreter_id="dsp.interpreter.x",
                instrument_key="AAA",
                methodology_id="dsp.methodology.x",
                methodology_version="1.0.0",
            )

    def test_missing_methodology_rejected_on_context(self) -> None:
        with pytest.raises(ValidationError, match="methodology_id"):
            EvidenceInterpretationContext(
                instrument_key="HDFCBANK",
                methodology_id="",
                methodology_version="1.0.0",
                provider_result=_result(),
            )


class TestInterpreterRegistry:
    def test_register_lookup_interpret(self) -> None:
        _, interpreters = seed_example_evidence_interpreter_context()
        meta = interpreters.lookup_active("dsp.interpreter.fundamental")
        assert "dsp.evidence.nim_stability" in meta.evidence_ids
        obs = interpreters.interpret("dsp.interpreter.fundamental", _ctx())
        assert obs.availability is EvidenceAvailability.INSUFFICIENT_DATA
        assert obs.is_placeholder is True
        assert obs.confidence is EvidenceObservationConfidence.UNKNOWN
        assert "score" not in obs.summary.lower()
        interpreters.validate()

    def test_interpret_available_with_value(self) -> None:
        _, interpreters = seed_example_evidence_interpreter_context()
        ctx = EvidenceInterpretationContext(
            instrument_key="HDFCBANK",
            methodology_id="dsp.methodology.commercial_banking",
            methodology_version="1.0.0",
            provider_result=EvidenceProviderResult(
                evidence_id="dsp.evidence.nim_stability",
                provider_id="dsp.provider.fundamental",
                availability=EvidenceAvailability.AVAILABLE,
                value="placeholder:dsp.evidence.nim_stability",
                is_placeholder=True,
            ),
            applicability_level=ApplicabilityLevel.REQUIRED,
        )
        a = interpreters.interpret("dsp.interpreter.fundamental", ctx)
        b = interpreters.interpret("dsp.interpreter.fundamental", ctx)
        assert a == b
        assert a.severity is EvidenceObservationSeverity.INFO
        assert a.category is EvidenceObservationCategory.QUALITY

    def test_unsupported_evidence_rejected(self) -> None:
        evidence, _ = seed_example_evidence_registries()
        registry = IndustryEvidenceInterpreterRegistry(evidence)
        bad = PlaceholderEvidenceInterpreter(
            IndustryEvidenceInterpreter(
                id="dsp.interpreter.bad",
                name="Bad",
                version="1.0.0",
                interpretations=(
                    EvidenceInterpretation(
                        evidence_id="dsp.evidence.does_not_exist"
                    ),
                ),
            )
        )
        with pytest.raises(IndustryError, match="unsupported evidence"):
            registry.register(bad)

    def test_interpret_unsupported_raises(self) -> None:
        _, interpreters = seed_example_evidence_interpreter_context()
        with pytest.raises(IndustryError, match="does not support"):
            interpreters.interpret(
                "dsp.interpreter.valuation",
                _ctx(evidence_id="dsp.evidence.nim_stability"),
            )

    def test_duplicate_interpreter_rejected(self) -> None:
        _, interpreters = seed_example_evidence_interpreter_context()
        twin = build_example_evidence_interpreters()[0]
        with pytest.raises(IndustryError, match="duplicate"):
            interpreters.register(twin)

    def test_interpret_many_deterministic(self) -> None:
        _, interpreters = seed_example_evidence_interpreter_context()
        interpreter = interpreters.get_interpreter("dsp.interpreter.fundamental")
        contexts = (
            _ctx(evidence_id="dsp.evidence.nim_stability"),
            _ctx(evidence_id="dsp.evidence.roe_persistence"),
        )
        results = interpreter.interpret_many(contexts)
        assert [r.evidence_refs[0] for r in results] == [
            "dsp.evidence.nim_stability",
            "dsp.evidence.roe_persistence",
        ]
        assert interpreter.interpret_many(contexts) == results
