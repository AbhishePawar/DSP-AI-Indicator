"""Regression tests for non-destructive dual-model research reconciliation."""

from types import SimpleNamespace

from llm_adapters.orchestrator.orchestrator import ResearchOrchestrator, _AttemptMemory
from llm_adapters.orchestrator.schema import (
    AIResearchOutput,
    EvidenceItem,
    ResearchSection,
)
from llm_adapters.orchestrator.validation import ValidationSuccess
from llm_adapters.privacy_boundary import PublicDecisionPack


def _output(
    *, business: str, risk: str, brief: str, evidence_id: str
) -> AIResearchOutput:
    section = lambda summary: ResearchSection(  # noqa: E731
        summary=summary, evidence_ids=[evidence_id], unavailable=False
    )
    return AIResearchOutput(
        company="Example Ltd",
        research_status="complete",
        recommendation="HOLD",
        confidence=0.8,
        valuation=section("DSP valuation is unchanged."),
        business_quality=section(business),
        moat=section("Evidence-backed moat assessment."),
        management=section("Management evidence reviewed."),
        financial_strength=section("Financial strength evidence reviewed."),
        earnings_quality=section("Earnings quality evidence reviewed."),
        growth_quality=section("Growth evidence reviewed."),
        industry=section("Industry evidence reviewed."),
        risk=section(risk),
        buffett_analysis=section("Buffett framework evidence reviewed."),
        evidence=[
            EvidenceItem(
                id=evidence_id, source="dsp.business_quality", claim=business
            )
        ],
        decision_brief=brief,
        limitations=[],
        assurance="All claims cite validated tool evidence.",
    )


def _attempt(output: AIResearchOutput, provider: str):
    pack = PublicDecisionPack(
        recommendation="HOLD",
        valuation="100",
        analysis=output.decision_brief,
        risks=(output.risk.summary,),
        evidence_citations=(output.evidence[0].id,),
        confidence=output.confidence,
        limitations=(),
    )
    validation = ValidationSuccess(output=output, pack=pack)
    memory = _AttemptMemory(
        completion=None,
        prompt=(),
        outcomes=(),
        catalog=(),
        validation=validation,
        identity=provider,
    )
    evaluation = SimpleNamespace(
        quality=SimpleNamespace(evidence_correctness=1.0),
        estimated_cost_usd=0.0,
    )
    return evaluation, memory


def test_dual_reconciliation_retains_unique_findings_and_citations():
    first = _attempt(
        _output(
            business="Strong distribution network.",
            risk="Customer concentration risk.",
            brief="Distribution is a strength.",
            evidence_id="gemini-evidence-1",
        ),
        "gemini:model",
    )
    second = _attempt(
        _output(
            business="Recurring customer relationships.",
            risk="Input-cost volatility.",
            brief="Recurring customers support resilience.",
            evidence_id="openai-evidence-2",
        ),
        "openai:model",
    )

    _, merged = ResearchOrchestrator._merge_successful_attempts([first, second], first)
    assert isinstance(merged.validation, ValidationSuccess)
    pack = merged.validation.pack
    assert "Distribution is a strength." in pack.analysis
    assert "Recurring customers support resilience." in pack.analysis
    assert "Customer concentration risk." in pack.risks
    assert "Input-cost volatility." in pack.risks
    assert set(pack.evidence_citations) == {"gemini-evidence-1", "openai-evidence-2"}
    assert any("Unresolved differences" in item for item in pack.limitations)
    assert set(merged.contributing_models) == {"gemini:model", "openai:model"}
    assert set(merged.conflicting_sections) >= {"business_quality", "risk"}


def test_dual_reconciliation_preserves_deterministic_decision_and_valuation():
    first = _attempt(
        _output(
            business="Evidence A.",
            risk="Risk A.",
            brief="Brief A.",
            evidence_id="evidence-a",
        ),
        "gemini:model",
    )
    second = _attempt(
        _output(
            business="Evidence B.",
            risk="Risk B.",
            brief="Brief B.",
            evidence_id="evidence-b",
        ),
        "openai:model",
    )

    _, merged = ResearchOrchestrator._merge_successful_attempts([first, second], first)
    assert isinstance(merged.validation, ValidationSuccess)
    assert merged.validation.pack.recommendation == "HOLD"
    assert merged.validation.pack.valuation == "100"
    assert merged.validation.output.recommendation == "HOLD"
