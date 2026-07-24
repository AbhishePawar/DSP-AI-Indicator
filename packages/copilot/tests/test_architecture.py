"""Architecture boundary tests for copilot domain modules (J1.4 freeze)."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src" / "copilot"
_DOMAIN_FILES = frozenset(
    {
        "models.py",
        "refs.py",
        "enums.py",
        "exceptions.py",
        "validation.py",
        "conversation.py",
        "explanation.py",
        "reporter.py",
        "__init__.py",
    }
)
_FORBIDDEN_IN_DOMAIN = frozenset(
    {
        "dsp",
        "fundamental",
        "economic",
        "valuation",
        "data_engine",
        "snapshot_bridge",
        "orchestration",
        "ai_committee",
        "dsp_platform",
        "decision_intelligence",
        "comparison",
        "universe",
        "contracts",
        "portfolio",
        "risk",
        "research",
        "industry",
        "quantitative_risk",
        "recommendation",
        "workflow",
        "knowledge_graph",
        "openai",
        "anthropic",
        "google",
        "gemini",
    }
)


def _imported_top_levels(source: str) -> frozenset[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.add(node.module.split(".", 1)[0])
    return frozenset(names)


class TestCopilotArchitecture:
    def test_domain_modules_forbid_upstream_imports(self) -> None:
        violations: list[str] = []
        for path in _SRC.rglob("*.py"):
            if path.name not in _DOMAIN_FILES:
                continue
            bad = (
                _imported_top_levels(path.read_text(encoding="utf-8"))
                & _FORBIDDEN_IN_DOMAIN
            )
            if bad:
                violations.append(f"{path.name}: {sorted(bad)}")
        assert violations == []

    def test_dependencies(self) -> None:
        data = tomllib.loads(
            (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
                encoding="utf-8"
            )
        )
        assert data["project"]["dependencies"] == ["core"]
        assert data["project"]["version"] == "0.5.0"

    def test_public_api_includes_full_pipeline(self) -> None:
        import copilot as cp

        assert cp.ConversationEngine is not None
        assert cp.ExplanationEngine is not None
        assert cp.CopilotReporter is not None
        assert cp.ReportFormatter is not None
        assert cp.ResponseFormatter is not None
        assert cp.ResponseMetadataBuilder is not None
        assert cp.CollectionStatistics is not None
        assert cp.ValidationStatusView is not None
        assert cp.ReportingResult is not None
        assert cp.LanguageModelPort is not None
        assert cp.__version__ == "0.5.0"
