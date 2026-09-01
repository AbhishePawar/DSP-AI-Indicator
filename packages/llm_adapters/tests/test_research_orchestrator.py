"""Tests for the STEP 3I AI Research Orchestrator.

Mocked providers and DSP tools only. No paid API calls.
"""

from __future__ import annotations

import json
from typing import Any

from llm_adapters.model_tiers import ModelTier
from llm_adapters.orchestrator import (
    AICompletion,
    OrchestratorStatus,
    PRIVATE_PROMPT_CANARY,
    ResearchOrchestrator,
    UserResearchRequest,
)
from llm_adapters.orchestrator.research_prompt import build_research_prompt
from llm_adapters.orchestrator.specification import ResearchSpecification, SIMPLE_TOOLS
from llm_adapters.privacy_boundary import assert_no_private_leakage
from llm_adapters.quality_gate import GateOutcome
from llm_adapters.routing import ComplexitySignal
from llm_adapters.tools import ToolRegistry
from llm_adapters.tools.protocol.models import ToolCall


class StubBackend:
    def __init__(self, *, raise_on: str | None = None, empty_rec: bool = False) -> None:
        self._raise_on = raise_on
        self._empty_rec = empty_rec

    def get_authenticated_financial_statements(self, symbol, *, exchange=None):
        return {"periods": ["2024"], "currency": "INR", "source": "dsp.financial_statements"}

    def financial_statement_health(self):
        return {"ok": True}

    def analyze_company(self, request):
        return {}

    def compare_companies(self, packs):
        return {}

    def ask_research_copilot(self, question, **kwargs):
        return {}

    def build_research_object(self, symbol, **kwargs):
        return {"lineage_id": "lin-1", "evidence_refs": ["r1"], "summary": {"headline": "OK"}}

    def get_research_snapshot(self, snapshot_id):
        return {}

    def run_copilot_v2(self, **kwargs):
        return {}

    def get_financial_quality(self, *, symbol):
        return {"metrics": {"roe": 0.18}, "as_of": "2026-09-01T00:00:00Z"}

    def get_valuation(self, *, symbol):
        if self._raise_on == "valuation":
            raise RuntimeError("valuation failed")
        return {
            "intrinsic_value_per_share": 180.0,
            "current_market_price": 150.0,
            "method": "two-stage DCF",
        }

    def get_margin_of_safety(self, *, symbol):
        return {"margin_of_safety": 0.2, "basis": "dsp.valuation"}

    def get_economic_moat(self, *, symbol):
        return {"moat": "Wide", "score": 0.8}

    def get_management_quality(self, *, symbol):
        return {"quality": "Strong", "score": 0.85}

    def get_financial_strength(self, *, symbol):
        return {"strength": "Strong", "score": 0.82}

    def get_earnings_quality(self, *, symbol):
        return {"quality": "High", "score": 0.78}

    def get_growth_quality(self, *, symbol):
        return {"growth": "Strong", "score": 0.75}

    def get_business_quality(self, *, symbol):
        return {"label": "Great", "score": 0.85}

    def get_risk(self, *, symbol):
        return {"risks": ["FX"], "score": 0.4}

    def get_quantitative_risk(self, *, symbol):
        return {"volatility": 0.25, "beta": 1.1, "max_drawdown": -0.3}

    def get_technical_signals(self, *, symbol):
        return {"signals": [{"name": "trend"}], "direction": "BULLISH"}

    def get_investment_recommendation(self, *, symbol):
        if self._raise_on == "recommendation":
            raise RuntimeError("recommendation failed")
        if self._empty_rec:
            return None
        return {"decision": "Buy", "confidence": 0.8, "margin_of_safety": 0.2}

    def run_deterministic_committee(self, *, symbol):
        return {"decision": "BUY", "votes": {"fundamental": "BUY"}, "confidence": 0.7}

    def compare_two_symbols(self, *, symbol_a, symbol_b):
        return {"dimensions": [], "summary": {}}


class ScriptedProvider:
    def __init__(
        self,
        provider_id: str,
        model_label: str,
        script: list[Any] | None = None,
    ) -> None:
        self.provider_id = provider_id
        self.model_label = model_label
        self._script = list(script or ["json"])
        self.calls = 0

    def complete(
        self,
        *,
        prompt_parts: tuple[str, ...],
        evidence_catalog: tuple[dict[str, Any], ...],
        prior_tool_results: tuple[dict[str, Any], ...] = (),
    ) -> AICompletion:
        del prior_tool_results
        self.calls += 1
        assert PRIVATE_PROMPT_CANARY in prompt_parts[0]
        step = self._script.pop(0) if self._script else "json"
        if step == "fail":
            return self._done("failed", None)
        if step == "unavailable":
            return self._done("unavailable", None)
        if step == "malformed":
            return self._done("complete", "this is not structured research")
        if step == "missing_evidence":
            return self._done("complete", _json_missing_evidence(evidence_catalog))
        if step == "unsupported":
            return self._done("complete", _json_unsupported(evidence_catalog))
        if step == "override":
            return self._done("complete", _happy_json(evidence_catalog, recommendation="Sell"))
        if step == "prompt_leak":
            payload = json.loads(_happy_json(evidence_catalog))
            payload["decision_brief"] = f"see {PRIVATE_PROMPT_CANARY}"
            return self._done("complete", json.dumps(payload))
        if step == "raw_leak":
            payload = json.loads(_happy_json(evidence_catalog))
            payload["assurance"] = "routing_reasons=secret chain_of_thought=hidden"
            return self._done("complete", json.dumps(payload))
        if isinstance(step, ToolCall):
            return AICompletion(
                status="complete",
                text=None,
                requested_calls=(step,),
                provider_id=self.provider_id,
                model_label=self.model_label,
            )
        return self._done("complete", _happy_json(evidence_catalog))

    def _done(self, status: str, text: str | None) -> AICompletion:
        return AICompletion(
            status=status,
            text=text,
            requested_calls=(),
            provider_id=self.provider_id,
            model_label=self.model_label,
        )


def _ids(catalog: tuple[dict[str, Any], ...]) -> dict[str, str]:
    return {
        str(row["tool_name"]): str(row["id"])
        for row in catalog
        if row.get("status") == "ok"
    }


def _section(catalog: tuple[dict[str, Any], ...], tool: str, summary: str) -> dict[str, Any]:
    ids = _ids(catalog)
    if tool not in ids:
        return {"summary": "Data unavailable.", "evidence_ids": [], "unavailable": True}
    return {"summary": summary, "evidence_ids": [ids[tool]], "unavailable": False}


def _evidence(catalog: tuple[dict[str, Any], ...], tool: str, claim: str) -> dict[str, str] | None:
    ids = _ids(catalog)
    if tool not in ids:
        return None
    return {"id": ids[tool], "source": tool, "claim": claim}


def _happy_json(
    catalog: tuple[dict[str, Any], ...],
    *,
    recommendation: str = "Buy",
) -> str:
    items = [
        _evidence(catalog, "dsp.valuation", "IV 180"),
        _evidence(catalog, "dsp.investment_recommendation", "Buy"),
        _evidence(catalog, "dsp.business_quality", "Great"),
        _evidence(catalog, "dsp.economic_moat", "Wide"),
        _evidence(catalog, "dsp.risk", "FX"),
    ]
    payload = {
        "company": "INFY",
        "research_status": "complete",
        "recommendation": recommendation,
        "confidence": 0.72,
        "valuation": _section(catalog, "dsp.valuation", "DSP intrinsic value is 180."),
        "business_quality": _section(catalog, "dsp.business_quality", "Great quality."),
        "moat": _section(catalog, "dsp.economic_moat", "Wide moat."),
        "management": _section(catalog, "dsp.management_quality", "Strong management."),
        "financial_strength": _section(catalog, "dsp.financial_strength", "Strong."),
        "earnings_quality": _section(catalog, "dsp.earnings_quality", "High."),
        "growth_quality": _section(catalog, "dsp.growth_quality", "Strong growth."),
        "industry": {"summary": "IT services.", "evidence_ids": [], "unavailable": False},
        "risk": _section(catalog, "dsp.risk", "FX risk is listed."),
        "buffett_analysis": _section(
            catalog, "dsp.economic_moat", "Durable advantage with margin of safety."
        ),
        "evidence": [item for item in items if item is not None],
        "decision_brief": "DSP tools support a Buy interpretation.",
        "limitations": ["lm_enrichment"],
        "assurance": "Conclusions cite authenticated DSP tool evidence only.",
    }
    return json.dumps(payload)


def _json_missing_evidence(catalog: tuple[dict[str, Any], ...]) -> str:
    payload = json.loads(_happy_json(catalog))
    payload["valuation"] = {
        "summary": "Looks cheap.",
        "evidence_ids": [],
        "unavailable": False,
    }
    return json.dumps(payload)


def _json_unsupported(catalog: tuple[dict[str, Any], ...]) -> str:
    payload = json.loads(_happy_json(catalog))
    payload["evidence"].append(
        {"id": "fabricated-id", "source": "dsp.valuation", "claim": "made up"}
    )
    payload["valuation"]["evidence_ids"].append("fabricated-id")
    return json.dumps(payload)


def _orchestrator(
    script: list[Any] | None = None,
    *,
    premium_script: list[Any] | None = None,
    backend: StubBackend | None = None,
    cheap: ScriptedProvider | None = None,
    premium: ScriptedProvider | None = None,
) -> ResearchOrchestrator:
    cheap = cheap or ScriptedProvider("deepseek", "deepseek-chat", script or ["json"])
    premium = premium or ScriptedProvider(
        "anthropic", "claude-3-5-sonnet-20241022", premium_script or ["json"]
    )
    return ResearchOrchestrator(
        backend=backend or StubBackend(),
        providers={
            ModelTier.COST_EFFICIENT: cheap,
            ModelTier.PREMIUM: premium,
        },
    )


def _request(*signals: ComplexitySignal) -> UserResearchRequest:
    return UserResearchRequest(
        symbol="INFY",
        question="Is Infosys a quality compounder at this price?",
        complexity_signals=signals,
        request_id="case-1",
    )


def test_valid_simple_research_flow() -> None:
    cheap = ScriptedProvider("deepseek", "deepseek-chat", ["json"])
    result = _orchestrator(cheap=cheap).run(_request())
    assert result.status is OrchestratorStatus.ACCEPTED
    assert result.gate.outcome is GateOutcome.ACCEPTED
    assert result.public.recommendation == "Buy"
    assert result.public.valuation in {"180.0", "180"}
    assert result.public.confidence == 0.72
    assert result.public.evidence_citations
    assert_no_private_leakage(result.public.to_dict())
    assert cheap.calls == 1


def test_valid_complex_research_flow() -> None:
    premium = ScriptedProvider("anthropic", "claude-3-5-sonnet-20241022", ["json"])
    result = _orchestrator(premium=premium).run(
        _request(ComplexitySignal.CONFLICTING_EVIDENCE)
    )
    assert result.status is OrchestratorStatus.ACCEPTED
    assert result.private.routing_tier == ModelTier.PREMIUM.value
    assert premium.calls == 1
    assert result.to_public().recommendation == "Buy"


def test_cost_efficient_routing() -> None:
    result = _orchestrator().run(_request())
    assert result.private.routing_tier == ModelTier.COST_EFFICIENT.value
    assert result.private.routing_reasons == ()
    assert "routing_tier" not in result.public.to_dict()


def test_premium_routing() -> None:
    result = _orchestrator().run(_request(ComplexitySignal.MATERIAL_RISK))
    assert result.private.routing_tier == ModelTier.PREMIUM.value
    assert "material_risk" in result.private.routing_reasons
    dumped = json.dumps(result.public.to_dict())
    assert "material_risk" not in dumped
    assert "premium" not in dumped


def test_escalation_from_cost_efficient_failure() -> None:
    cheap = ScriptedProvider("deepseek", "deepseek-chat", ["fail"])
    premium = ScriptedProvider("anthropic", "claude-3-5-sonnet-20241022", ["json"])
    result = _orchestrator(cheap=cheap, premium=premium).run(_request())
    assert result.status is OrchestratorStatus.ACCEPTED
    assert cheap.calls == 1
    assert premium.calls == 1
    assert result.public.recommendation == "Buy"


def test_provider_failure_fail_closed() -> None:
    cheap = ScriptedProvider("deepseek", "deepseek-chat", ["fail"])
    premium = ScriptedProvider("anthropic", "claude-3-5-sonnet-20241022", ["unavailable"])
    result = _orchestrator(cheap=cheap, premium=premium).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED
    assert result.gate.outcome is GateOutcome.FAILED_CLOSED
    assert result.public.recommendation == "Unable to complete."
    assert result.public.valuation is None
    assert result.public.confidence == 0.0


def test_tool_failure_fail_closed() -> None:
    result = _orchestrator(backend=StubBackend(raise_on="recommendation")).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED
    assert result.public.recommendation == "Unable to complete."


def test_malformed_ai_output_fail_closed() -> None:
    cheap = ScriptedProvider("deepseek", "deepseek-chat", ["malformed"])
    premium = ScriptedProvider("anthropic", "claude-3-5-sonnet-20241022", ["malformed"])
    result = _orchestrator(cheap=cheap, premium=premium).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED


def test_missing_evidence_fail_closed() -> None:
    cheap = ScriptedProvider("deepseek", "deepseek-chat", ["missing_evidence"])
    premium = ScriptedProvider("anthropic", "claude-3-5-sonnet-20241022", ["missing_evidence"])
    result = _orchestrator(cheap=cheap, premium=premium).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED


def test_unsupported_claim_fail_closed() -> None:
    cheap = ScriptedProvider("deepseek", "deepseek-chat", ["unsupported"])
    premium = ScriptedProvider("anthropic", "claude-3-5-sonnet-20241022", ["unsupported"])
    result = _orchestrator(cheap=cheap, premium=premium).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED


def test_ai_cannot_override_dsp_recommendation() -> None:
    cheap = ScriptedProvider("deepseek", "deepseek-chat", ["override"])
    premium = ScriptedProvider("anthropic", "claude-3-5-sonnet-20241022", ["override"])
    result = _orchestrator(cheap=cheap, premium=premium).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED
    assert result.public.recommendation != "Sell"


def test_privacy_leakage_rejected() -> None:
    cheap = ScriptedProvider("deepseek", "deepseek-chat", ["raw_leak"])
    premium = ScriptedProvider("anthropic", "claude-3-5-sonnet-20241022", ["raw_leak"])
    result = _orchestrator(cheap=cheap, premium=premium).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED
    dumped = json.dumps(result.public.to_dict())
    assert "routing_reasons" not in dumped
    assert "chain_of_thought" not in dumped


def test_prompt_leakage_rejected() -> None:
    cheap = ScriptedProvider("deepseek", "deepseek-chat", ["prompt_leak"])
    premium = ScriptedProvider("anthropic", "claude-3-5-sonnet-20241022", ["prompt_leak"])
    result = _orchestrator(cheap=cheap, premium=premium).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED
    assert PRIVATE_PROMPT_CANARY not in json.dumps(result.public.to_dict())


def test_raw_response_and_prompt_stay_private_on_success() -> None:
    result = _orchestrator().run(_request())
    public = result.to_public().to_dict()
    assert_no_private_leakage(public)
    dumped = json.dumps(public)
    assert PRIVATE_PROMPT_CANARY not in dumped
    assert PRIVATE_PROMPT_CANARY in result.private.internal_prompt
    assert result.private.raw_ai_response
    assert "raw_ai_response" not in public
    assert "internal_prompt" not in public
    assert "provider" not in public
    assert "model" not in public
    assert "input_tokens" not in public
    assert "tool_calls" not in public


def test_fail_closed_does_not_fabricate_decision() -> None:
    result = _orchestrator(script=["fail"], premium_script=["fail"]).run(_request())
    assert result.public.recommendation == "Unable to complete."
    assert "Buy" not in result.public.analysis
    assert result.public.limitations == ("research_failed_closed",)


def test_deterministic_tool_usage() -> None:
    a = _orchestrator().run(_request())
    b = _orchestrator().run(_request())
    assert a.public == b.public
    assert a.private.tool_calls == b.private.tool_calls


def test_provider_neutrality_same_public_pack() -> None:
    packs = []
    for provider_id, model in (
        ("openai", "gpt-4o-mini"),
        ("deepseek", "deepseek-chat"),
        ("gemini", "gemini-1.5-flash"),
        ("anthropic", "claude-3-5-sonnet-20241022"),
    ):
        cheap = ScriptedProvider(provider_id, model, ["json"])
        premium = ScriptedProvider(provider_id, model, ["json"])
        result = _orchestrator(cheap=cheap, premium=premium).run(_request())
        assert result.status is OrchestratorStatus.ACCEPTED
        packs.append(result.public)
        dumped = json.dumps(result.public.to_dict()).lower()
        assert provider_id not in dumped
        assert "gpt-4o" not in dumped
        assert "claude" not in dumped
        assert "gemini" not in dumped
        assert "deepseek" not in dumped
    assert packs[0] == packs[1] == packs[2] == packs[3]


def test_public_decision_pack_correctness() -> None:
    result = _orchestrator().run(_request())
    pack = result.public
    assert pack.schema_version == "public_decision_pack_v1"
    assert pack.recommendation == "Buy"
    assert pack.analysis
    assert pack.risks
    assert pack.evidence_citations
    assert 0.0 <= pack.confidence <= 1.0
    assert PRIVATE_PROMPT_CANARY not in pack.analysis


def test_ai_requested_tool_passes_through_boundary() -> None:
    extra = ToolCall(
        call_id="ai-1",
        name="dsp.management_quality",
        arguments={"symbol": "INFY"},
    )
    cheap = ScriptedProvider("deepseek", "deepseek-chat", [extra, "json"])
    result = _orchestrator(cheap=cheap).run(_request())
    assert result.status is OrchestratorStatus.ACCEPTED
    names = {row["tool_name"] for row in result.private.tool_calls}
    assert "dsp.management_quality" in names
    assert cheap.calls == 2


def test_unknown_ai_tool_does_not_fabricate() -> None:
    extra = ToolCall(
        call_id="ai-bad",
        name="dsp.not_a_tool",
        arguments={"symbol": "INFY"},
    )
    cheap = ScriptedProvider("deepseek", "deepseek-chat", [extra, "json"])
    result = _orchestrator(cheap=cheap).run(_request())
    statuses = {row["tool_name"]: row["status"] for row in result.private.tool_calls}
    assert statuses["dsp.not_a_tool"] == "unknown_tool"
    assert result.status is OrchestratorStatus.ACCEPTED


def test_spec_uses_only_public_manifest_tools() -> None:
    registry = ToolRegistry.default()
    spec = ResearchSpecification.from_user_request(
        _request(),
        allowed_tools=registry.names(),
    )
    assert set(spec.required_tools).issubset(set(SIMPLE_TOOLS))
    assert set(spec.required_tools).issubset(set(registry.names()))


def test_private_prompt_never_in_public_pack() -> None:
    spec = ResearchSpecification.from_user_request(
        _request(),
        allowed_tools=ToolRegistry.default().names(),
    )
    parts = build_research_prompt(spec, evidence_catalog=(), tool_manifest=[])
    assert PRIVATE_PROMPT_CANARY in parts[0]
    result = _orchestrator().run(_request())
    assert PRIVATE_PROMPT_CANARY not in json.dumps(result.public.to_dict())


def test_adapter_backed_provider_has_no_http_in_orchestrator() -> None:
    import inspect

    from llm_adapters.orchestrator.provider import AdapterBackedAIProvider

    source = inspect.getsource(AdapterBackedAIProvider)
    assert "httpx" not in source
    assert "api.openai.com" not in source


def test_production_ai_remains_blocked() -> None:
    from llm_adapters.activation_evidence import (
        ActivationEvidence,
        BenchmarkEvidence,
        ConfigurationEvidence,
        FailClosedEvidence,
        PrivacyEvidence,
        ToolEvidence,
    )
    from llm_adapters.activation_guard import ActivationState, evaluate_activation

    verdict = evaluate_activation(
        ActivationEvidence(
            benchmark=BenchmarkEvidence.empty(),
            successful_evaluations=(),
            configuration=ConfigurationEvidence(
                default_provider="deterministic",
                cost_efficient_model="",
                premium_model="",
                available_providers=(),
                pricing_known_for_all_tiers=False,
                routing_tier_count=0,
                all_provider_keys_configured=False,
            ),
            tools=ToolEvidence(
                available_tools=(),
                minimum_tool_count=1,
                all_tools_healthy=False,
            ),
            privacy=PrivacyEvidence(False, False, False, False),
            fail_closed=FailClosedEvidence(False, False, False, False),
            required_quality_threshold=60.0,
        )
    )
    assert verdict.state is ActivationState.AI_PRODUCTION_BLOCKED


def test_unavailable_recommendation_does_not_invent_buy() -> None:
    result = _orchestrator(backend=StubBackend(empty_rec=True)).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED
    assert result.public.recommendation == "Unable to complete."
