"""Architecture boundary tests for the universe package."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src" / "universe"
_FORBIDDEN = frozenset(
    {
        "dsp",
        "fundamental",
        "economic",
        "valuation",
        "data_engine",
        "snapshot_bridge",
        "orchestration",
        "recommendation",
        "ai_committee",
        "dsp_platform",
        "comparison",
        "industry",
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


class TestUniverseArchitecture:
    def test_no_engine_or_committee_imports(self) -> None:
        violations: list[str] = []
        for path in _SRC.rglob("*.py"):
            bad = _imported_top_levels(path.read_text(encoding="utf-8")) & _FORBIDDEN
            if bad:
                violations.append(f"{path.name}: {sorted(bad)}")
        assert violations == []

    def test_dependencies(self) -> None:
        data = tomllib.loads(
            (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
                encoding="utf-8"
            )
        )
        assert data["project"]["dependencies"] == [
            "contracts",
            "core",
            "decision_intelligence",
        ]

    def test_public_api(self) -> None:
        import universe as u

        assert u.InvestmentUniverse is not None
        assert u.MultiStockAnalysisService is not None
        assert u.BatchFailurePolicy.PARTIAL.value == "partial"
        assert callable(u.summarize_decision_pack)
        assert callable(u.filter_entries)
