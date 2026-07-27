"""Architecture tests for llm_adapters — edge adapters only."""

from __future__ import annotations

import ast
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src" / "llm_adapters"
_FORBIDDEN = frozenset(
    {
        "valuation",
        "financial",
        "investment_recommendation",
        "investment_committee",
        "recommendation",
        "dsp_platform",
        "api_platform",
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


class TestLlmAdaptersArchitecture:
    def test_version_and_public_api(self) -> None:
        import llm_adapters

        assert isinstance(llm_adapters.__version__, str)
        assert llm_adapters.__version__
        assert isinstance(llm_adapters.__all__, (list, tuple))

    def test_no_investment_engine_imports(self) -> None:
        violations: list[str] = []
        for path in _SRC.rglob("*.py"):
            imported = _imported_top_levels(path.read_text(encoding="utf-8"))
            bad = imported & _FORBIDDEN
            if bad:
                violations.append(f"{path.name}: {sorted(bad)}")
        assert not violations, violations
