"""Architecture: controlled retrieval stays off the analyse/ShareCount path."""

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
    / "controlled_document_retrieval"
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

_FORBIDDEN_IMPORTS = frozenset(
    {
        "anthropic",
        "api_platform",
        "gemini",
        "httpx",
        "investment_recommendation",
        "llm_adapters",
        "openai",
        "recommendation",
        "requests",
        "upstox",
        "valuation",
    }
)
_FORBIDDEN_SNIPPETS = (
    "ShareCountSnapshot(",
    "accept_current_outstanding_claims",
    "AI_ENABLED",
    "activation_ready=True",
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


class TestControlledDocumentRetrievalArchitecture:
    def test_no_provider_valuation_or_sharecount_authority(self) -> None:
        violations: list[str] = []
        for path in _SRC.rglob("*.py"):
            if path.name == "testing.py":
                continue
            text = path.read_text(encoding="utf-8")
            bad = _imported_top_levels(text) & _FORBIDDEN_IMPORTS
            if bad:
                violations.append(f"{path.name}: {sorted(bad)}")
            for snippet in _FORBIDDEN_SNIPPETS:
                if snippet in text:
                    violations.append(f"{path.name}: snippet {snippet!r}")
        assert violations == [], violations

    def test_package_init_does_not_export_test_double(self) -> None:
        init = (_SRC / "__init__.py").read_text(encoding="utf-8")
        assert "FakeDocumentTransport" not in init
        from dsp_platform.controlled_document_retrieval import __all__ as exported

        assert "FakeDocumentTransport" not in exported

    def test_http_does_not_auto_retrieve(self) -> None:
        assert "controlled_document_retrieval" not in _PIPELINE.read_text(
            encoding="utf-8"
        )
        for name in (
            "composition.py",
            "analysis.py",
            "research.py",
            "research_company.py",
            "copilot.py",
        ):
            text = (_API_ROUTERS / name).read_text(encoding="utf-8")
            assert "controlled_document_retrieval" not in text
            assert "PrimarySourceDocumentRetrievalPort" not in text
            assert "ControlledHttpsDocumentRetrieval" not in text
