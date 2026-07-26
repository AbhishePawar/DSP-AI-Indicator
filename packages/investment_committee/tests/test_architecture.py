"""Architecture boundary tests for investment_committee (FEATURE-008)."""

from __future__ import annotations

import ast
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src" / "investment_committee"
_PKG_ROOT = Path(__file__).resolve().parents[1]
_FORBIDDEN = frozenset(
    [
        "ai_committee",
        "api_platform",
        "business_quality",
        "comparison",
        "compliance",
        "contracts",
        "copilot",
        "data_engine",
        "data_ingestion",
        "decision_intelligence",
        "dsp",
        "dsp_platform",
        "economic",
        "financial",
        "fundamental",
        "industry",
        "knowledge_graph",
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
        "workflow",
    ]
)
_EXPECTED_VERSION = "0.1.0"
_EXPECTED_DEPS = [
    "core",
    "valuation",
    "economic_moat",
    "management_quality",
    "financial_strength",
    "earnings_quality",
    "growth_quality",
    "business_quality_aggregator",
    "investment_recommendation",
]


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


class TestInvestmentCommitteeArchitecture:
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
        assert data["project"]["dependencies"] == _EXPECTED_DEPS
        assert data["project"]["version"] == _EXPECTED_VERSION

    def test_public_api_stable(self) -> None:
        import investment_committee as mod

        assert getattr(mod, "__version__") == _EXPECTED_VERSION
        missing = [name for name in mod.__all__ if not hasattr(mod, name)]
        assert missing == [], missing
        assert hasattr(mod, "InvestmentCommitteeEngine")
        assert hasattr(mod, "CommitteeDecision")
        assert hasattr(mod, "ReviewerRole")

    def test_distinct_from_frozen_ai_committee(self) -> None:
        from ai_committee import InvestmentCommittee as FrozenCommittee
        from investment_committee import InvestmentCommitteeEngine as FeatEngine

        assert FeatEngine is not FrozenCommittee
        assert FeatEngine.__module__.startswith("investment_committee")
