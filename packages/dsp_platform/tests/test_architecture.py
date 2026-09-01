"""Architecture boundary tests for dsp_platform (ASI-003 + EPIC-001).

Additive verification only — does not redesign the package.
EPIC-001 allowlists FEATURE composition packages for orchestration-only imports.
"""

from __future__ import annotations

import ast
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src" / "dsp_platform"
_PKG_ROOT = Path(__file__).resolve().parents[1]
# Still forbidden: frozen G-era engines, HTTP/security tiers, raw dsp indicator
_FORBIDDEN = frozenset(
    [
        "ai_committee",
        "api_platform",
        "compliance",
        "data_ingestion",
        "dsp",
        "economic",
        "fundamental",
        "production_platform",
        "security_platform",
    ]
)
# ASI-003 additive allowlist — freeze one already-shipping P1-01 composition edge.
# Pair is (posix path relative to dsp_platform src, forbidden top-level package).
# "fundamental" stays forbidden in every other dsp_platform module.
_FORBIDDEN_IMPORT_ALLOWLIST: frozenset[tuple[str, str]] = frozenset(
    {
        ("composition/authenticated_valuation.py", "fundamental"),
    }
)
_EXPECTED_VERSION = "2.0.0"
_EXPECTED_DEPS = [
    "comparison",
    "contracts",
    "copilot",
    "core",
    "data_engine",
    "decision_intelligence",
    "industry",
    "knowledge_graph",
    "orchestration",
    "portfolio",
    "quantitative_risk",
    "recommendation",
    "research",
    "risk",
    "snapshot_bridge",
    "universe",
    "workflow",
    "financial",
    "valuation",
    "business_quality",
    "economic_moat",
    "management_quality",
    "financial_strength",
    "earnings_quality",
    "growth_quality",
    "business_quality_aggregator",
    "investment_recommendation",
    "investment_committee",
    "persistence",
    "auth",
    "admin",
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


class TestDspPlatformArchitecture:
    def test_no_forbidden_imports(self) -> None:
        violations: list[str] = []
        for path in _SRC.rglob("*.py"):
            rel = path.relative_to(_SRC).as_posix()
            imported = _imported_top_levels(_read(path))
            bad = {
                name
                for name in (imported & _FORBIDDEN)
                if (rel, name) not in _FORBIDDEN_IMPORT_ALLOWLIST
            }
            if bad:
                violations.append(f"{rel}: {sorted(bad)}")
        assert violations == [], violations

    def test_authenticated_valuation_fundamental_allowlist_is_narrow(self) -> None:
        """P1-01 may import fundamental.FinancialSnapshot in exactly one file."""
        rel = "composition/authenticated_valuation.py"
        path = _SRC / Path(*rel.split("/"))
        imported = _imported_top_levels(_read(path))
        assert frozenset({(rel, "fundamental")}) == _FORBIDDEN_IMPORT_ALLOWLIST
        assert "fundamental" in imported
        assert (imported & _FORBIDDEN) - {"fundamental"} == frozenset()

    def test_declared_dependencies(self) -> None:
        import tomllib

        data = tomllib.loads((_PKG_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        assert data["project"]["dependencies"] == _EXPECTED_DEPS
        assert data["project"]["version"] == _EXPECTED_VERSION

    def test_public_api_stable(self) -> None:
        import dsp_platform as mod

        assert getattr(mod, "__version__") == _EXPECTED_VERSION
        assert hasattr(mod, "__all__")
        missing = [name for name in mod.__all__ if not hasattr(mod, name)]
        assert missing == [], missing
        assert hasattr(mod, "DSPPlatform")
        assert hasattr(mod, "FORBIDDEN_APPLICATION_PACKAGES")
        assert hasattr(mod, "PlatformOrchestrator")
        assert hasattr(mod, "CompositionRequest")
        assert hasattr(mod, "PipelineResult")
