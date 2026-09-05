"""Architecture: current-outstanding protocol stays blocked and non-canonical."""

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
    / "current_outstanding_protocol"
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
_AUTH_VALUATION = (
    _REPO
    / "packages"
    / "dsp_platform"
    / "src"
    / "dsp_platform"
    / "composition"
    / "authenticated_valuation.py"
)
_SHARE_COUNTS = (
    _REPO / "packages" / "dsp_platform" / "src" / "dsp_platform" / "share_counts.py"
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
    "openai",
    "anthropic",
    "gemini",
    "perplexity",
    "httpx",
    "cloudbuild.yaml",
    "AI_ENABLED",
    "web_search",
    "serpapi",
    "tavily",
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


class TestCurrentOutstandingProtocolArchitecture:
    def test_no_provider_llm_valuation_recommendation_or_cloud_imports(self) -> None:
        violations: list[str] = []
        for path in _SRC.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            bad = _imported_top_levels(text) & _FORBIDDEN_IMPORTS
            if bad:
                violations.append(f"{path.name}: {sorted(bad)}")
            if path.name == "testing.py":
                continue
            for snippet in _FORBIDDEN_SNIPPETS:
                if snippet in text:
                    violations.append(f"{path.name}: snippet {snippet!r}")
        assert violations == [], violations

    def test_ai_output_cannot_construct_sharecount_snapshot(self) -> None:
        for name in (
            "ai_candidate.py",
            "prompt.py",
            "testing.py",
            "queries.py",
            "web_research.py",
            "gated_discovery.py",
        ):
            text = (_SRC / name).read_text(encoding="utf-8")
            assert "ShareCountSnapshot(" not in text
            assert "accept_current_outstanding_claims" not in text
            assert "accept_share_count_from_validated_evidence" not in text

    def test_only_dsp_promotion_may_accept_snapshots(self) -> None:
        promotion = (_SRC / "promotion.py").read_text(encoding="utf-8")
        assert "accept_current_outstanding_claims" in promotion
        assert "ShareCountSnapshot(" not in promotion
        protocol = (_SRC / "protocol.py").read_text(encoding="utf-8")
        assert "ShareCountSnapshot(" not in protocol
        assert "accept_current_outstanding_claims" not in protocol

    def test_package_init_does_not_export_test_double(self) -> None:
        init = (_SRC / "__init__.py").read_text(encoding="utf-8")
        assert "DeterministicShareCountExtractionAiPort" not in init
        from dsp_platform.current_outstanding_protocol import __all__ as exported

        assert "DeterministicShareCountExtractionAiPort" not in exported
        assert "DeterministicScreenerLikeWebDiscovery" not in exported
        assert "DeterministicShareCountWebResearchAiPort" not in init

    def test_http_pipeline_and_sharecount_do_not_auto_run_protocol(self) -> None:
        pipeline = _PIPELINE.read_text(encoding="utf-8")
        assert "current_outstanding_protocol" not in pipeline
        assert "canonical_research_ai_runtime" not in pipeline
        assert "controlled_document_retrieval" not in pipeline
        auth = _AUTH_VALUATION.read_text(encoding="utf-8")
        assert "current_outstanding_protocol" not in auth
        assert "canonical_research_ai_runtime" not in auth
        assert "controlled_document_retrieval" not in auth
        facade = _SHARE_COUNTS.read_text(encoding="utf-8")
        assert "current_outstanding_protocol" not in facade
        for name in (
            "composition.py",
            "analysis.py",
            "research.py",
            "research_company.py",
            "copilot.py",
        ):
            text = (_API_ROUTERS / name).read_text(encoding="utf-8")
            assert "current_outstanding_protocol" not in text
            assert "controlled_document_retrieval" not in text
            assert "ControlledHttpsDocumentRetrieval" not in text

    def test_no_env_ai_enabled_shortcut(self) -> None:
        for path in _SRC.rglob("*.py"):
            if path.name == "testing.py":
                continue
            text = path.read_text(encoding="utf-8")
            assert "AI_ENABLED" not in text
            assert "os.environ" not in text
            assert "DSP_AI" not in text

    def test_production_factory_uses_blocked_ports(self) -> None:
        text = (_SRC / "protocol.py").read_text(encoding="utf-8")
        assert "ActivationGatedEvidenceDiscovery" in text
        assert "activation_ready=False" in text
        assert "AiAssistedShareCountWebDiscovery" in text
        assert "ProductionBlockedPrimarySourceDocumentRetrieval" in text
        assert "ProductionBlockedCanonicalResearchAiPort" in text
        assert "DeterministicShareCountExtractionAiPort" not in text
        assert "DeterministicScreenerLikeWebDiscovery" not in text
        assert "openai" not in text.lower()
        assert "canonical_research_ai_runtime" not in text
        assert "ProviderBackedCanonicalResearchAiPort" not in text
        assert "GeminiAdapter" not in text
        assert "ControlledHttpsDocumentRetrieval" not in text
        assert "controlled_document_retrieval" not in text

    def test_not_imported_by_llm_upstox_valuation_recommendation(self) -> None:
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
                if "current_outstanding_protocol" in text:
                    offenders.append(path.as_posix())
        assert offenders == []

    def test_frontend_does_not_import_protocol(self) -> None:
        offenders: list[str] = []
        skip_parts = {"node_modules", ".next", "dist", "coverage", ".vite"}
        for root in _FRONTEND_HINTS:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if skip_parts.intersection(path.parts):
                    continue
                if path.suffix.lower() not in {".py", ".ts", ".tsx", ".js"}:
                    continue
                if not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                if "current_outstanding_protocol" in text:
                    offenders.append(path.as_posix())
        assert offenders == []
