"""Architecture guards for the canonical research HTTP blocked stub (STEP 4I)."""

from __future__ import annotations

import ast
from pathlib import Path

_PKG = Path(__file__).resolve().parents[1]
_REPO = Path(__file__).resolve().parents[3]
_SRC = _PKG / "src" / "api_platform" / "api"
_ROUTER = _SRC / "routers" / "research_company.py"
_SCHEMAS = _SRC / "research_company_schemas.py"
_COMPOSITION = _SRC / "routers" / "composition.py"
_RESEARCH = _SRC / "routers" / "research.py"
_ANALYSIS = _SRC / "routers" / "analysis.py"

_HTTP_FILES = (_ROUTER, _SCHEMAS)

_FORBIDDEN_IMPORTS = frozenset(
    {
        "anthropic",
        "deepseek",
        "gemini",
        "google",
        "httpx",
        "llm_adapters",
        "openai",
        "decision_intelligence",
        "valuation",
        "financial",
        "investment_recommendation",
        "orchestration",
        "recommendation",
    }
)

_FORBIDDEN_SNIPPETS = (
    "analyze_decision_pack(",
    "ResearchOrchestrator",
    "invoke_research",
    "DecisionPack",
    "PublicDecisionPack",
    "AIResearchOutput",
    "validate_research_output(",
    "assemble_canonical_research",
    "build_research_package",
    "build_private_research_prompt",
    "build_public_research_report",
    "validate_canonical_research",
    "build_test_only_ai_output_fixture",
    "AI_OUTPUT_FIXTURE",
    "dsp_platform.research_prompt",
    "dsp_platform.research_package",
    "dsp_platform.research_assembly",
    "dsp_platform.research_validation",
    "from openai",
    "import openai",
    "from anthropic",
    "import anthropic",
    "OpenAI",
    "Anthropic",
    "genai",
    "InvestmentRecommendationEngine",
    "ValuationEngine",
    "FinancialEngine",
    "GrahamEngine",
    "DiscountedCashFlowEngine",
    "fcf_growth",
    "terminal_growth",
    "discount_rate",
    "8.5 + 2",
    "wacc",
    "score_100 / 10",
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


class TestResearchCompanyHttpArchitecture:
    def test_http_layer_may_import_public_report_contract(self) -> None:
        text = _SCHEMAS.read_text(encoding="utf-8")
        assert "dsp_platform.research_report" in text
        assert "PublicResearchReport" in text
        imported = _imported_top_levels(text)
        assert "dsp_platform" in imported

    def test_does_not_import_provider_sdks(self) -> None:
        violations: list[str] = []
        for path in _HTTP_FILES:
            imported = _imported_top_levels(path.read_text(encoding="utf-8"))
            bad = imported & _FORBIDDEN_IMPORTS
            if bad:
                violations.append(f"{path.name}: {sorted(bad)}")
        assert violations == []

    def test_does_not_import_private_prompt_or_legacy_paths(self) -> None:
        for path in _HTTP_FILES:
            text = _non_comment_source(path)
            for snippet in _FORBIDDEN_SNIPPETS:
                assert snippet not in text, f"{path.name}: {snippet}"

    def test_does_not_invoke_analyze_decision_pack(self) -> None:
        for path in _HTTP_FILES:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if isinstance(func, ast.Attribute):
                    assert func.attr != "analyze_decision_pack", path.name
                if isinstance(func, ast.Name):
                    assert func.id != "analyze_decision_pack", path.name

    def test_does_not_modify_analyse_route(self) -> None:
        text = _COMPOSITION.read_text(encoding="utf-8")
        assert "research_company" not in text
        assert "ResearchCompanyRequest" not in text
        assert "assemble_canonical_research" not in text
        assert "compose_intelligence" in text
        assert '@router.post("/analyse"' in text

    def test_does_not_modify_legacy_research_or_analyze_company(self) -> None:
        research = _RESEARCH.read_text(encoding="utf-8")
        analysis = _ANALYSIS.read_text(encoding="utf-8")
        assert "/research/company" not in research
        assert "ResearchCompanyRequest" not in research
        assert "ResearchCompanyRequest" not in analysis
        assert "analyze_company" in analysis
        assert "/research/object" in research
        assert "/research/report" in research

    def test_permissions_reuse_analyze_company(self) -> None:
        from security_platform.security.middleware import PATH_PERMISSIONS
        from security_platform.security.permissions import Permission

        company = PATH_PERMISSIONS["/api/v1/research/company"]
        assert PATH_PERMISSIONS["/research/company"] is Permission.ANALYZE_COMPANY
        assert company is Permission.ANALYZE_COMPANY
        assert PATH_PERMISSIONS["/api/v1/analyse"] is Permission.ANALYZE_COMPANY

    def test_frontend_untouched(self) -> None:
        web = _REPO / "apps" / "web"
        offenders: list[str] = []
        for path in (*web.rglob("*.ts"), *web.rglob("*.tsx")):
            text = path.read_text(encoding="utf-8")
            if "/research/company" in text or "ResearchCompanyRequest" in text:
                offenders.append(str(path.relative_to(web)))
        assert offenders == []

    def test_does_not_create_a_second_calculation_engine(self) -> None:
        for path in _HTTP_FILES:
            text = _non_comment_source(path)
            assert "class " not in text or "Engine" not in text
            assert "def calculate" not in text
            assert "intrinsic_value =" not in text
