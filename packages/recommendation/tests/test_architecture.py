"""Architecture boundary tests for recommendation domain modules."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src" / "recommendation"
_DOMAIN_FILES = frozenset(
    {
        "models.py",
        "refs.py",
        "enums.py",
        "exceptions.py",
        "assembler.py",
        "engine.py",
        "reporter.py",
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


class TestRecommendationArchitecture:
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
        assert data["project"]["version"] == "0.4.0"

    def test_public_api_includes_full_pipeline(self) -> None:
        import recommendation as rec

        assert rec.RecommendationAssembler is not None
        assert rec.RecommendationEngine is not None
        assert rec.RecommendationReporter is not None
        assert rec.ReportingStatus.COMPLETE.value == "complete"
        assert rec.__version__ == "0.4.0"
