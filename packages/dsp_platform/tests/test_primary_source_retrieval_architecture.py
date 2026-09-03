"""Architecture: primary-source retrieval stays blocked and independent."""

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
    / "primary_source_retrieval"
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
_PIPELINE = (
    _REPO
    / "packages"
    / "dsp_platform"
    / "src"
    / "dsp_platform"
    / "composition"
    / "pipeline.py"
)
_SHARE_COUNTS = (
    _REPO / "packages" / "dsp_platform" / "src" / "dsp_platform" / "share_counts.py"
)
_SHARE_COUNT_EVIDENCE = (
    _REPO
    / "packages"
    / "dsp_platform"
    / "src"
    / "dsp_platform"
    / "share_count_evidence.py"
)
_FRONTEND_HINTS = (
    _REPO / "apps",
    _REPO / "packages" / "web",
    _REPO / "frontend",
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
    "ShareCountSnapshot",
    "accept_share_count_from_validated_evidence",
    "CanonicalResearchAiPort",
    "openai",
    "anthropic",
    "httpx",
    "cloudbuild.yaml",
    "data_engine.providers.upstox",
    "data_engine.share_count",
    "get_share_count",
    "urllib.request",
    "urlopen",
)


def _imported_names(source: str) -> frozenset[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".", 1)[0])
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.level and node.level > 0:
                continue
            names.add(node.module.split(".", 1)[0])
            names.add(node.module)
            for alias in node.names:
                names.add(alias.name)
    return frozenset(names)


def _imported_top_levels(source: str) -> frozenset[str]:
    return frozenset(name.split(".", 1)[0] for name in _imported_names(source))


class TestPrimarySourceRetrievalArchitecture:
    def test_no_provider_llm_sharecount_valuation_or_cloud_imports(self) -> None:
        violations: list[str] = []
        for path in _SRC.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            bad = _imported_top_levels(text) & _FORBIDDEN_IMPORTS
            if bad:
                violations.append(f"{path.name}: {sorted(bad)}")
            imported = _imported_names(text)
            if "ShareCountPort" in imported or "ShareCountSnapshot" in imported:
                violations.append(f"{path.name}: imported ShareCount types")
            if "CanonicalResearchAiPort" in imported:
                violations.append(f"{path.name}: imported CanonicalResearchAiPort")
            for snippet in _FORBIDDEN_SNIPPETS:
                if snippet in text:
                    violations.append(f"{path.name}: snippet {snippet!r}")
        assert violations == [], violations

    def test_package_init_does_not_export_local_fixture(self) -> None:
        init = (_SRC / "__init__.py").read_text(encoding="utf-8")
        assert "LocalPrimarySourceDocumentRetrieval" not in init
        assert "DeterministicExternalEvidenceDiscovery" not in init
        from dsp_platform.primary_source_retrieval import __all__ as exported

        assert "LocalPrimarySourceDocumentRetrieval" not in exported
        assert "load_local_filing_fixture" not in exported

    def test_production_modules_do_not_import_test_retrieval(self) -> None:
        offenders: list[str] = []
        roots = (
            _REPO / "packages" / "dsp_platform" / "src" / "dsp_platform",
            _REPO / "packages" / "api_platform" / "src" / "api_platform",
        )
        skip = {"testing.py", "test_primary_source_retrieval.py"}
        for root in roots:
            for path in root.rglob("*.py"):
                if path.name in skip:
                    continue
                text = path.read_text(encoding="utf-8")
                if "LocalPrimarySourceDocumentRetrieval" in text:
                    offenders.append(path.as_posix())
                if "primary_source_retrieval.testing" in text:
                    offenders.append(path.as_posix())
        assert offenders == []

    def test_http_pipeline_and_sharecount_do_not_auto_retrieve(self) -> None:
        pipeline = _PIPELINE.read_text(encoding="utf-8")
        assert "primary_source_retrieval" not in pipeline
        facade = _SHARE_COUNTS.read_text(encoding="utf-8")
        assert "primary_source_retrieval" not in facade
        evidence = _SHARE_COUNT_EVIDENCE.read_text(encoding="utf-8")
        assert "primary_source_retrieval" not in evidence
        for name in (
            "composition.py",
            "research.py",
            "research_company.py",
            "copilot.py",
        ):
            text = (_API_ROUTERS / name).read_text(encoding="utf-8")
            assert "primary_source_retrieval" not in text

    def test_no_env_fallback_to_local_corpus(self) -> None:
        for path in _SRC.rglob("*.py"):
            if path.name == "testing.py":
                continue
            text = path.read_text(encoding="utf-8")
            assert "DSP_PRIMARY_SOURCE" not in text
            assert "os.environ" not in text
            assert "build_default" not in text

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
                if "primary_source_retrieval" in text:
                    offenders.append(path.as_posix())
        assert offenders == []

    def test_frontend_does_not_import_retrieval(self) -> None:
        offenders: list[str] = []
        for root in _FRONTEND_HINTS:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if path.suffix.lower() not in {".py", ".ts", ".tsx", ".js"}:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                if "primary_source_retrieval" in text:
                    offenders.append(path.as_posix())
        assert offenders == []
