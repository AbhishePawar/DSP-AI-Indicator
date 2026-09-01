"""Privacy tests for the provider-neutral tool-call boundary."""

from __future__ import annotations

import json

import pytest

from llm_adapters.privacy_boundary import (
    PrivateInternalResult,
    PublicDecisionPack,
    assert_no_private_leakage,
)
from llm_adapters.tools import ToolRegistry, assert_no_tool_leakage
from llm_adapters.tools.protocol import (
    ToolCall,
    ToolCallBoundary,
    ToolCallStatus,
    assert_provider_envelope_private_free,
)
from llm_adapters.tools.protocol.dispatcher import safe_provider_payload
from llm_adapters.tools.protocol.privacy import (
    ProtocolPrivacyError,
    failed_privacy_envelope,
)
from llm_adapters.tools.protocol.openai_compatible import format_openai_tool_messages


class StubBackend:
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
        return {"lineage_id": "lin-1", "evidence_refs": ["r1"], "summary": {}}

    def get_research_snapshot(self, snapshot_id):
        return {}

    def run_copilot_v2(self, **kwargs):
        return {}

    def get_financial_quality(self, *, symbol):
        return {"metrics": {"roe": 0.18}, "as_of": "2026-09-01T00:00:00Z"}

    def get_valuation(self, *, symbol):
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
        return {"decision": "Buy", "confidence": 0.8, "margin_of_safety": 0.2}

    def run_deterministic_committee(self, *, symbol):
        return {"decision": "BUY", "votes": {"fundamental": "BUY"}, "confidence": 0.7}

    def compare_two_symbols(self, *, symbol_a, symbol_b):
        return {"dimensions": [], "summary": {}}


def _boundary(backend: StubBackend | None = None) -> ToolCallBoundary:
    return ToolCallBoundary(ToolRegistry.default(), backend or StubBackend())


_FORBIDDEN_SUBSTRINGS = (
    "api_key",
    "sk-live",
    "provider_credentials",
    "internal_prompt",
    "private prompt",
    "dsp_instructions",
    "routing_reasons",
    "estimated_cost",
    "input_tokens",
    "output_tokens",
    "raw_provider",
    "chain_of_thought",
    "Bearer ",
)


def test_successful_envelope_passes_leakage_guards() -> None:
    outcome = _boundary().execute(
        ToolCall(call_id="c1", name="dsp.valuation", arguments={"symbol": "AAPL"})
    )
    payload = outcome.provider_payload()
    assert_no_tool_leakage(payload)
    assert_no_tool_leakage(payload["result"])
    assert_provider_envelope_private_free(payload)
    dumped = json.dumps(payload).lower()
    for token in ("api_key", "routing", "token", "cost", "chain_of_thought", "prompt"):
        assert token not in dumped


def test_provider_messages_never_include_audit_or_secrets() -> None:
    outcome = _boundary().execute(
        ToolCall(call_id="c1", name="dsp.research_object", arguments={"symbol": "AAPL"})
    )
    messages = format_openai_tool_messages((outcome,))
    content = messages[0]["content"]
    body = json.loads(content)
    assert "audit" not in body
    assert "audit" not in messages[0]
    flat = json.dumps(messages)
    for token in _FORBIDDEN_SUBSTRINGS:
        assert token.lower() not in flat.lower()


def test_audit_record_omits_argument_values_and_secrets() -> None:
    outcome = _boundary().execute(
        ToolCall(call_id="c1", name="dsp.valuation", arguments={"symbol": "AAPL"})
    )
    audit = dict(outcome.audit)
    assert audit["argument_keys"] == ("symbol",)
    assert "AAPL" not in json.dumps(audit)
    assert "api_key" not in audit
    assert "provider" not in audit
    assert "cost" not in audit


def test_private_internal_result_still_strips_tool_calls_from_browser() -> None:
    public = PublicDecisionPack(
        recommendation="Buy",
        valuation=None,
        analysis="ok",
        risks=(),
        evidence_citations=("dsp.valuation:result",),
        confidence=0.5,
        limitations=("lm_enrichment",),
    )
    private = PrivateInternalResult(
        public=public,
        provider="openai",
        model="gpt-4o",
        routing_tier="cost_efficient",
        routing_reasons=("latency",),
        confidence_requirement=0.6,
        estimated_cost_usd=0.42,
        input_tokens=111,
        output_tokens=222,
        latency_ms=90,
        model_score=80.0,
        routing_criteria=("quality",),
        internal_prompt="SECRET PROMPT",
        tool_calls=({"name": "dsp.valuation", "input": {"symbol": "AAPL"}},),
        tool_results=({"name": "dsp.valuation", "result": {"intrinsic_value_per_share": 180.0}},),
        raw_ai_response="RAW PROVIDER MESSAGE",
        chain_of_thought="SECRET COT",
    )
    out = private.to_public().to_dict()
    assert_no_private_leakage(out)
    dumped = json.dumps(out)
    for token in (
        "SECRET PROMPT",
        "SECRET COT",
        "RAW PROVIDER",
        "gpt-4o",
        "0.42",
        "tool_calls",
        "tool_results",
        "openai",
        "111",
        "222",
    ):
        assert token not in dumped
    assert "dsp.valuation:result" in out["evidence_citations"]


def test_secret_shaped_envelope_fails_closed() -> None:
    with pytest.raises(ProtocolPrivacyError):
        assert_provider_envelope_private_free(
            {
                "tool_name": "dsp.valuation",
                "status": "ok",
                "result": {"note": "sk-abcdefghijklmnopqrstuvwxyz"},
            }
        )


def test_nested_private_key_fails_closed() -> None:
    with pytest.raises(ProtocolPrivacyError):
        assert_provider_envelope_private_free(
            {
                "tool_name": "dsp.valuation",
                "status": "ok",
                "result": {"routing_reasons": ["never"]},
            }
        )


def test_safe_provider_payload_replaces_leaking_outcome() -> None:
    from llm_adapters.tools.protocol.models import ToolCallError, ToolCallOutcome
    from llm_adapters.tools.contract import ToolResult, ToolStatus

    leaking = ToolCallOutcome(
        call_id="c1",
        tool_name="dsp.valuation",
        status=ToolCallStatus.OK,
        result=ToolResult(
            tool_name="dsp.valuation",
            tool_version="1.0.0",
            status=ToolStatus.OK,
            result={"api_key": "secret"},
            evidence_refs=(),
            calculation_metadata={},
            limitations=(),
        ),
        error=None,
        audit={"call_id": "c1", "tool_name": "dsp.valuation", "status": "ok"},
    )
    payload = safe_provider_payload(leaking)
    assert payload == failed_privacy_envelope("dsp.valuation")
    assert "secret" not in json.dumps(payload)
    assert_provider_envelope_private_free(payload)


def test_error_reason_strips_credential_shaped_text() -> None:
    class LeakyBackend(StubBackend):
        def get_valuation(self, *, symbol):
            raise RuntimeError("OPENAI_API_KEY=sk-live-should-not-leak")

    outcome = ToolCallBoundary(ToolRegistry.default(), LeakyBackend()).execute(
        ToolCall(call_id="c1", name="dsp.valuation", arguments={"symbol": "AAPL"})
    )
    assert outcome.status is ToolCallStatus.TOOL_FAILED
    dumped = json.dumps(outcome.provider_payload())
    assert "sk-live" not in dumped
    assert "OPENAI_API_KEY" not in dumped
    assert "api_key" not in dumped.lower()
