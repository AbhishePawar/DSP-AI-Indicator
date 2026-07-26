"""Architecture boundary tests for economic_moat (ASI-003 + FEATURE-001)."""

from __future__ import annotations

import ast
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src" / "economic_moat"
_PKG_ROOT = Path(__file__).resolve().parents[1]
_FORBIDDEN = frozenset(
    [
        "ai_committee",
        "api_platform",
        "comparison",
        "compliance",
        "contracts",
        "copilot",
        "data_engine",
        "data_ingestion",
        "decision_intelligence",
        "earnings_quality",
        "growth_quality",
        "business_quality_aggregator",
        "investment_recommendation",
        "investment_committee",
        "dsp",
        "dsp_platform",
        "economic",
        "fundamental",
        "financial_strength",
        "industry",
        "knowledge_graph",
        "management_quality",
        "orchestration",
        "portfolio",
        "production_platform",
        "quantitative_risk",
        "recommendation",
        "research",
        "risk",
        "security_platform",
        "snapshot_bridge",
        "universe",
        "valuation",
        "workflow",
    ]
)
_EXPECTED_VERSION = "0.2.0"


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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


class TestEconomicMoatArchitecture:
    def test_no_forbidden_imports(self) -> None:
        violations: list[str] = []
        for path in _SRC.rglob("*.py"):
            bad = _imported_top_levels(_read(path)) & _FORBIDDEN
            if bad:
                violations.append(f"{path.relative_to(_SRC)}: {sorted(bad)}")
        assert violations == [], violations

    def test_declared_dependencies(self) -> None:
        import tomllib

        data = tomllib.loads((_PKG_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        assert data["project"]["dependencies"] == [
            "core",
            "financial",
            "business_quality",
        ]
        assert data["project"]["version"] == _EXPECTED_VERSION

    def test_public_api_stable(self) -> None:
        import economic_moat as mod

        assert getattr(mod, "__version__") == _EXPECTED_VERSION
        assert hasattr(mod, "__all__")
        missing = [name for name in mod.__all__ if not hasattr(mod, name)]
        assert missing == [], missing
        assert hasattr(mod, "EconomicEngine")
        assert hasattr(mod, "MoatRating")
        assert hasattr(mod, "MoatDimension")
        assert hasattr(mod, "MoatComponentScore")
