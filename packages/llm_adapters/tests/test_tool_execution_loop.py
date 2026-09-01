"""STEP 3J trusted-tool execution loop tests.

Mocked providers and DSP tools only. No paid API calls.
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from copilot.enums import LanguageModelStatus, UserIntentType
from copilot.models import LanguageModelRequest, LanguageModelResult
from llm_adapters.activation_evidence import (
    ActivationEvidence,
    BenchmarkEvidence,
    ConfigurationEvidence,
    FailClosedEvidence,
    PrivacyEvidence,
    ToolEvidence,
)
from llm_adapters.activation_guard import ActivationState, evaluate_activation
from llm_adapters.config import LLMPlatformConfig
from llm_adapters.model_tiers import ModelTier
from llm_adapters.openai_adapter import OpenAIAdapter
from llm_adapters.orchestrator import (
    AdapterBackedAIProvider,
    OrchestratorStatus,
    ResearchOrchestrator,
    ToolLoopLimits,
)
from llm_adapters.orchestrator.provider import (
    AdapterBackedAIProvider as AdapterProvider,
)
from llm_adapters.privacy_boundary import assert_no_private_leakage
from llm_adapters.tools import DEFAULT_TOOL_NAMES, ToolRegistry
from llm_adapters.tools.protocol.models import ToolCall
from llm_adapters.tools.protocol.openai_compatible import OpenAICompatibleToolCalling

_ORCH_TESTS = importlib.util.spec_from_file_location(
    "dsp_test_research_orchestrator",
    Path(__file__).with_name("test_research_orchestrator.py"),
)
assert _ORCH_TESTS is not None and _ORCH_TESTS.loader is not None
_orch_tests = importlib.util.module_from_spec(_ORCH_TESTS)
_ORCH_TESTS.loader.exec_module(_orch_tests)
ScriptedProvider = _orch_tests.ScriptedProvider
StubBackend = _orch_tests.StubBackend
_happy_json = _orch_tests._happy_json
_orchestrator = _orch_tests._orchestrator
_request = _orch_tests._request


_ORCH_SRC = (
    Path(__file__).resolve().parents[1] / "src" / "llm_adapters" / "orchestrator"
)
_FORBIDDEN_ENGINE_IMPORTS = frozenset(
    {
        "dsp_platform",
        "data_engine",
        "fundamental",
        "composition",
        "valuation",
        "financial",
        "openai",
        "anthropic",
        "httpx",
    }
)


def _fail_both(script: list[Any], **kwargs: Any) -> ResearchOrchestrator:
    cheap = ScriptedProvider("deepseek", "deepseek-chat", list(script))
    premium = ScriptedProvider("anthropic", "claude-3-5-sonnet-20241022", list(script))
    return _orchestrator(cheap=cheap, premium=premium, **kwargs)


def _tool(name: str, call_id: str, **arguments: Any) -> ToolCall:
    return ToolCall(call_id=call_id, name=name, arguments=arguments)


def test_final_answer_without_tool_call() -> None:
    cheap = ScriptedProvider("deepseek", "deepseek-chat", ["json"])
    result = _orchestrator(cheap=cheap).run(_request())
    assert result.status is OrchestratorStatus.ACCEPTED
    assert cheap.calls == 1
    assert result.public.recommendation == "Buy"


def test_one_dsp_tool_call() -> None:
    extra = _tool("dsp.management_quality", "ai-1", symbol="INFY")
    cheap = ScriptedProvider("deepseek", "deepseek-chat", [extra, "json"])
    result = _orchestrator(cheap=cheap).run(_request())
    assert result.status is OrchestratorStatus.ACCEPTED
    names = {row["tool_name"] for row in result.private.tool_calls}
    assert "dsp.management_quality" in names
    assert cheap.calls == 2
    assert cheap.last_prior_tool_results


def test_two_sequential_tool_calls() -> None:
    first = _tool("dsp.financial_statements", "ai-fs", symbol="INFY")
    second = _tool("dsp.valuation", "ai-val", symbol="INFY")
    cheap = ScriptedProvider("deepseek", "deepseek-chat", [first, second, "json"])
    result = _orchestrator(cheap=cheap).run(_request())
    assert result.status is OrchestratorStatus.ACCEPTED
    assert cheap.calls == 3
    names = [row["tool_name"] for row in result.private.tool_calls]
    assert names.count("dsp.financial_statements") >= 1
    assert names.count("dsp.valuation") >= 1


def test_multiple_tool_calls_in_one_provider_response() -> None:
    batch = (
        _tool("dsp.financial_statements", "batch-fs", symbol="INFY"),
        _tool("dsp.valuation", "batch-val", symbol="INFY"),
        _tool("dsp.risk", "batch-risk", symbol="INFY"),
    )
    cheap = ScriptedProvider("deepseek", "deepseek-chat", [batch, "json"])
    result = _orchestrator(cheap=cheap).run(_request())
    assert result.status is OrchestratorStatus.ACCEPTED
    assert cheap.calls == 2
    names = {row["tool_name"] for row in result.private.tool_calls}
    assert {"dsp.financial_statements", "dsp.valuation", "dsp.risk"} <= names


def test_tool_call_followed_by_another_tool_call() -> None:
    first = _tool("dsp.economic_moat", "seq-1", symbol="INFY")
    second = _tool("dsp.business_quality", "seq-2", symbol="INFY")
    cheap = ScriptedProvider("deepseek", "deepseek-chat", [first, second, "json"])
    result = _orchestrator(cheap=cheap).run(_request())
    assert result.status is OrchestratorStatus.ACCEPTED
    assert cheap.calls == 3


def test_invalid_tool_name_fail_closed() -> None:
    extra = _tool("dsp.not_a_tool", "bad-name", symbol="INFY")
    result = _fail_both([extra, "json"]).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED
    assert result.public.recommendation == "Unable to complete."
    statuses = {row["tool_name"]: row["status"] for row in result.private.tool_calls}
    assert statuses["dsp.not_a_tool"] == "unknown_tool"


def test_malformed_tool_arguments_fail_closed() -> None:
    extra = _tool("dsp.valuation", "bad-args", symbol=["INFY"])
    result = _fail_both([extra, "json"]).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED
    assert result.public.recommendation == "Unable to complete."
    statuses = {row["call_id"]: row["status"] for row in result.private.tool_calls}
    assert statuses["bad-args"] == "invalid_arguments"


def test_missing_required_arguments_fail_closed() -> None:
    extra = ToolCall(call_id="missing-symbol", name="dsp.valuation", arguments={})
    result = _fail_both([extra, "json"]).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED
    statuses = {row["call_id"]: row["status"] for row in result.private.tool_calls}
    assert statuses["missing-symbol"] == "invalid_arguments"


def test_dsp_tool_unavailable_fail_closed() -> None:
    extra = _tool("dsp.management_quality", "unavail", symbol="INFY")
    result = _fail_both(
        [extra, "json"],
        backend=StubBackend(none_on="management"),
    ).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED
    assert result.public.recommendation == "Unable to complete."
    statuses = {row["call_id"]: row["status"] for row in result.private.tool_calls}
    assert statuses["unavail"] == "unavailable"


def test_dsp_tool_failure_fail_closed() -> None:
    extra = _tool("dsp.management_quality", "boom", symbol="INFY")
    result = _fail_both(
        [extra, "json"],
        backend=StubBackend(raise_on="management"),
    ).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED
    statuses = {row["call_id"]: row["status"] for row in result.private.tool_calls}
    assert statuses["boom"] == "tool_failed"


def test_provider_unavailable_fail_closed() -> None:
    result = _fail_both(["unavailable"]).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED
    assert result.public.recommendation == "Unable to complete."


def test_provider_malformed_response_fail_closed() -> None:
    result = _fail_both(["malformed"]).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED


def test_malformed_final_json_fail_closed() -> None:
    result = _fail_both(["malformed"]).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED
    assert result.public.recommendation == "Unable to complete."


def test_invalid_airesearch_output_fail_closed() -> None:
    result = _fail_both(["invalid_schema"]).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED


def test_fabricated_evidence_citation_fail_closed() -> None:
    result = _fail_both(["unsupported"]).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED


def test_unsupported_claim_fail_closed() -> None:
    result = _fail_both(["unsupported"]).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED
    dumped = json.dumps(result.public.to_dict())
    assert "fabricated-id" not in dumped


def test_ai_cannot_override_dsp_recommendation() -> None:
    result = _fail_both(["override"]).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED
    assert result.public.recommendation != "Sell"
    assert result.public.recommendation == "Unable to complete."


def test_repeated_identical_tool_call_fail_closed() -> None:
    same = _tool("dsp.risk", "dup-1", symbol="INFY")
    again = _tool("dsp.risk", "dup-2", symbol="INFY")
    result = _fail_both([same, again, "json"]).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED
    assert result.public.recommendation == "Unable to complete."


def test_maximum_iteration_exceeded_fail_closed() -> None:
    first = _tool("dsp.risk", "iter-1", symbol="INFY")
    second = _tool("dsp.economic_moat", "iter-2", symbol="INFY")
    limits = ToolLoopLimits(
        max_iterations=1,
        max_tool_calls=12,
        max_identical=1,
        max_provider_round_trips=8,
    )
    result = _fail_both([first, second, "json"], loop_limits=limits).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED
    assert result.public.recommendation == "Unable to complete."


def test_maximum_tool_call_limit_exceeded_fail_closed() -> None:
    first = _tool("dsp.risk", "lim-1", symbol="INFY")
    second = _tool("dsp.economic_moat", "lim-2", symbol="INFY")
    limits = ToolLoopLimits(
        max_iterations=6,
        max_tool_calls=1,
        max_identical=1,
        max_provider_round_trips=8,
    )
    result = _fail_both([first, second, "json"], loop_limits=limits).run(_request())
    assert result.status is OrchestratorStatus.FAILED_CLOSED


def test_privacy_boundary() -> None:
    result = _orchestrator().run(_request())
    public = result.to_public().to_dict()
    assert_no_private_leakage(public)
    dumped = json.dumps(public)
    assert "routing_tier" not in dumped
    assert "internal_prompt" not in dumped
    assert result.private.chain_of_thought == ""


def test_no_provider_model_cost_leakage() -> None:
    result = _orchestrator().run(_request())
    dumped = json.dumps(result.public.to_dict()).lower()
    for token in (
        "deepseek",
        "anthropic",
        "openai",
        "gemini",
        "gpt-4o",
        "claude",
        "estimated_cost",
        "input_tokens",
        "output_tokens",
        "routing_tier",
    ):
        assert token not in dumped


def test_no_chain_of_thought_leakage() -> None:
    result = _fail_both(["raw_leak"]).run(_request())
    dumped = json.dumps(result.public.to_dict())
    assert "chain_of_thought" not in dumped
    assert result.private.chain_of_thought == ""


def test_deterministic_behavior() -> None:
    extra = _tool("dsp.management_quality", "det-1", symbol="INFY")
    a = _orchestrator(script=[extra, "json"]).run(_request())
    b = _orchestrator(script=[extra, "json"]).run(_request())
    assert a.public == b.public
    assert a.status is OrchestratorStatus.ACCEPTED


def test_no_direct_dsp_engine_imports() -> None:
    violations: list[str] = []
    for path in _ORCH_SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.name.split(".", 1)[0])
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                names.add(node.module.split(".", 1)[0])
        bad = names & _FORBIDDEN_ENGINE_IMPORTS
        if bad:
            violations.append(f"{path.name}: {sorted(bad)}")
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("import") or stripped.startswith("from"):
                assert "DSPPlatformToolAdapter" not in stripped
    assert not violations, violations


def test_public_manifest_contains_only_approved_tools() -> None:
    registry = ToolRegistry.default()
    names = set(registry.names())
    manifest_names = {entry["name"] for entry in registry.public_manifest()}
    assert names == set(DEFAULT_TOOL_NAMES)
    assert manifest_names == set(DEFAULT_TOOL_NAMES)
    for entry in registry.public_manifest():
        assert "provenance" not in entry
        assert "validation_status" not in entry


def test_all_seventeen_existing_tools_remain_available() -> None:
    assert len(DEFAULT_TOOL_NAMES) == 17
    registry = ToolRegistry.default()
    assert len(registry.names()) == 17
    assert tuple(sorted(registry.names())) == tuple(sorted(DEFAULT_TOOL_NAMES))


def test_activation_guard_remains_fail_closed() -> None:
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


def test_adapter_backed_provider_has_no_http() -> None:
    source = inspect.getsource(AdapterProvider)
    assert "httpx" not in source
    assert "api.openai.com" not in source
    assert "api.anthropic.com" not in source


class _ScriptedResearchAdapter(OpenAICompatibleToolCalling):
    provider_id = "openai"
    model_label = "gpt-4o-mini"

    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self._payloads = list(payloads)
        self.posted_tools: list[Any] = []

    def is_configured(self) -> bool:
        return True

    def invoke(self, request: LanguageModelRequest) -> LanguageModelResult:
        result, _ = self.invoke_research(request)
        return result

    def invoke_research(
        self,
        request: LanguageModelRequest,
        *,
        tools: Any = None,
        tool_result_messages: Any = None,
    ) -> tuple[LanguageModelResult, dict[str, Any] | None]:
        del request, tool_result_messages
        self.posted_tools.append(tools)
        data = self._payloads.pop(0)
        text = None
        message = (data.get("choices") or [{}])[0].get("message") or {}
        if message.get("content"):
            text = str(message["content"])
        return (
            LanguageModelResult(
                result_id="r1",
                status=LanguageModelStatus.COMPLETE,
                provenance=("test",),
                narrative_text=text,
                structured_sections=() if text else ("tool_call",),
                model_label=self.model_label,
            ),
            data,
        )


def test_adapter_backed_loop_one_tool_then_json() -> None:
    adapter = _ScriptedResearchAdapter(
        [
            {
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "oa-1",
                                    "type": "function",
                                    "function": {
                                        "name": "dsp_management_quality",
                                        "arguments": '{"symbol":"INFY"}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            },
            {"choices": [{"message": {"content": "PLACEHOLDER_JSON"}}]},
        ]
    )
    provider = AdapterBackedAIProvider(adapter)

    class _CatalogAwareProvider:
        provider_id = provider.provider_id
        model_label = provider.model_label

        def complete(self, **kwargs: Any):
            catalog = kwargs.get("evidence_catalog") or ()
            completion = provider.complete(**kwargs)
            if completion.requested_calls:
                return completion
            return ScriptedProvider("openai", "gpt-4o-mini", ["json"]).complete(
                prompt_parts=kwargs["prompt_parts"],
                evidence_catalog=catalog,
                prior_tool_results=kwargs.get("prior_tool_results", ()),
                tool_manifest=kwargs.get("tool_manifest", ()),
                prior_outcomes=kwargs.get("prior_outcomes", ()),
            )

    orchestrator = ResearchOrchestrator(
        backend=StubBackend(),
        providers={
            ModelTier.COST_EFFICIENT: _CatalogAwareProvider(),
            ModelTier.PREMIUM: ScriptedProvider(
                "anthropic", "claude-3-5-sonnet-20241022", ["json"]
            ),
        },
    )
    result = orchestrator.run(_request())
    assert adapter.posted_tools
    assert adapter.posted_tools[0]
    posted_names = {item["function"]["name"] for item in adapter.posted_tools[0]}
    assert posted_names == {name.replace(".", "_") for name in DEFAULT_TOOL_NAMES}
    assert result.status is OrchestratorStatus.ACCEPTED
    names = {row["tool_name"] for row in result.private.tool_calls}
    assert "dsp.management_quality" in names


def test_openai_invoke_research_attaches_manifest_tools() -> None:
    config = LLMPlatformConfig(
        default_provider="openai",
        openai_api_key="test-key",
        anthropic_api_key=None,
        gemini_api_key=None,
        deepseek_api_key=None,
        openai_model="gpt-4o-mini",
        anthropic_model="claude-3-5-sonnet-20241022",
        gemini_model="gemini-1.5-flash",
        deepseek_model="deepseek-chat",
        request_timeout_seconds=5.0,
        max_retries=0,
    )
    adapter = OpenAIAdapter(config)
    manifest = ToolRegistry.default().public_manifest()
    tools = adapter.tool_declarations(manifest)
    request = LanguageModelRequest(
        request_id="req-loop",
        intent_class=UserIntentType.EXPLAIN_REPORT,
        prompt_parts=("system rules", "user question"),
        context_digest_ids=("Recommendation",),
        provenance=("test",),
    )
    body = {
        "choices": [
            {
                "message": {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "c1",
                            "type": "function",
                            "function": {
                                "name": "dsp_valuation",
                                "arguments": '{"symbol":"INFY"}',
                            },
                        }
                    ],
                }
            }
        ]
    }
    captured: dict[str, Any] = {}

    def _post(*_args: Any, **kwargs: Any) -> MagicMock:
        captured["json"] = kwargs.get("json")
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = body
        return resp

    with patch("llm_adapters.openai_adapter.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.side_effect = _post
        result, raw = adapter.invoke_research(request, tools=tools)
    assert result.status is LanguageModelStatus.COMPLETE
    assert raw is not None
    assert adapter.payload_contains_tool_calls(raw)
    posted = captured["json"]["tools"]
    assert len(posted) == 17
    names = {item["function"]["name"] for item in posted}
    assert names == {name.replace(".", "_") for name in DEFAULT_TOOL_NAMES}
    src = Path(inspect.getsourcefile(OpenAIAdapter) or "").read_text(encoding="utf-8")
    assert "dsp.financial_statements" not in src
    assert "DEFAULT_TOOL_NAMES" not in src
