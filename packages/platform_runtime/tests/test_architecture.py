"""Architecture boundaries for platform_runtime (PEP-004.1)."""

from __future__ import annotations

import ast
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src" / "platform_runtime"
_PKG_ROOT = Path(__file__).resolve().parents[1]
_FORBIDDEN = frozenset(
    {
        "ai_committee",
        "api_platform",
        "business_quality",
        "business_quality_aggregator",
        "comparison",
        "copilot",
        "data_engine",
        "decision_intelligence",
        "dsp",
        "dsp_platform",
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
        "quantitative_risk",
        "recommendation",
        "research",
        "risk",
        "snapshot_bridge",
        "universe",
        "valuation",
        "workflow",
    }
)
_EXPECTED_VERSION = "0.1.0"
_ALLOWED_DEPS = ["production-platform", "security-platform", "compliance"]


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


class TestPlatformRuntimeArchitecture:
    def test_no_engine_imports(self) -> None:
        violations: list[str] = []
        for path in _SRC.rglob("*.py"):
            bad = _imported_top_levels(_read(path)) & _FORBIDDEN
            if bad:
                violations.append(f"{path.relative_to(_SRC)}: {sorted(bad)}")
        assert violations == [], violations

    def test_declared_dependencies(self) -> None:
        import tomllib

        data = tomllib.loads((_PKG_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        assert data["project"]["dependencies"] == _ALLOWED_DEPS

    def test_public_api(self) -> None:
        import platform_runtime as mod

        assert mod.__version__ == _EXPECTED_VERSION
        assert hasattr(mod, "EnterprisePlatform")
        missing = [n for n in mod.__all__ if not hasattr(mod, n)]
        assert missing == [], missing
