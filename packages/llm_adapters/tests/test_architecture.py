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

# Files where a best-effort lazy import is permitted (returns None on
# failure and is never used in production — wiring provides the real
# builder). All other files in this package must not import any DSP
# engine module.
_LAZY_IMPORT_ALLOWLIST: frozenset[str] = frozenset(
    {
        "tools/dsp_platform_adapter.py",
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
            rel = path.relative_to(_SRC).as_posix()
            if rel in _LAZY_IMPORT_ALLOWLIST:
                continue
            imported = _imported_top_levels(path.read_text(encoding="utf-8"))
            bad = imported & _FORBIDDEN
            if bad:
                violations.append(f"{path.name}: {sorted(bad)}")
        assert not violations, violations

    def test_adapter_is_the_only_bridge(self) -> None:
        """DSPPlatformToolAdapter is the only place in llm_adapters that
        is permitted to *call* the canonical DSP platform surface. Other
        modules may import the adapter type for re-export and use, but
        they must not invoke platform methods directly."""
        from pathlib import Path as _P
        allowed = _P("tools") / "dsp_platform_adapter.py"
        offenders: list[str] = []
        for path in _SRC.rglob("*.py"):
            rel = path.relative_to(_SRC)
            if rel == allowed:
                continue
            text = path.read_text(encoding="utf-8")
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                    continue
                # Direct method calls on a platform object are forbidden.
                if "_platform.analyze" in line or "_platform.get_" in line or "_platform.run_" in line:
                    offenders.append(f"{path.name}: {stripped}")
                    break
                if "platform.analyze_decision_pack" in line or "platform.run_institutional_committee" in line:
                    offenders.append(f"{path.name}: {stripped}")
                    break
        assert not offenders, offenders

    def test_tools_subpackage_does_not_import_engines_directly(self) -> None:
        """Beyond the adapter, the tools subpackage must not import any
        DSP engine package directly. Everything goes through the
        adapter or the registry."""
        from pathlib import Path as _P
        # Forbidden import statements (not constants or string literals).
        forbidden_imports: tuple[tuple[str, str], ...] = (
            ("import", "valuation"),
            ("import", "financial"),
            ("import", "economic_moat"),
            ("import", "investment_recommendation"),
            ("import", "investment_committee"),
            ("import", "ai_committee"),
            ("import", "industry"),
            ("import", "recommendation"),
        )
        for path in (_SRC / "tools").rglob("*.py"):
            if path.name == "dsp_platform_adapter.py":
                continue
            text = path.read_text(encoding="utf-8")
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                    continue
                for kw, module in forbidden_imports:
                    # Only flag actual import statements.
                    if (f"{kw} {module}" in stripped or f"{kw} {module}." in stripped):
                        raise AssertionError(
                            f"{path.name} imports DSP engine module {module!r} at: {stripped!r}"
                        )
