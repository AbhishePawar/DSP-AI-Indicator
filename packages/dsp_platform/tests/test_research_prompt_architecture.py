"""Architecture guards for the private methodology prompt generator."""

from __future__ import annotations

import ast
from pathlib import Path

_PKG = Path(__file__).resolve().parents[1]
_SRC = _PKG / "src" / "dsp_platform" / "research_prompt"
_REPO = Path(__file__).resolve().parents[3]

_FORBIDDEN_IMPORTS = frozenset(
    {
        "ai_committee",
        "anthropic",
        "api_platform",
        "dsp",
        "earnings_quality",
        "economic",
        "economic_moat",
        "financial",
        "financial_strength",
        "fundamental",
        "gemini",
        "google",
        "growth_quality",
        "httpx",
        "investment_committee",
        "investment_recommendation",
        "llm_adapters",
        "management_quality",
        "openai",
        "orchestration",
        "recommendation",
        "requests",
        "urllib",
        "valuation",
    }
)

_FORBIDDEN_SNIPPETS = (
    "from valuation",
    "import valuation",
    "from financial",
    "import financial",
    "ValuationEngine",
    "FinancialEngine",
    "InvestmentRecommendationEngine",
    "analyze_decision_pack(",
    "ResearchOrchestrator",
    "httpx",
    "openai",
)

_FORMULA_SNIPPETS = (
    "fcf_growth",
    "terminal_growth",
    "discount_rate",
    "8.5 + 2",
    "wacc",
    "score / 10",
    "/ 10.0",
    "margin_of_safety =",
)


def _imported_top_levels(source: str) -> frozenset[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.level and node.level > 0:
                continue
            names.add(node.module.split(".", 1)[0])
    return frozenset(names)


def _non_comment_source(path: Path) -> str:
    lines: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("#"):
            continue
        lines.append(line)
    return "\n".join(lines)


class TestResearchPromptArchitecture:
    def test_no_engine_provider_or_http_imports(self) -> None:
        violations: list[str] = []
        for path in _SRC.rglob("*.py"):
            imported = _imported_top_levels(path.read_text(encoding="utf-8"))
            bad = imported & _FORBIDDEN_IMPORTS
            if bad:
                violations.append(f"{path.name}: {sorted(bad)}")
        assert violations == [], violations

    def test_generator_is_mapping_only(self) -> None:
        text = _non_comment_source(_SRC / "generator.py")
        for snippet in _FORBIDDEN_SNIPPETS:
            assert snippet not in text, snippet
        for snippet in _FORMULA_SNIPPETS:
            assert snippet not in text, snippet

    def test_not_wired_to_http_or_orchestrator(self) -> None:
        routers = (
            _REPO
            / "packages"
            / "api_platform"
            / "src"
            / "api_platform"
            / "api"
            / "routers"
        )
        for name in ("composition.py", "research.py", "copilot.py"):
            text = (routers / name).read_text(encoding="utf-8")
            assert "build_private_research_prompt" not in text
            assert "PrivateResearchPrompt" not in text
        orch = (
            _REPO
            / "packages"
            / "llm_adapters"
            / "src"
            / "llm_adapters"
            / "orchestrator"
        )
        for path in orch.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            assert "build_private_research_prompt" not in text
            assert "dsp_platform.research_prompt" not in text
