"""Architecture tests for llm_adapters — edge adapters only."""

from __future__ import annotations

import ast
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src" / "llm_adapters"
_FORBIDDEN = frozenset(
    {
        "valuation",
        "financial",
        "investment_recommendation",
        "investment_committee",
        "recommendation",
        "dsp_platform",
        "api_platform",
    }
)

# Files where a best-effort lazy import is permitted (returns None on
# failure and is never used in production — wiring provides the real
# builder). All other files in this package must not import any DSP
# engine module.
_LAZY_IMPORT_ALLOWLIST: frozenset[str] = frozenset(
    {
        "tools/dsp_platform_adapter.py",
    }
)


def _imported_top_levels(source: str) -> frozenset[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.add(node.module.split(".", 1)[0])
    return frozenset(names)


class TestLlmAdaptersArchitecture:
    def test_version_and_public_api(self) -> None:
        import llm_adapters

        assert isinstance(llm_adapters.__version__, str)
        assert llm_adapters.__version__
        assert isinstance(llm_adapters.__all__, (list, tuple))

    def test_no_investment_engine_imports(self) -> None:
        violations: list[str] = []
        for path in _SRC.rglob("*.py"):
            rel = path.relative_to(_SRC).as_posix()
            if rel in _LAZY_IMPORT_ALLOWLIST:
                continue
            imported = _imported_top_levels(path.read_text(encoding="utf-8"))
            bad = imported & _FORBIDDEN
            if bad:
                violations.append(f"{path.name}: {sorted(bad)}")
        assert not violations, violations

    def test_adapter_is_the_only_bridge(self) -> None:
        """DSPPlatformToolAdapter is the only place in llm_adapters that
        is permitted to *call* the canonical DSP platform surface. Other
        modules may import the adapter type for re-export and use, but
        they must not invoke platform methods directly."""
        from pathlib import Path as _P
        allowed = _P("tools") / "dsp_platform_adapter.py"
        offenders: list[str] = []
        for path in _SRC.rglob("*.py"):
            rel = path.relative_to(_SRC)
            if rel == allowed:
                continue
            text = path.read_text(encoding="utf-8")
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                    continue
                # Direct method calls on a platform object are forbidden.
                if "_platform.analyze" in line or "_platform.get_" in line or "_platform.run_" in line:
                    offenders.append(f"{path.name}: {stripped}")
                    break
                if "platform.analyze_decision_pack" in line or "platform.run_institutional_committee" in line:
                    offenders.append(f"{path.name}: {stripped}")
                    break
        assert not offenders, offenders

    def test_tools_subpackage_does_not_import_engines_directly(self) -> None:
        """Beyond the adapter, the tools subpackage must not import any
        DSP engine package directly. Everything goes through the
        adapter or the registry."""
        from pathlib import Path as _P
        # Forbidden import statements (not constants or string literals).
        forbidden_imports: tuple[tuple[str, str], ...] = (
            ("import", "valuation"),
            ("import", "financial"),
            ("import", "economic_moat"),
            ("import", "investment_recommendation"),
            ("import", "investment_committee"),
            ("import", "ai_committee"),
            ("import", "industry"),
            ("import", "recommendation"),
        )
        for path in (_SRC / "tools").rglob("*.py"):
            if path.name == "dsp_platform_adapter.py":
                continue
            text = path.read_text(encoding="utf-8")
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                    continue
                for kw, module in forbidden_imports:
                    # Only flag actual import statements.
                    if (f"{kw} {module}" in stripped or f"{kw} {module}." in stripped):
                        raise AssertionError(
                            f"{path.name} imports DSP engine module {module!r} at: {stripped!r}"
                        )

    def test_protocol_adapters_cannot_import_dsp_engines(self) -> None:
        """Provider protocol adapters must stay isolated from DSP engines."""
        protocol_dir = _SRC / "tools" / "protocol"
        assert protocol_dir.is_dir()
        forbidden = _FORBIDDEN | {
            "economic_moat",
            "ai_committee",
            "industry",
            "dsp",
            "httpx",
            "openai",
            "anthropic",
            "google",
            "google.generativeai",
        }
        violations: list[str] = []
        for path in protocol_dir.rglob("*.py"):
            imported = _imported_top_levels(path.read_text(encoding="utf-8"))
            bad = imported & forbidden
            if bad:
                violations.append(f"{path.name}: {sorted(bad)}")
        assert not violations, violations

    def test_protocol_adapters_do_not_import_platform_adapter(self) -> None:
        """Protocol adapters talk to ToolRegistry only, never the platform adapter."""
        protocol_dir = _SRC / "tools" / "protocol"
        offenders: list[str] = []
        for path in protocol_dir.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if "DSPPlatformToolAdapter" in stripped and (
                    stripped.startswith("import") or stripped.startswith("from")
                ):
                    offenders.append(f"{path.name}: {stripped}")
        assert not offenders, offenders

    def test_provider_adapters_do_not_import_dsp_engines(self) -> None:
        """OpenAI, DeepSeek, Gemini, Anthropic adapters must not import engines."""
        adapter_files = (
            "openai_adapter.py",
            "deepseek_adapter.py",
            "gemini_adapter.py",
            "anthropic_adapter.py",
        )
        violations: list[str] = []
        for name in adapter_files:
            path = _SRC / name
            imported = _imported_top_levels(path.read_text(encoding="utf-8"))
            bad = imported & (_FORBIDDEN | {"economic_moat", "dsp"})
            if bad:
                violations.append(f"{name}: {sorted(bad)}")
        assert not violations, violations

    def test_openai_and_deepseek_share_compatible_protocol_layer(self) -> None:
        """DeepSeek and OpenAI must share one function-calling implementation."""
        from llm_adapters.anthropic_adapter import AnthropicAdapter
        from llm_adapters.deepseek_adapter import DeepSeekAdapter
        from llm_adapters.gemini_adapter import GeminiAdapter
        from llm_adapters.openai_adapter import OpenAIAdapter
        from llm_adapters.tools.protocol.openai_compatible import (
            OpenAICompatibleToolCalling,
            declarations_as_openai_tools,
            parse_openai_tool_calls,
        )

        assert issubclass(OpenAIAdapter, OpenAICompatibleToolCalling)
        assert issubclass(DeepSeekAdapter, OpenAICompatibleToolCalling)
        assert not issubclass(GeminiAdapter, OpenAICompatibleToolCalling)
        assert not issubclass(AnthropicAdapter, OpenAICompatibleToolCalling)
        assert OpenAIAdapter.parse_tool_calls is OpenAICompatibleToolCalling.parse_tool_calls
        assert DeepSeekAdapter.parse_tool_calls is OpenAICompatibleToolCalling.parse_tool_calls
        assert OpenAIAdapter.parse_tool_calls is DeepSeekAdapter.parse_tool_calls
        assert OpenAIAdapter.tool_declarations is DeepSeekAdapter.tool_declarations
        assert OpenAIAdapter.format_tool_results is DeepSeekAdapter.format_tool_results

        openai_src = (_SRC / "openai_adapter.py").read_text(encoding="utf-8")
        deepseek_src = (_SRC / "deepseek_adapter.py").read_text(encoding="utf-8")
        for src, label in ((openai_src, "openai_adapter"), (deepseek_src, "deepseek_adapter")):
            assert "def declarations_as_openai_tools" not in src, label
            assert "def parse_openai_tool_calls" not in src, label
            assert "OpenAICompatibleToolCalling" in src, label
        assert declarations_as_openai_tools is not parse_openai_tool_calls
