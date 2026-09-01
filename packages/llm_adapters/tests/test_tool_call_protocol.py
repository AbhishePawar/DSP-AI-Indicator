"""Provider-neutral tool-call protocol tests (no paid provider calls)."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from copilot.enums import UserIntentType
from copilot.models import LanguageModelRequest
from llm_adapters.anthropic_adapter import AnthropicAdapter
from llm_adapters.config import LLMPlatformConfig
from llm_adapters.deepseek_adapter import DeepSeekAdapter
from llm_adapters.gemini_adapter import GeminiAdapter
from llm_adapters.openai_adapter import OpenAIAdapter
from llm_adapters.tools import ToolRegistry
from llm_adapters.tools.protocol import (
    ToolCall,
    ToolCallBoundary,
    ToolCallOutcome,
    ToolCallStatus,
    declarations_as_anthropic_tools,
    declarations_as_gemini_functions,
    declarations_as_openai_tools,
    parse_anthropic_tool_use,
    parse_gemini_function_calls,
    parse_openai_tool_calls,
)
from llm_adapters.tools.protocol.openai_compatible import OpenAICompatibleToolCalling


# --- stub backend (no DSP engines, no network) -----------------------------


class StubBackend:
    def __init__(
        self,
        *,
        valuation: dict | None = None,
        statements: dict | None | object = ...,
        raise_on: str | None = None,
    ) -> None:
        self._valuation = valuation if valuation is not None else {
            "intrinsic_value_per_share": 180.0,
            "current_market_price": 150.0,
            "method": "two-stage DCF",
            "as_of": "2026-09-01T00:00:00Z",
        }
        if statements is ...:
            self._statements = {
                "periods": ["2024"],
                "currency": "INR",
                "source": "dsp.financial_statements",
            }
        else:
            self._statements = statements
        self._raise_on = raise_on

    def get_authenticated_financial_statements(self, symbol, *, exchange=None):
        if self._raise_on == "statements":
            raise RuntimeError("data unavailable")
        if self._statements is None:
            return None
        return dict(self._statements)

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
        if self._raise_on == "valuation":
            raise RuntimeError("valuation failed")
        return dict(self._valuation)

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


def _allowed() -> frozenset[str]:
    return frozenset(ToolRegistry.default().names())


def _config() -> LLMPlatformConfig:
    return LLMPlatformConfig(
        default_provider="openai",
        openai_api_key="test-openai",
        anthropic_api_key="test-anthropic",
        gemini_api_key="test-gemini",
        deepseek_api_key="test-deepseek",
        openai_model="gpt-4o-mini",
        anthropic_model="claude-3-5-sonnet-20241022",
        gemini_model="gemini-1.5-flash",
        deepseek_model="deepseek-chat",
        request_timeout_seconds=5.0,
        max_retries=0,
    )


def _request() -> LanguageModelRequest:
    return LanguageModelRequest(
        request_id="req-1",
        intent_class=UserIntentType.EXPLAIN_REPORT,
        prompt_parts=("system rules", "user question"),
        context_digest_ids=("Recommendation",),
        provenance=("test",),
    )


# --- declarations from public_manifest only --------------------------------


def test_declarations_cover_exactly_the_public_manifest() -> None:
    registry = ToolRegistry.default()
    manifest = registry.public_manifest()
    names = {entry["name"] for entry in manifest}
    openai_tools = declarations_as_openai_tools(manifest)
    gemini_fns = declarations_as_gemini_functions(manifest)
    anthropic_tools = declarations_as_anthropic_tools(manifest)
    assert len(openai_tools) == len(manifest) == 17
    assert len(gemini_fns) == 17
    assert len(anthropic_tools) == 17
    openai_names = {t["function"]["name"] for t in openai_tools}
    gemini_names = {t["name"] for t in gemini_fns}
    anthropic_names = {t["name"] for t in anthropic_tools}
    expected_provider = {n.replace(".", "_") for n in names}
    assert openai_names == expected_provider
    assert gemini_names == expected_provider
    assert anthropic_names == expected_provider
    for entry in openai_tools:
        dumped = json.dumps(entry)
        assert "provenance" not in dumped
        assert "dsp_platform" not in dumped
        assert "api_key" not in dumped


def test_boundary_declarations_match_public_manifest() -> None:
    boundary = _boundary()
    decls = boundary.declarations()
    manifest_names = [e["name"] for e in boundary.public_manifest()]
    assert [d.name for d in decls] == manifest_names
    for decl in decls:
        assert decl.name in _allowed()
        assert not hasattr(decl, "provenance")


# --- dispatcher fail-closed ------------------------------------------------


def test_valid_internal_call_returns_ok() -> None:
    outcome = _boundary().execute(
        ToolCall(call_id="c1", name="dsp.valuation", arguments={"symbol": "AAPL"})
    )
    assert outcome.status is ToolCallStatus.OK
    assert outcome.result is not None
    assert outcome.result.result["intrinsic_value_per_share"] == 180.0
    payload = outcome.provider_payload()
    assert payload["status"] == "ok"
    assert "audit" not in payload
    assert "provider" not in payload


def test_unknown_tool_fails_closed() -> None:
    outcome = _boundary().execute(
        ToolCall(call_id="c1", name="os.system", arguments={"cmd": "id"})
    )
    assert outcome.status is ToolCallStatus.UNKNOWN_TOOL
    assert outcome.result is None
    assert outcome.provider_payload()["status"] == "unknown_tool"


def test_unapproved_registered_tool_is_unauthorized() -> None:
    boundary = _boundary()
    boundary._allowed = frozenset(n for n in boundary._allowed if n != "dsp.valuation")
    outcome = boundary.execute(
        ToolCall(call_id="c1", name="dsp.valuation", arguments={"symbol": "AAPL"})
    )
    assert outcome.status is ToolCallStatus.UNAUTHORIZED
    assert outcome.result is None


def test_malformed_arguments_fail_closed() -> None:
    outcome = _boundary().execute(
        ToolCall(call_id="c1", name="dsp.valuation", arguments=["AAPL"])  # type: ignore[arg-type]
    )
    assert outcome.status is ToolCallStatus.MALFORMED


def test_invalid_arguments_fail_closed() -> None:
    outcome = _boundary().execute(
        ToolCall(call_id="c1", name="dsp.valuation", arguments={})
    )
    assert outcome.status is ToolCallStatus.INVALID_ARGUMENTS


def test_wrong_argument_type_fail_closed() -> None:
    outcome = _boundary().execute(
        ToolCall(call_id="c1", name="dsp.valuation", arguments={"symbol": 12})
    )
    assert outcome.status is ToolCallStatus.INVALID_ARGUMENTS


def test_tool_failure_fail_closed() -> None:
    outcome = _boundary(StubBackend(raise_on="valuation")).execute(
        ToolCall(call_id="c1", name="dsp.valuation", arguments={"symbol": "AAPL"})
    )
    assert outcome.status is ToolCallStatus.TOOL_FAILED
    assert "api_key" not in outcome.provider_payload()["result"]["reason"].lower()


def test_unavailable_data_is_explicit() -> None:
    outcome = _boundary(StubBackend(statements=None)).execute(
        ToolCall(
            call_id="c1",
            name="dsp.financial_statements",
            arguments={"symbol": "AAPL"},
        )
    )
    assert outcome.status is ToolCallStatus.UNAVAILABLE


def test_missing_call_id_is_malformed() -> None:
    outcome = _boundary().execute(
        ToolCall(call_id="", name="dsp.valuation", arguments={"symbol": "AAPL"})
    )
    assert outcome.status is ToolCallStatus.MALFORMED


# --- OpenAI ----------------------------------------------------------------


def test_openai_roundtrip_success() -> None:
    adapter = OpenAIAdapter(_config())
    boundary = _boundary()
    payload = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "id": "call_val",
                            "type": "function",
                            "function": {
                                "name": "dsp_valuation",
                                "arguments": '{"symbol":"INFY"}',
                            },
                        }
                    ]
                }
            }
        ]
    }
    outcomes, messages = adapter.execute_provider_tool_calls(payload, boundary)
    assert len(outcomes) == 1
    assert outcomes[0].status is ToolCallStatus.OK
    assert outcomes[0].result is not None
    assert outcomes[0].result.result["intrinsic_value_per_share"] == 180.0
    assert messages[0]["role"] == "tool"
    assert messages[0]["tool_call_id"] == "call_val"
    body = json.loads(messages[0]["content"])
    assert body["status"] == "ok"
    assert "routing_reasons" not in body
    assert "input_tokens" not in body


def test_openai_malformed_json_arguments() -> None:
    parsed = parse_openai_tool_calls(
        {
            "tool_calls": [
                {
                    "id": "call_bad",
                    "type": "function",
                    "function": {"name": "dsp_valuation", "arguments": "{not-json"},
                }
            ]
        },
        allowed_internal=_allowed(),
    )
    assert len(parsed) == 1
    assert isinstance(parsed[0], ToolCallOutcome)
    assert parsed[0].status is ToolCallStatus.MALFORMED


def test_openai_unknown_tool() -> None:
    parsed = parse_openai_tool_calls(
        {
            "tool_calls": [
                {
                    "id": "call_x",
                    "type": "function",
                    "function": {"name": "secret_internal_engine", "arguments": "{}"},
                }
            ]
        },
        allowed_internal=_allowed(),
    )
    assert parsed[0].status is ToolCallStatus.UNKNOWN_TOOL  # type: ignore[union-attr]


def test_openai_missing_id_is_malformed() -> None:
    parsed = parse_openai_tool_calls(
        {
            "tool_calls": [
                {
                    "type": "function",
                    "function": {"name": "dsp_valuation", "arguments": "{}"},
                }
            ]
        },
        allowed_internal=_allowed(),
    )
    assert parsed[0].status is ToolCallStatus.MALFORMED  # type: ignore[union-attr]


def test_openai_invoke_does_not_send_tools() -> None:
    adapter = OpenAIAdapter(_config())
    captured: dict[str, Any] = {}

    def fake_post(*args: Any, **kwargs: Any) -> MagicMock:
        captured["json"] = kwargs.get("json")
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        return resp

    with patch("llm_adapters.openai_adapter.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.side_effect = fake_post
        adapter.invoke(_request())
    assert captured["json"] is not None
    assert "tools" not in captured["json"]
    assert "tool_choice" not in captured["json"]


# --- DeepSeek shares OpenAI-compatible layer --------------------------------


def test_deepseek_uses_identical_openai_compatible_protocol() -> None:
    openai = OpenAIAdapter(_config())
    deepseek = DeepSeekAdapter(_config())
    boundary = _boundary()
    payload = {
        "tool_calls": [
            {
                "id": "call_ds",
                "type": "function",
                "function": {
                    "name": "dsp_margin_of_safety",
                    "arguments": {"symbol": "TCS"},
                },
            }
        ]
    }
    o_out, o_msg = openai.execute_provider_tool_calls(payload, boundary)
    d_out, d_msg = deepseek.execute_provider_tool_calls(payload, boundary)
    assert o_out[0].status is ToolCallStatus.OK
    assert d_out[0].status is ToolCallStatus.OK
    assert o_out[0].result == d_out[0].result
    assert o_msg == d_msg
    assert openai.parse_tool_calls.__func__ is deepseek.parse_tool_calls.__func__
    assert openai.tool_declarations.__func__ is deepseek.tool_declarations.__func__
    assert isinstance(openai, OpenAICompatibleToolCalling)
    assert isinstance(deepseek, OpenAICompatibleToolCalling)


def test_deepseek_invoke_does_not_send_tools() -> None:
    adapter = DeepSeekAdapter(_config())
    captured: dict[str, Any] = {}

    def fake_post(*args: Any, **kwargs: Any) -> MagicMock:
        captured["json"] = kwargs.get("json")
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        return resp

    with patch("llm_adapters.deepseek_adapter.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.side_effect = fake_post
        adapter.invoke(_request())
    assert "tools" not in captured["json"]


# --- Gemini ----------------------------------------------------------------


def test_gemini_roundtrip_success() -> None:
    adapter = GeminiAdapter(_config())
    boundary = _boundary()
    payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "functionCall": {
                                "name": "dsp_economic_moat",
                                "args": {"symbol": "INFY"},
                            }
                        }
                    ]
                }
            }
        ]
    }
    outcomes, parts = adapter.execute_provider_tool_calls(payload, boundary)
    assert outcomes[0].status is ToolCallStatus.OK
    assert outcomes[0].result is not None
    assert outcomes[0].result.result["moat"] == "Wide"
    assert "functionResponse" in parts[0]
    assert parts[0]["functionResponse"]["name"] == "dsp_economic_moat"
    assert parts[0]["functionResponse"]["response"]["status"] == "ok"


def test_gemini_declarations_use_uppercase_schema_types() -> None:
    fns = declarations_as_gemini_functions(ToolRegistry.default().public_manifest())
    valuation = next(f for f in fns if f["name"] == "dsp_valuation")
    assert valuation["parameters"]["type"] == "OBJECT"
    assert valuation["parameters"]["properties"]["symbol"]["type"] == "STRING"


def test_gemini_unknown_and_malformed() -> None:
    unknown = parse_gemini_function_calls(
        {"functionCall": {"name": "delete_all", "args": {}}},
        allowed_internal=_allowed(),
    )
    assert unknown[0].status is ToolCallStatus.UNKNOWN_TOOL  # type: ignore[union-attr]
    malformed = parse_gemini_function_calls(
        {"functionCall": {"name": "dsp_valuation", "args": ["INFY"]}},
        allowed_internal=_allowed(),
    )
    assert malformed[0].status is ToolCallStatus.MALFORMED  # type: ignore[union-attr]


def test_gemini_invoke_does_not_send_function_declarations() -> None:
    adapter = GeminiAdapter(_config())
    captured: dict[str, Any] = {}

    def fake_post(*args: Any, **kwargs: Any) -> MagicMock:
        captured["json"] = kwargs.get("json")
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "ok"}]}}]
        }
        return resp

    with patch("llm_adapters.gemini_adapter.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.side_effect = fake_post
        adapter.invoke(_request())
    assert "tools" not in captured["json"]
    assert "functionDeclarations" not in json.dumps(captured["json"])


# --- Anthropic -------------------------------------------------------------


def test_anthropic_roundtrip_success() -> None:
    adapter = AnthropicAdapter(_config())
    boundary = _boundary()
    payload = {
        "content": [
            {"type": "text", "text": "checking valuation"},
            {
                "type": "tool_use",
                "id": "toolu_01",
                "name": "dsp_valuation",
                "input": {"symbol": "INFY"},
            },
        ]
    }
    outcomes, blocks = adapter.execute_provider_tool_calls(payload, boundary)
    assert outcomes[0].status is ToolCallStatus.OK
    assert blocks[0]["type"] == "tool_result"
    assert blocks[0]["tool_use_id"] == "toolu_01"
    assert blocks[0]["is_error"] is False
    body = json.loads(blocks[0]["content"])
    assert body["result"]["intrinsic_value_per_share"] == 180.0


def test_anthropic_error_sets_is_error() -> None:
    adapter = AnthropicAdapter(_config())
    boundary = _boundary()
    payload = {
        "type": "tool_use",
        "id": "toolu_bad",
        "name": "not_a_tool",
        "input": {},
    }
    outcomes, blocks = adapter.execute_provider_tool_calls(payload, boundary)
    assert outcomes[0].status is ToolCallStatus.UNKNOWN_TOOL
    assert blocks[0]["is_error"] is True


def test_anthropic_malformed_input() -> None:
    parsed = parse_anthropic_tool_use(
        {"type": "tool_use", "id": "toolu_1", "name": "dsp_valuation", "input": "not-json{"},
        allowed_internal=_allowed(),
    )
    assert parsed[0].status is ToolCallStatus.MALFORMED  # type: ignore[union-attr]


def test_anthropic_invoke_does_not_send_tools() -> None:
    adapter = AnthropicAdapter(_config())
    captured: dict[str, Any] = {}

    def fake_post(*args: Any, **kwargs: Any) -> MagicMock:
        captured["json"] = kwargs.get("json")
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"content": [{"type": "text", "text": "ok"}]}
        return resp

    with patch("llm_adapters.anthropic_adapter.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.side_effect = fake_post
        adapter.invoke(_request())
    assert "tools" not in captured["json"]


# --- four-provider parity on the same DSP result ---------------------------


def test_all_four_providers_resolve_the_same_dsp_tool() -> None:
    boundary = _boundary()
    allowed = boundary.allowed_names()
    openai_payload = {
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "dsp_business_quality", "arguments": '{"symbol":"INFY"}'},
            }
        ]
    }
    gemini_payload = {"functionCall": {"name": "dsp_business_quality", "args": {"symbol": "INFY"}}}
    anthropic_payload = {
        "type": "tool_use",
        "id": "toolu_1",
        "name": "dsp_business_quality",
        "input": {"symbol": "INFY"},
    }
    o = ToolCallBoundary(ToolRegistry.default(), StubBackend()).execute_many(
        parse_openai_tool_calls(openai_payload, allowed_internal=allowed)
    )
    d = ToolCallBoundary(ToolRegistry.default(), StubBackend()).execute_many(
        parse_openai_tool_calls(openai_payload, allowed_internal=allowed)
    )
    g = ToolCallBoundary(ToolRegistry.default(), StubBackend()).execute_many(
        parse_gemini_function_calls(gemini_payload, allowed_internal=allowed)
    )
    a = ToolCallBoundary(ToolRegistry.default(), StubBackend()).execute_many(
        parse_anthropic_tool_use(anthropic_payload, allowed_internal=allowed)
    )
    assert o[0].status is d[0].status is g[0].status is a[0].status is ToolCallStatus.OK
    assert o[0].result == d[0].result == g[0].result == a[0].result


# --- isolation: protocol is not wired to analyse or production AI ----------


def test_protocol_modules_do_not_reference_analyse_or_httpx() -> None:
    protocol_dir = (
        Path(__file__).resolve().parents[1] / "src" / "llm_adapters" / "tools" / "protocol"
    )
    for path in protocol_dir.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "/api/v1/analyse" not in text
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".", 1)[0] != "httpx"
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".", 1)[0] != "httpx"


def test_production_ai_activation_remains_blocked() -> None:
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
            privacy=PrivacyEvidence(
                private_fields_enumerated=False,
                public_pack_present=False,
                leakage_guard_active=False,
                benchmark_report_audited=False,
            ),
            fail_closed=FailClosedEvidence(
                quality_gate_present=False,
                no_fabrication_guarantee=False,
                deterministic_fallback_present=False,
                escalation_present=False,
            ),
            required_quality_threshold=60.0,
        )
    )
    assert verdict.state is ActivationState.AI_PRODUCTION_BLOCKED
    assert not verdict.is_ready()
