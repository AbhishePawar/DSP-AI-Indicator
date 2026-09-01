"""Architecture guards for the public research report contract."""

from __future__ import annotations

import ast
from pathlib import Path

_PKG = Path(__file__).resolve().parents[1]
_SRC = _PKG / "src" / "dsp_platform" / "research_report"
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
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        lines.append(line)
    return "\n".join(lines)


class TestResearchReportArchitecture:
    def test_no_engine_or_provider_imports(self) -> None:
        violations: list[str] = []
        for path in _SRC.rglob("*.py"):
            imported = _imported_top_levels(path.read_text(encoding="utf-8"))
            bad = imported & _FORBIDDEN_IMPORTS
            if bad:
                violations.append(f"{path.name}: {sorted(bad)}")
        assert violations == [], violations

    def test_builder_is_mapping_only(self) -> None:
        builder = _SRC / "builder.py"
        text = _non_comment_source(builder)
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

    def test_not_wired_to_analyse_or_research_http(self) -> None:
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
            assert "PublicResearchReport" not in text
            assert "build_public_research_report" not in text
            assert "dsp_platform.research_report" not in text
            assert "dsp.public_research_report" not in text

    def test_not_imported_by_llm_adapters(self) -> None:
        adapters_src = _REPO / "packages" / "llm_adapters" / "src" / "llm_adapters"
        offenders: list[str] = []
        for path in adapters_src.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if (
                "dsp_platform.research_report" in text
                or "build_public_research_report" in text
                or "PublicResearchReport" in text
            ):
                offenders.append(path.as_posix())
        assert offenders == []

    def test_frontend_untouched(self) -> None:
        web = _REPO / "apps" / "web"
        offenders: list[str] = []
        for path in web.rglob("*.ts"):
            text = path.read_text(encoding="utf-8")
            if "PublicResearchReport" in text or "dsp.public_research_report" in text:
                offenders.append(str(path))
        for path in web.rglob("*.tsx"):
            text = path.read_text(encoding="utf-8")
            if "PublicResearchReport" in text or "dsp.public_research_report" in text:
                offenders.append(str(path))
        assert offenders == []
