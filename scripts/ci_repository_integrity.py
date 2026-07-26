#!/usr/bin/env python3
"""ASI-007 repository integrity checks for CI.

Validates package discovery registration and importability for every
path listed in root pyproject.toml [tool.setuptools.packages.find].
Exits non-zero on failure. No network. No product behaviour.
"""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _registered_src_paths() -> list[str]:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block = re.search(
        r"\[tool\.setuptools\.packages\.find\]\s*where\s*=\s*\[(.*?)\]",
        text,
        re.S,
    )
    if not block:
        raise SystemExit("setuptools.packages.find where= block not found")
    return re.findall(r'"([^"]+)"', block.group(1))


def main() -> int:
    errors: list[str] = []
    paths = _registered_src_paths()
    if "packages/economic_moat/src" not in paths:
        errors.append("economic_moat missing from packages.find")
    if "packages/management_quality/src" not in paths:
        errors.append("management_quality missing from packages.find")
    if "packages/financial_strength/src" not in paths:
        errors.append("financial_strength missing from packages.find")
    if "packages/earnings_quality/src" not in paths:
        errors.append("earnings_quality missing from packages.find")
    if "packages/growth_quality/src" not in paths:
        errors.append("growth_quality missing from packages.find")
    if "packages/business_quality_aggregator/src" not in paths:
        errors.append("business_quality_aggregator missing from packages.find")
    if "packages/investment_recommendation/src" not in paths:
        errors.append("investment_recommendation missing from packages.find")
    if "packages/investment_committee/src" not in paths:
        errors.append("investment_committee missing from packages.find")
    if "packages/data-ingestion/src" in paths:
        errors.append("orphan data-ingestion must not be registered")

    for rel in paths:
        src = ROOT / rel
        if not src.is_dir():
            errors.append(f"missing src path: {rel}")
            continue
        # import name = single package dir under src
        kids = [
            p.name
            for p in src.iterdir()
            if p.is_dir() and (p / "__init__.py").exists()
        ]
        if len(kids) != 1:
            errors.append(f"expected one import package under {rel}, found {kids}")
            continue
        name = kids[0]
        try:
            mod = importlib.import_module(name)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"import failed for {name}: {type(exc).__name__}: {exc}")
            continue
        ver = getattr(mod, "__version__", None)
        if not isinstance(ver, str) or not ver:
            errors.append(f"{name} missing __version__")
        all_names = getattr(mod, "__all__", None)
        if not isinstance(all_names, (list, tuple)):
            errors.append(f"{name} missing __all__")
        elif any(not hasattr(mod, item) for item in all_names):
            missing = [item for item in all_names if not hasattr(mod, item)]
            errors.append(f"{name} __all__ unresolved: {missing}")

    print(f"Registered package paths: {len(paths)}")
    if errors:
        print("INTEGRITY FAIL")
        for err in errors:
            print(f" - {err}")
        return 1
    print("INTEGRITY PASS")
    return 0


if __name__ == "__main__":
    # Ensure package src roots are importable the same way pytest configures.
    for rel in _registered_src_paths():
        sys.path.insert(0, str(ROOT / rel))
    raise SystemExit(main())
