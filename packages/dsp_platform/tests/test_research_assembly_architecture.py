"""Architecture guards for the in-process canonical research assembler."""

from __future__ import annotations

import ast
from pathlib import Path

_PKG = Path(__file__).resolve().parents[1]
_SRC = _PKG / "src" / "dsp_platform" / "research_assembly"
_REPO = Path(__file__).resolve().parents[3]

_FORBIDDEN_IMPORTS = frozenset(
    {
        "ai_committee",
        "anthropic",
        "api_platform",
        "data_ingestion",
        "deepseek",
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
        "valuation",
    }
)

_FORBIDDEN_SNIPPETS = (
    "from valuation",
    "import valuation",
    "from financial",
    "import financial",
    "InvestmentRecommendationEngine",
    "ValuationEngine",
    "FinancialEngine",
    "GrahamEngine",
    "DiscountedCashFlowEngine",
    "analyze_decision_pack(",
    "ResearchOrchestrator",
    "invoke_research",
    "OpenAI",
    "Anthropic",
    "genai",
    "validate_research_output(",
    "DecisionPack",
    "httpx",
    "Cloud Run",
    "docker",
)

_FORMULA_SNIPPETS = (
    "fcf_growth",
    "terminal_growth",
    "discount_rate",
    "8.5 + 2",
    "wacc",
    "(ivps - price)",
    "(iv_per_share - price)",
    "margin_of_safety =",
    "score_100 / 10",
    " / 10.0",
)


def _imported_top_levels(source: str) -> frozenset[str]:
    tree = ast.parse(source)
    collected: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                collected.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.level and node.level > 0:
                continue
            collected.add(node.module.split(".", 1)[0])
    return frozenset(collected)


def _non_comment_source(path: Path) -> str:
    lines: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        lines.append(line)
    return "\n".join(lines)


class TestResearchAssemblyArchitecture:
    def test_no_engine_or_provider_imports(self) -> None:
        violations: list[str] = []
        for path in _SRC.rglob("*.py"):
            imported = _imported_top_levels(path.read_text(encoding="utf-8"))
            bad = imported & _FORBIDDEN_IMPORTS
            if bad:
                violations.append(f"{path.name}: {sorted(bad)}")
        assert violations == [], violations

    def test_assembler_does_not_import_test_fixture(self) -> None:
        for name in ("assembler.py", "ai_port.py"):
            text = (_SRC / name).read_text(encoding="utf-8")
            assert "research_assembly.testing" not in text
            assert "build_test_only_ai_output_fixture" not in text

    def test_ai_port_is_provider_neutral(self) -> None:
        path = _SRC / "ai_port.py"
        source = path.read_text(encoding="utf-8")
        imported = _imported_top_levels(source)
        assert "llm_adapters" not in imported
        assert "openai" not in imported
        assert "os" not in imported
        assert "copilot" not in imported
        assert "httpx" not in imported
        text = _non_comment_source(path)
        assert "CanonicalResearchAiPort" in text
        assert "resolve_canonical_ai_execution_access" in text
        assert "invoke_canonical_research_ai_port" in text
        assert "CanonicalAIDraft" in text
        for snippet in _FORBIDDEN_SNIPPETS:
            assert snippet not in text, snippet
        for snippet in _FORMULA_SNIPPETS:
            assert snippet not in text, snippet

    def test_assembler_is_orchestration_only(self) -> None:
        text = _non_comment_source(_SRC / "assembler.py")
        for snippet in _FORBIDDEN_SNIPPETS:
            assert snippet not in text, snippet
        for snippet in _FORMULA_SNIPPETS:
            assert snippet not in text, snippet

    def test_no_analyze_decision_pack_call(self) -> None:
        for path in _SRC.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if isinstance(func, ast.Attribute):
                    assert func.attr != "analyze_decision_pack", path.name
                if isinstance(func, ast.Name):
                    assert func.id != "analyze_decision_pack", path.name

    def test_not_wired_to_analyse_http(self) -> None:
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
            path = routers / name
            text = path.read_text(encoding="utf-8")
            assert "assemble_canonical_research" not in text
            assert "CanonicalResearchAssembly" not in text
            assert "dsp_platform.research_assembly" not in text

    def test_not_imported_by_llm_adapters(self) -> None:
        adapters_src = _REPO / "packages" / "llm_adapters" / "src" / "llm_adapters"
        offenders: list[str] = []
        for path in adapters_src.rglob("*.py"):
            imported = _imported_top_levels(path.read_text(encoding="utf-8"))
            rel = path.relative_to(adapters_src).as_posix()
            if "dsp_platform" in imported and rel != "tools/dsp_platform_adapter.py":
                offenders.append(rel)
            text = path.read_text(encoding="utf-8")
            if "assemble_canonical_research" in text:
                offenders.append(rel)
        assert offenders == []

    def test_frontend_untouched(self) -> None:
        web = _REPO / "apps" / "web"
        offenders: list[str] = []
        for path in (*web.rglob("*.ts"), *web.rglob("*.tsx")):
            text = path.read_text(encoding="utf-8")
            if "assemble_canonical_research" in text:
                offenders.append(str(path))
        assert offenders == []
