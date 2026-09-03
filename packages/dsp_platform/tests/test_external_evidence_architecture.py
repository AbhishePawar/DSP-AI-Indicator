"""Architecture: external evidence stays provider-neutral and calculation-neutral."""

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
    / "external_evidence"
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
_FRONTEND_HINTS = (
    _REPO / "apps",
    _REPO / "packages" / "web",
    _REPO / "frontend",
)

_FORBIDDEN_IMPORTS = frozenset(
    {
        "ai_committee",
        "anthropic",
        "api_platform",
        "cloudbuild",
        "data_ingestion",
        "deepseek",
        "dsp",
        "earnings_quality",
        "economic_moat",
        "financial",
        "financial_strength",
        "fmp",
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
    "get_share_count",
    "data_engine.providers.upstox",
    "data_engine.providers.fmp",
    "data_engine.providers.yahoo",
    "llm_adapters",
    "openai",
    "anthropic",
    "analyze_decision_pack(",
    "httpx",
    "cloudbuild.yaml",
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


class TestExternalEvidenceArchitecture:
    def test_no_provider_engine_frontend_or_deploy_imports(self) -> None:
        violations: list[str] = []
        for path in _SRC.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            imported = _imported_top_levels(text)
            bad = imported & _FORBIDDEN_IMPORTS
            if bad:
                violations.append(f"{path.name}: {sorted(bad)}")
            for snippet in _FORBIDDEN_SNIPPETS:
                if snippet in text:
                    violations.append(f"{path.name}: snippet {snippet!r}")
        assert violations == [], violations

    def test_analyse_and_research_http_do_not_depend_on_external_evidence(self) -> None:
        for name in (
            "composition.py",
            "research.py",
            "research_company.py",
            "copilot.py",
        ):
            text = (_API_ROUTERS / name).read_text(encoding="utf-8")
            assert "ValidatedExternalEvidencePackage" not in text
            assert "build_validated_external_evidence_package" not in text
            assert "dsp_platform.external_evidence" not in text

    def test_not_imported_by_llm_adapters_or_upstox(self) -> None:
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
                if "dsp_platform.external_evidence" in text:
                    offenders.append(path.as_posix())
        assert offenders == []

    def test_frontend_trees_do_not_import_evidence_package(self) -> None:
        offenders: list[str] = []
        for root in _FRONTEND_HINTS:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if path.suffix.lower() not in {".py", ".ts", ".tsx", ".js"}:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                if "ValidatedExternalEvidencePackage" in text:
                    offenders.append(path.as_posix())
        assert offenders == []
