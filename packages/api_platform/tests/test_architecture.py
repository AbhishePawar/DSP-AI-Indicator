"""Architecture boundary tests for api_platform (ASI-003 + EPIC-002).

Additive verification only — does not redesign the package.
"""

from __future__ import annotations

import ast
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src" / "api_platform"
_PKG_ROOT = Path(__file__).resolve().parents[1]
_FORBIDDEN = frozenset(
    [
        "ai_committee",
        "business_quality",
        "business_quality_aggregator",
        "comparison",
        "compliance",
        "copilot",
        "core",
        "data_engine",
        "data_ingestion",
        "decision_intelligence",
        "dsp",
        "earnings_quality",
        "economic",
        "economic_moat",
        "financial",
        "financial_strength",
        "fundamental",
        "growth_quality",
        "industry",
        "investment_committee",
        "investment_recommendation",
        "knowledge_graph",
        "management_quality",
        "orchestration",
        "portfolio",
        "production_platform",
        "quantitative_risk",
        "recommendation",
        "research",
        "risk",
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


class TestApiPlatformArchitecture:
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
            "dsp_platform",
            "contracts",
            "llm_adapters",
            "fastapi>=0.115.0",
            "uvicorn>=0.30.0",
            "httpx>=0.27.0",
        ]

    def test_public_api_stable(self) -> None:
        import api_platform as mod

        assert getattr(mod, "__version__") == _EXPECTED_VERSION
        assert hasattr(mod, "__all__")
        missing = [name for name in mod.__all__ if not hasattr(mod, name)]
        assert missing == [], missing
        assert hasattr(mod, "create_app")
