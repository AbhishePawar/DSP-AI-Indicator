"""STEP 5A — provider-neutral canonical research AI port (no vendor execution)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from dsp_platform.research_assembly.activation import (
    CanonicalProductionAiDecision,
    CanonicalProductionAiState,
    resolve_canonical_production_ai,
)
from dsp_platform.research_assembly.ai_port import (
    BlockedCanonicalResearchAiPort,
    CanonicalAiEvidenceState,
    CanonicalAiPortBlockedError,
    CanonicalAiPortResult,
    CanonicalAiPortState,
    invoke_canonical_research_ai_port,
    resolve_canonical_ai_execution_access,
)
from dsp_platform.research_prompt.methodology import PRIVATE_METHODOLOGY_CANARY
from dsp_platform.research_report.models import PublicResearchReport
from dsp_platform.research_validation.draft import (
    CanonicalAIDraft,
    CanonicalAIDraftError,
    parse_canonical_ai_draft,
)

_SRC = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "dsp_platform"
    / "research_assembly"
    / "ai_port.py"
)


class _SpyEvidenceGate:
    def __init__(self, state: CanonicalAiEvidenceState) -> None:
        self.state = state
        self.calls = 0

    def evaluate(self) -> CanonicalAiEvidenceState:
        self.calls += 1
        return self.state


class _SpyPort:
    """Test-only double. Not a vendor adapter and not a network client."""

    def __init__(
        self,
        *,
        draft: CanonicalAIDraft | None = None,
        result: object = None,
        error: Exception | None = None,
    ) -> None:
        self.draft = draft
        self.result = result
        self.error = error
        self.calls = 0

    def interpret(self, private_prompt: object) -> object:
        self.calls += 1
        if self.error is not None:
            raise self.error
        if self.result is not None:
            return self.result
        return self.draft


def _off() -> CanonicalProductionAiDecision:
    return resolve_canonical_production_ai()


def _forged_on() -> CanonicalProductionAiDecision:
    return CanonicalProductionAiDecision(
        state=CanonicalProductionAiState.OFF,
        activated=True,
    )


def _draft() -> CanonicalAIDraft:
    return parse_canonical_ai_draft(
        {
            "executive_summary": "Interpretation only.",
            "evidence_ids": ["stage:valuation"],
        }
    )


def test_gate_a_off_blocks_without_consulting_evidence_or_port() -> None:
    gate = _SpyEvidenceGate(CanonicalAiEvidenceState.READY)
    port = _SpyPort(draft=_draft())
    access = resolve_canonical_ai_execution_access(gate_a=_off(), evidence_gate=gate)
    assert access.state is CanonicalAiPortState.BLOCKED
    assert access.draft is None
    assert gate.calls == 0
    result = invoke_canonical_research_ai_port(port, object(), access)
    assert result.state is CanonicalAiPortState.BLOCKED
    assert result.draft is None
    assert port.calls == 0


def test_gate_a_on_without_evidence_gate_is_blocked() -> None:
    access = resolve_canonical_ai_execution_access(
        gate_a=_forged_on(),
        evidence_gate=None,
    )
    assert access.state is CanonicalAiPortState.BLOCKED


def test_gate_b_not_ready_blocks_port() -> None:
    gate = _SpyEvidenceGate(CanonicalAiEvidenceState.BLOCKED)
    port = _SpyPort(draft=_draft())
    access = resolve_canonical_ai_execution_access(
        gate_a=_forged_on(),
        evidence_gate=gate,
    )
    assert gate.calls == 1
    assert access.state is CanonicalAiPortState.BLOCKED
    result = invoke_canonical_research_ai_port(port, object(), access)
    assert port.calls == 0
    assert result.draft is None


def test_eligible_access_does_not_imply_production_execution() -> None:
    gate = _SpyEvidenceGate(CanonicalAiEvidenceState.READY)
    access = resolve_canonical_ai_execution_access(
        gate_a=_forged_on(),
        evidence_gate=gate,
    )
    assert access.state is CanonicalAiPortState.ELIGIBLE
    assert access.draft is None
    assert resolve_canonical_production_ai().activated is False


def test_blocked_port_cannot_execute() -> None:
    port = BlockedCanonicalResearchAiPort()
    with pytest.raises(CanonicalAiPortBlockedError, match="blocked") as captured:
        port.interpret(object())
    assert PRIVATE_METHODOLOGY_CANARY not in str(captured.value)


def test_mock_port_returns_canonical_draft_only() -> None:
    """Mock double — not a live vendor call."""
    draft = _draft()
    port = _SpyPort(draft=draft)
    access = CanonicalAiPortResult(
        state=CanonicalAiPortState.ELIGIBLE,
        draft=None,
    )
    result = invoke_canonical_research_ai_port(port, object(), access)
    assert port.calls == 1
    assert result.state is CanonicalAiPortState.EXECUTED
    assert result.draft is draft
    assert isinstance(result.draft, CanonicalAIDraft)
    assert not isinstance(result.draft, PublicResearchReport)


def test_invalid_draft_fails_closed() -> None:
    port = _SpyPort(error=CanonicalAIDraftError("extra keys"))
    access = CanonicalAiPortResult(
        state=CanonicalAiPortState.ELIGIBLE,
        draft=None,
    )
    result = invoke_canonical_research_ai_port(port, object(), access)
    assert result.state is CanonicalAiPortState.BLOCKED
    assert result.draft is None


def test_arbitrary_mapping_is_not_a_draft() -> None:
    port = _SpyPort(result={"executive_summary": "raw"})
    access = CanonicalAiPortResult(
        state=CanonicalAiPortState.ELIGIBLE,
        draft=None,
    )
    result = invoke_canonical_research_ai_port(port, object(), access)
    assert result.state is CanonicalAiPortState.BLOCKED
    assert result.draft is None


def test_port_result_repr_hides_prompt() -> None:
    result = CanonicalAiPortResult(state=CanonicalAiPortState.BLOCKED, draft=None)
    blob = repr(result)
    assert PRIVATE_METHODOLOGY_CANARY not in blob
    assert "instructions" not in blob


def test_ai_port_source_is_vendor_neutral() -> None:
    source = _SRC.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module.split(".", 1)[0])
    assert "llm_adapters" not in imported
    assert "openai" not in imported
    assert "anthropic" not in imported
    assert "httpx" not in imported
    assert "os" not in imported
    assert "copilot" not in imported
    assert "api_platform" not in imported
    for snippet in (
        "openai",
        "anthropic",
        "gemini",
        "deepseek",
        "httpx",
        "getenv",
        "api_key",
        "API_KEY",
        "ResearchOrchestrator",
        "CopilotCompleteService",
        "PublicResearchReport",
        "evaluate_activation",
    ):
        assert snippet not in source, snippet
    assert "CanonicalResearchAiPort" in source
    assert "CanonicalAIDraft" in source
    assert "class CanonicalResearchAiPort" in source


def test_production_gate_a_remains_off() -> None:
    decision = resolve_canonical_production_ai({"explicitly_activated": True})
    assert decision.activated is False
    assert decision.state is CanonicalProductionAiState.OFF


def test_private_prompt_repr_is_redacted() -> None:
    from dsp_platform.research_prompt.models import PrivateResearchPrompt

    prompt = PrivateResearchPrompt(
        schema_version="test",
        methodology_version="test",
        source_pipeline="compose_intelligence",
        canary=PRIVATE_METHODOLOGY_CANARY,
        instructions=f"secret {PRIVATE_METHODOLOGY_CANARY}",
        data_block="data",
        text=f"full {PRIVATE_METHODOLOGY_CANARY}",
    )
    blob = repr(prompt)
    assert blob == "PrivateResearchPrompt(<redacted>)"
    assert PRIVATE_METHODOLOGY_CANARY not in blob
