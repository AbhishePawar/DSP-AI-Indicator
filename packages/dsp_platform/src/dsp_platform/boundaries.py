"""Application import-boundary contracts.

External applications must depend only on ``dsp_platform`` and
``contracts``. Internal packages remain an implementation detail of the
composition root.
"""

from __future__ import annotations

import ast
from pathlib import Path

from dsp_platform.exceptions import PlatformError

__all__ = [
    "ALLOWED_APPLICATION_PACKAGES",
    "FORBIDDEN_APPLICATION_PACKAGES",
    "PLATFORM_PACKAGES",
    "assert_application_imports",
    "assert_public_sibling_imports",
    "scan_cross_package_deep_imports",
    "scan_module_imports",
]

ALLOWED_APPLICATION_PACKAGES: frozenset[str] = frozenset(
    {
        "dsp_platform",
        "contracts",
    }
)

FORBIDDEN_APPLICATION_PACKAGES: frozenset[str] = frozenset(
    {
        "data_engine",
        "snapshot_bridge",
        "dsp",
        "fundamental",
        "economic",
        "valuation",
        "financial",
        "business_quality",
        "economic_moat",
        "management_quality",
        "financial_strength",
        "earnings_quality",
        "growth_quality",
        "business_quality_aggregator",
        "investment_recommendation",
        "investment_committee",
        "ai_committee",
        "orchestration",
        "recommendation",
        "decision_intelligence",
        "universe",
        "industry",
        "comparison",
        "portfolio",
        "risk",
        "research",
        "quantitative_risk",
        "workflow",
        "knowledge_graph",
        "copilot",
        "llm_adapters",
        "compliance",
        "core",
        "api_platform",
        "security_platform",
        "production_platform",
    }
)

#: Packages that participate in the Clean Architecture stack and must
#: import sibling packages only through their public ``__init__`` façade.
PLATFORM_PACKAGES: frozenset[str] = frozenset(
    {
        "contracts",
        "core",
        "data_engine",
        "snapshot_bridge",
        "dsp",
        "fundamental",
        "economic",
        "valuation",
        "financial",
        "business_quality",
        "economic_moat",
        "management_quality",
        "financial_strength",
        "earnings_quality",
        "growth_quality",
        "business_quality_aggregator",
        "investment_recommendation",
        "investment_committee",
        "ai_committee",
        "orchestration",
        "recommendation",
        "decision_intelligence",
        "universe",
        "industry",
        "comparison",
        "portfolio",
        "risk",
        "research",
        "quantitative_risk",
        "workflow",
        "knowledge_graph",
        "copilot",
        "llm_adapters",
        "compliance",
        "dsp_platform",
        "api_platform",
        "security_platform",
        "production_platform",
    }
)

#: Shared-kernel submodule prefixes still accepted as public surface.
#: Prefer top-level ``from contracts import …`` / ``from core import …``;
#: these prefixes remain allowed to avoid a bulk mechanical rewrite.
_ALLOWED_SHARED_KERNEL_PREFIXES: frozenset[str] = frozenset(
    {
        "contracts.domain",
        "contracts.enums",
        "contracts.exceptions",
        "core.exceptions",
        "core.registry",
        "core.validation",
        "core.types",
        # LanguageModelPort types — edge adapters implement the port contract
        "copilot.enums",
        "copilot.models",
    }
)


def scan_module_imports(source: str) -> frozenset[str]:
    """Return top-level package names imported by ``source``.

    Args:
        source: Python source text.

    Returns:
        Top-level package names referenced by ``import`` / ``from``.
    """
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            names.add(node.module.split(".", 1)[0])
    return frozenset(names)


def assert_application_imports(
    source: str,
    *,
    path: str | Path | None = None,
) -> frozenset[str]:
    """Assert application source only imports allowed packages.

    Args:
        source: Python source text of an application module.
        path: Optional path used in error messages.

    Returns:
        The set of top-level packages imported.

    Raises:
        PlatformError: If a forbidden internal package is imported.
    """
    imported = scan_module_imports(source)
    forbidden = imported & FORBIDDEN_APPLICATION_PACKAGES
    if forbidden:
        location = f" in {path}" if path is not None else ""
        msg = (
            f"application import boundary violated{location}: "
            f"forbidden packages {sorted(forbidden)}; "
            f"applications may import only {sorted(ALLOWED_APPLICATION_PACKAGES)}"
        )
        raise PlatformError(msg)
    return imported


def scan_cross_package_deep_imports(
    source: str,
    *,
    current_package: str,
) -> frozenset[str]:
    """Return sibling-package deep imports (non-façade) in ``source``.

    A deep import is ``from pkg.sub… import …`` or ``import pkg.sub…``
    where ``pkg`` is another platform package. Same-package internals and
    shared-kernel submodule prefixes are excluded.

    Args:
        source: Python source text.
        current_package: Top-level package that owns the module.

    Returns:
        Fully-qualified module prefixes that violate façade parity.
    """
    tree = ast.parse(source)
    violations: set[str] = set()
    for node in ast.walk(tree):
        modules: list[str] = []
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.append(node.module)
        for module in modules:
            top, _, rest = module.partition(".")
            if not rest:
                continue
            if top == current_package:
                continue
            if top not in PLATFORM_PACKAGES:
                continue
            if any(
                module == prefix or module.startswith(f"{prefix}.")
                for prefix in _ALLOWED_SHARED_KERNEL_PREFIXES
            ):
                continue
            violations.add(module)
    return frozenset(violations)


def assert_public_sibling_imports(
    source: str,
    *,
    current_package: str,
    path: str | Path | None = None,
) -> None:
    """Assert a module imports sibling packages only via public façades.

    Raises:
        PlatformError: If a deep cross-package import is present.
    """
    violations = scan_cross_package_deep_imports(
        source, current_package=current_package
    )
    if violations:
        location = f" in {path}" if path is not None else ""
        msg = (
            f"package façade boundary violated{location}: "
            f"deep sibling imports {sorted(violations)}; "
            f"import sibling packages from their public __init__ only"
        )
        raise PlatformError(msg)
