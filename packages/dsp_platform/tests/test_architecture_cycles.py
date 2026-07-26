"""Monorepo first-party import cycle detection (ASI-003)."""

from __future__ import annotations

import ast
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_INTERNAL = frozenset(
    {
        "ai_committee",
        "api_platform",
        "business_quality",
        "comparison",
        "compliance",
        "contracts",
        "copilot",
        "core",
        "data_engine",
        "decision_intelligence",
        "dsp",
        "dsp_platform",
        "economic",
        "economic_moat",
        "management_quality",
        "financial_strength",
        "earnings_quality",
        "growth_quality",
        "business_quality_aggregator",
        "investment_recommendation",
        "investment_committee",
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
        "valuation",
        "workflow",
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
            if node.level and node.level > 0:
                continue
            names.add(node.module.split(".", 1)[0])
    return frozenset(names)


def _build_graph() -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    for pkg in sorted(_INTERNAL):
        src = _REPO / "packages" / pkg / "src" / pkg
        if not src.is_dir():
            continue
        used: set[str] = set()
        for path in src.rglob("*.py"):
            used |= _imported_top_levels(path.read_text(encoding="utf-8-sig"))
        graph[pkg] = used & _INTERNAL - {pkg}
    return graph


def _find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    white, gray, black = 0, 1, 2
    color = {n: white for n in graph}
    stack: list[str] = []
    cycles: list[list[str]] = []

    def dfs(u: str) -> None:
        color[u] = gray
        stack.append(u)
        for v in graph.get(u, ()):
            if v not in color:
                continue
            if color[v] == gray:
                cycles.append(stack[stack.index(v) :] + [v])
            elif color[v] == white:
                dfs(v)
        stack.pop()
        color[u] = black

    for node in list(graph):
        if color[node] == white:
            dfs(node)
    return cycles


class TestMonorepoArchitectureCycles:
    def test_no_first_party_import_cycles(self) -> None:
        cycles = _find_cycles(_build_graph())
        assert cycles == [], cycles
