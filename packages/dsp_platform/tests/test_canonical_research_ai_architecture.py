"""Architecture: canonical research AI seam stays test-only and blocked."""

from __future__ import annotations

import ast
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_SRC = (
    _REPO
    / "packages"
    / "dsp_platform"
    / "src"
    / "dsp_platform"
    / "canonical_research_ai"
)
_ASSEMBLY = (
    _REPO
    / "packages"
    / "dsp_platform"
    / "src"
    / "dsp_platform"
    / "research_assembly"
)
_API_ROUTERS = (
    _REPO
    / "packages"
    / "api_platform"
    / "src"
    / "api_platform"
    / "api"
    / "routers"
)

_FORBIDDEN_IMPORTS = frozenset(
    {
        "anthropic",
        "api_platform",
        "cloudbuild",
        "deepseek",
        "fmp",
        "gemini",
        "google",
        "httpx",
        "investment_recommendation",
        "llm_adapters",
        "openai",
        "recommendation",
        "requests",
        "upstox",
        "valuation",
        "yahoo",
        "yfinance",
    }
)

_FORBIDDEN_SNIPPETS = (
    "from valuation",
    "import valuation",
    "ValuationEngine",
    "InvestmentRecommendationEngine",
    "ShareCountPort",
    "openai",
    "anthropic",
    "httpx",
    "cloudbuild.yaml",
    "data_engine.providers.upstox",
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


class TestCanonicalResearchAiArchitecture:
    def test_no_provider_engine_or_deploy_imports(self) -> None:
        violations: list[str] = []
        for path in _SRC.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            imported = _imported_top_levels(text)
            bad = imported & _FORBIDDEN_IMPORTS
            if bad:
                violations.append(f"{path.name}: {sorted(bad)}")
            if path.name == "testing.py":
                continue
            for snippet in _FORBIDDEN_SNIPPETS:
                if snippet in text:
                    violations.append(f"{path.name}: snippet {snippet!r}")
        assert violations == [], violations

    def test_production_modules_do_not_import_test_ai(self) -> None:
        offenders: list[str] = []
        roots = (
            _REPO / "packages" / "dsp_platform" / "src" / "dsp_platform",
            _REPO / "packages" / "api_platform" / "src" / "api_platform",
        )
        skip = {"testing.py", "test_canonical_research_ai.py"}
        for root in roots:
            for path in root.rglob("*.py"):
                if path.name in skip:
                    continue
                text = path.read_text(encoding="utf-8")
                if "DeterministicCanonicalResearchAiPort" in text:
                    offenders.append(path.as_posix())
                if "canonical_research_ai.testing" in text:
                    offenders.append(path.as_posix())
        assert offenders == []

    def test_assembler_does_not_call_a_port(self) -> None:
        text = (_ASSEMBLY / "assembler.py").read_text(encoding="utf-8")
        assert "DeterministicCanonicalResearchAiPort" not in text
        assert "ProductionBlockedCanonicalResearchAiPort" not in text
        assert ".interpret(" not in text
        assert "canonical_research_ai.testing" not in text

    def test_http_does_not_depend_on_ai_port(self) -> None:
        for name in (
            "composition.py",
            "research.py",
            "research_company.py",
            "copilot.py",
        ):
            text = (_API_ROUTERS / name).read_text(encoding="utf-8")
            assert "canonical_research_ai" not in text
            assert "DeterministicCanonicalResearchAiPort" not in text

    def test_not_imported_by_llm_upstox_valuation(self) -> None:
        roots = (
            _REPO / "packages" / "llm_adapters" / "src" / "llm_adapters",
            _REPO / "packages" / "data_engine" / "src" / "data_engine",
            _REPO / "packages" / "valuation" / "src" / "valuation",
            _REPO / "packages" / "recommendation" / "src" / "recommendation",
        )
        offenders: list[str] = []
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*.py"):
                text = path.read_text(encoding="utf-8")
                if "dsp_platform.canonical_research_ai" in text:
                    offenders.append(path.as_posix())
        assert offenders == []

    def test_share_count_port_untouched(self) -> None:
        for path in _SRC.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            assert "ShareCountPort" not in text
            assert "get_share_count" not in text
            assert "data_engine.share_count" not in text
