"""Architecture: ShareCount evidence acceptance stays DSP-owned and explicit."""

from __future__ import annotations

import ast
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_ACCEPTANCE = (
    _REPO
    / "packages"
    / "data_engine"
    / "src"
    / "data_engine"
    / "share_count"
    / "acceptance.py"
)
_MAPPER = (
    _REPO
    / "packages"
    / "dsp_platform"
    / "src"
    / "dsp_platform"
    / "share_count_evidence.py"
)
_ADAPTERS = (
    _REPO
    / "packages"
    / "data_engine"
    / "src"
    / "data_engine"
    / "share_count"
    / "adapters.py"
)
_SHARE_COUNTS_FACADE = (
    _REPO / "packages" / "dsp_platform" / "src" / "dsp_platform" / "share_counts.py"
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
_API_ROUTERS = (
    _REPO
    / "packages"
    / "api_platform"
    / "src"
    / "api_platform"
    / "api"
    / "routers"
)
_AI_PACKAGES = (
    _REPO
    / "packages"
    / "dsp_platform"
    / "src"
    / "dsp_platform"
    / "canonical_research_ai",
    _REPO / "packages" / "dsp_platform" / "src" / "dsp_platform" / "research_prompt",
    _REPO / "packages" / "dsp_platform" / "src" / "dsp_platform" / "research_package",
    _REPO / "packages" / "dsp_platform" / "src" / "dsp_platform" / "research_assembly",
    _REPO / "packages" / "llm_adapters" / "src" / "llm_adapters",
    _REPO / "packages" / "ai_committee" / "src" / "ai_committee",
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
        "gemini",
        "google",
        "httpx",
        "investment_recommendation",
        "llm_adapters",
        "openai",
        "recommendation",
        "requests",
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
    "httpx",
    "cloudbuild.yaml",
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


class TestShareCountEvidenceArchitecture:
    def test_acceptance_does_not_import_llm_web_frontend_or_valuation(self) -> None:
        violations: list[str] = []
        for path in (_ACCEPTANCE, _MAPPER):
            text = path.read_text(encoding="utf-8")
            bad = _imported_top_levels(text) & _FORBIDDEN_IMPORTS
            if bad:
                violations.append(f"{path.name}: {sorted(bad)}")
            for snippet in _FORBIDDEN_SNIPPETS:
                if snippet in text:
                    violations.append(f"{path.name}: snippet {snippet!r}")
        assert violations == [], violations

    def test_acceptance_does_not_import_dsp_platform(self) -> None:
        text = _ACCEPTANCE.read_text(encoding="utf-8")
        assert "dsp_platform" not in text
        assert "canonical_research_ai" not in text
        assert "research_prompt" not in text

    def test_mapper_does_not_construct_sharecount_port(self) -> None:
        text = _MAPPER.read_text(encoding="utf-8")
        imported = _imported_names(text)
        assert "ShareCountPort" not in imported
        assert "build_default_share_count_adapter_from_env" not in text
        assert "NullShareCountAdapter" not in text
        assert "class ShareCountPort" not in text

    def test_ai_packages_cannot_import_acceptance(self) -> None:
        offenders: list[str] = []
        needles = (
            "share_count_evidence",
            "accept_share_count_from_validated_evidence",
            "accept_current_outstanding_claims",
            "data_engine.share_count.acceptance",
        )
        for root in _AI_PACKAGES:
            if not root.exists():
                continue
            for path in root.rglob("*.py"):
                text = path.read_text(encoding="utf-8")
                if any(needle in text for needle in needles):
                    offenders.append(path.as_posix())
        assert offenders == []

    def test_http_and_pipeline_do_not_auto_accept_share_count_evidence(self) -> None:
        pipeline = _PIPELINE.read_text(encoding="utf-8")
        assert "share_count_evidence" not in pipeline
        assert "accept_share_count_from_validated_evidence" not in pipeline
        assert "accept_current_outstanding_claims" not in pipeline
        for name in (
            "composition.py",
            "research.py",
            "research_company.py",
            "copilot.py",
        ):
            text = (_API_ROUTERS / name).read_text(encoding="utf-8")
            assert "share_count_evidence" not in text
            assert "accept_share_count_from_validated_evidence" not in text

    def test_production_adapter_factory_has_no_evidence_fallback(self) -> None:
        text = _ADAPTERS.read_text(encoding="utf-8")
        assert "accept_current_outstanding_claims" not in text
        assert "ValidatedExternalEvidencePackage" not in text
        assert "NullShareCountAdapter" in text
        facade = _SHARE_COUNTS_FACADE.read_text(encoding="utf-8")
        assert "accept_share_count_from_validated_evidence" not in facade
        assert "build_default_share_count_adapter_from_env" in facade

    def test_frontend_does_not_import_acceptance(self) -> None:
        offenders: list[str] = []
        for root in _FRONTEND_HINTS:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if path.suffix.lower() not in {".py", ".ts", ".tsx", ".js"}:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                if "accept_share_count_from_validated_evidence" in text:
                    offenders.append(path.as_posix())
        assert offenders == []
