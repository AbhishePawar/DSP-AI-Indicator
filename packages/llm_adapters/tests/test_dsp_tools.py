"""Tests for the DSP trusted tool interface (registry + dispatcher)."""

from __future__ import annotations

import pytest

from llm_adapters.tools import (
    DEFAULT_TOOL_NAMES,
    DSPToolBackend,
    ToolRegistry,
    ToolResult,
    ToolSpec,
    ToolStatus,
    assert_no_tool_leakage,
)
from llm_adapters.tools.contract import ToolInputField, ToolOutputField
from llm_adapters.privacy_boundary import (
    PrivateInternalResult,
    PublicDecisionPack,
    assert_no_private_leakage,
)


# --- stub backend ---------------------------------------------------------

_SENTINEL = object()


class StubBackend:
    """Implements the DSPToolBackend protocol for tests."""

    def __init__(
        self,
        *,
        valuation: dict | None = None,
        moat: dict | None = None,
        research: dict | None = None,
        comparison: dict | None = None,
        statements: object = _SENTINEL,
        raise_on: str | None = None,
    ) -> None:
        self._valuation = valuation or {
            "intrinsic_value_per_share": 180.0,
            "current_market_price": 150.0,
            "method": "two-stage DCF",
            "as_of": "2026-09-01T00:00:00Z",
        }
        self._moat = moat or {"moat": "Wide", "score": 0.8}
        self._research = research or {
            "lineage_id": "lin-1",
            "evidence_refs": ["r1", "r2"],
            "summary": {"headline": "OK"},
        }
        self._comparison = comparison or {
            "dimensions": [{"name": "valuation", "winner": "A"}],
            "summary": {"winner": "A"},
        }
        # Allow callers to pass None to mean "no data available".
        if statements is _SENTINEL:
            self._statements = {
                "periods": ["2024", "2023"],
                "currency": "INR",
                "source": "dsp.financial_statements",
                "as_of": "2026-09-01T00:00:00Z",
            }
        else:
            self._statements = statements
        self._raise_on = raise_on

    def get_authenticated_financial_statements(self, symbol: str, *, exchange: str | None = None):
        if self._raise_on == "statements":
            raise RuntimeError("data unavailable")
        if self._statements is None:
            return None
        return dict(self._statements, _symbol=symbol)

    def financial_statement_health(self):
        return {"ok": True}

    def analyze_company(self, request):
        return {"decision": "Buy", "confidence": 0.7}

    def compare_companies(self, packs):
        return {"summary": {}}

    def ask_research_copilot(self, question, **kwargs):
        return {"answer": "ok"}

    def build_research_object(self, symbol, **kwargs):
        if self._raise_on == "research":
            raise RuntimeError("research failed")
        return dict(self._research, _symbol=symbol)

    def get_research_snapshot(self, snapshot_id):
        return {"lineage_id": snapshot_id}

    def run_copilot_v2(self, **kwargs):
        return {"message": "ok"}

    # tool backend extensions
    def get_financial_quality(self, *, symbol):
        return {"metrics": {"roe": 0.18}, "as_of": "2026-09-01T00:00:00Z"}

    def get_valuation(self, *, symbol):
        return dict(self._valuation, _symbol=symbol)

    def get_margin_of_safety(self, *, symbol):
        return {"margin_of_safety": 0.2, "basis": "dsp.valuation"}

    def get_economic_moat(self, *, symbol):
        return dict(self._moat, _symbol=symbol)

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
        return {"signals": [{"name": "trend", "value": "up"}], "direction": "BULLISH"}

    def get_investment_recommendation(self, *, symbol):
        return {"decision": "Buy", "confidence": 0.8, "margin_of_safety": 0.2}

    def run_deterministic_committee(self, *, symbol):
        return {
            "decision": "BUY",
            "votes": {"fundamental": "BUY", "technical": "HOLD"},
            "confidence": 0.7,
        }

    def compare_two_symbols(self, *, symbol_a, symbol_b):
        return dict(self._comparison, _a=symbol_a, _b=symbol_b)


# --- registry shape --------------------------------------------------------


def test_registry_contains_only_approved_tools() -> None:
    registry = ToolRegistry.default()
    assert set(registry.names()) == set(DEFAULT_TOOL_NAMES)
    # The brief required all 17 categories.
    expected = {
        "dsp.financial_statements", "dsp.financial_quality",
        "dsp.valuation", "dsp.margin_of_safety", "dsp.economic_moat",
        "dsp.management_quality", "dsp.financial_strength",
        "dsp.earnings_quality", "dsp.growth_quality",
        "dsp.business_quality", "dsp.risk", "dsp.quantitative_risk",
        "dsp.technical_signals", "dsp.investment_recommendation",
        "dsp.deterministic_committee", "dsp.research_object",
        "dsp.comparison",
    }
    assert expected.issubset(set(registry.names()))


def test_every_tool_has_typed_schemas() -> None:
    registry = ToolRegistry.default()
    for name in registry.names():
        spec = registry.get_spec(name)
        assert spec is not None
        assert spec.name
        assert spec.version
        assert spec.description
        assert spec.provenance
        assert spec.input_schema  # at least one field
        assert spec.output_schema
        # every input field has a name and type
        for f in spec.input_schema:
            assert isinstance(f, ToolInputField)
            assert f.name
            assert f.type
        for f in spec.output_schema:
            assert isinstance(f, ToolOutputField)
            assert f.name
            assert f.type


# --- valid invocation ------------------------------------------------------


def test_valid_invocation_returns_typed_result() -> None:
    registry = ToolRegistry.default()
    backend = StubBackend()
    result = registry.dispatch("dsp.valuation", {"symbol": "AAPL"}, backend)
    assert isinstance(result, ToolResult)
    assert result.status is ToolStatus.OK
    assert result.tool_name == "dsp.valuation"
    assert result.tool_version == "1.0.0"
    assert result.result["intrinsic_value_per_share"] == 180.0
    assert result.calculation_metadata["as_of"] == "2026-09-01T00:00:00Z"
    assert result.is_success()


def test_deterministic_tool_returns_deterministic_results() -> None:
    """Two invocations of the same tool with the same input must match."""
    registry = ToolRegistry.default()
    backend = StubBackend()
    a = registry.dispatch("dsp.valuation", {"symbol": "AAPL"}, backend)
    b = registry.dispatch("dsp.valuation", {"symbol": "AAPL"}, backend)
    assert a == b


def test_tool_results_carry_evidence_refs() -> None:
    registry = ToolRegistry.default()
    backend = StubBackend()
    result = registry.dispatch("dsp.research_object", {"symbol": "AAPL"}, backend)
    assert result.status is ToolStatus.OK
    assert "r1" in result.evidence_refs
    assert "r2" in result.evidence_refs


# --- invalid input ---------------------------------------------------------


def test_invalid_input_rejected() -> None:
    registry = ToolRegistry.default()
    backend = StubBackend()
    result = registry.dispatch("dsp.valuation", {}, backend)  # missing symbol
    assert result.status is ToolStatus.INVALID_INPUT
    assert "missing required" in result.limitations[0].lower()


def test_invalid_type_rejected() -> None:
    registry = ToolRegistry.default()
    backend = StubBackend()
    result = registry.dispatch("dsp.valuation", {"symbol": 123}, backend)
    assert result.status is ToolStatus.INVALID_INPUT
    assert "wrong type" in result.limitations[0].lower()


def test_unknown_tool_returns_invalid_input() -> None:
    registry = ToolRegistry.default()
    backend = StubBackend()
    result = registry.dispatch("dsp.not_a_real_tool", {"symbol": "AAPL"}, backend)
    assert result.status is ToolStatus.INVALID_INPUT
    assert "unknown tool" in result.limitations[0].lower()


# --- unavailable / failure -------------------------------------------------


def test_unavailable_data_is_explicit() -> None:
    registry = ToolRegistry.default()
    backend = StubBackend(statements=None)
    result = registry.dispatch("dsp.financial_statements", {"symbol": "AAPL"}, backend)
    # None from backend -> unavailable
    assert result.status is ToolStatus.UNAVAILABLE
    assert "no financial statements available" in result.limitations[0].lower()


def test_calculation_failure_fails_closed() -> None:
    registry = ToolRegistry.default()
    backend = StubBackend(raise_on="statements")
    result = registry.dispatch("dsp.financial_statements", {"symbol": "AAPL"}, backend)
    assert result.status is ToolStatus.FAILED
    assert "RuntimeError" in result.limitations[0]


def test_research_failure_fails_closed() -> None:
    registry = ToolRegistry.default()
    backend = StubBackend(raise_on="research")
    result = registry.dispatch("dsp.research_object", {"symbol": "AAPL"}, backend)
    assert result.status is ToolStatus.FAILED
    assert "RuntimeError" in result.limitations[0]


# --- privacy: tool results carry no private data --------------------------


def test_tool_result_never_carries_private_fields() -> None:
    registry = ToolRegistry.default()
    backend = StubBackend()
    for name in registry.names():
        spec = registry.get_spec(name)
        assert spec is not None
        # Construct a minimal valid input for every tool
        input_ = _minimal_input_for(spec)
        result = registry.dispatch(name, input_, backend)
        # OK, UNAVAILABLE, FAILED, INVALID_INPUT are all valid statuses.
        # The result dict (whichever one) must never carry private fields.
        assert_no_tool_leakage(result.result)
        assert_no_tool_leakage(result.calculation_metadata)
        for ev in result.evidence_refs:
            assert not any(priv in ev for priv in (
                "provider", "model", "internal_prompt", "raw_ai_response",
            ))


def _minimal_input_for(spec: ToolSpec) -> dict:
    """Build a minimal-valid input dict for the given tool spec."""
    return {f.name: _default_for_type(f.type) for f in spec.input_schema if f.required}


def _default_for_type(type_str: str):
    if type_str == "string":
        return "AAPL"
    if type_str == "integer":
        return 1
    if type_str == "number":
        return 1.0
    if type_str == "boolean":
        return False
    if type_str == "object":
        return {}
    if type_str == "array":
        return []
    if type_str == "any":
        return "AAPL"
    raise ValueError(type_str)


def test_public_manifest_has_no_provenance() -> None:
    """Public manifest (sent to LLM) must omit provenance."""
    registry = ToolRegistry.default()
    manifest = registry.public_manifest()
    assert len(manifest) == len(registry.names())
    for entry in manifest:
        assert "name" in entry
        assert "version" in entry
        assert "description" in entry
        assert "input_schema" in entry
        assert "output_schema" in entry
        assert "provenance" not in entry
        assert "validation_status" not in entry


# --- AI cannot bypass canonical DSP engines ------------------------------


def test_backend_methods_must_be_canonical_dsp_methods() -> None:
    """The tool backend protocol lists the methods a backend MAY expose.

    A free-form Python object that does not implement any of these cannot
    be used as a backend. This is enforced by typing (Protocol).
    """
    # The protocol is structural; a class with the right methods matches.
    backend = StubBackend()
    assert isinstance(backend, DSPToolBackend)


def test_missing_backend_method_fails_closed() -> None:
    """A backend without a specific method must produce FAILED, not crash."""

    class BareBackend:
        def get_authenticated_financial_statements(self, symbol, *, exchange=None):
            return {"periods": []}

    registry = ToolRegistry.default()
    bare = BareBackend()
    # 'valuation' tool needs backend.get_valuation; BareBackend lacks it.
    result = registry.dispatch("dsp.valuation", {"symbol": "AAPL"}, bare)
    assert result.status is ToolStatus.FAILED
    assert "backend missing" in result.limitations[0].lower()


# --- PublicDecisionPack privacy boundary still intact --------------------


def test_tool_results_do_not_affect_public_decision_pack_boundary() -> None:
    """The privacy boundary from STEP 3B must still hold alongside the tool layer.

    Tool call records and tool result records are PRIVATE; they must
    never reach the public pack. The public pack may, however, reference
    tool outputs indirectly through ``evidence_citations``.
    """
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
        provider="deepseek",
        model="deepseek-chat",
        routing_tier="cost_efficient",
        routing_reasons=(),
        confidence_requirement=0.6,
        estimated_cost_usd=0.01,
        input_tokens=1000,
        output_tokens=500,
        latency_ms=200,
        model_score=85.0,
        routing_criteria=(),
        internal_prompt="PRIVATE",
        tool_calls=(
            {"name": "dsp.valuation", "input": {"symbol": "AAPL"}},
        ),
        tool_results=(
            {"name": "dsp.valuation", "result": {"intrinsic_value_per_share": 180.0}},
        ),
        raw_ai_response="PRIVATE",
        chain_of_thought="PRIVATE",
    )
    out = private.to_public().to_dict()
    assert_no_private_leakage(out)
    # Provider / model / cost / tokens / internal prompt / raw response
    # / chain-of-thought must not leak.
    flat = str(out).lower()
    for forbidden in (
        "deepseek", "PRIVATE", "raw_ai", "chain_of_thought",
        "internal_prompt", "input_tokens", "output_tokens",
        "estimated_cost", "model_score", "routing_tier",
    ):
        assert forbidden.lower() not in flat
    # The evidence citation referencing the tool is fine.
    assert "dsp.valuation:result" in out["evidence_citations"]


# --- tool count: brief requires 17 categories ------------------------------


def test_seventeen_tools_present() -> None:
    assert len(DEFAULT_TOOL_NAMES) == 17


# --- registry is immutable ------------------------------------------------


def test_registry_is_immutable() -> None:
    """ToolRegistry is a frozen dataclass; attribute assignment is rejected."""
    registry = ToolRegistry.default()
    with pytest.raises(Exception):
        registry._tools = {}  # type: ignore[misc]
