"""Shared path bootstrap for P7.3 perf scripts."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def bootstrap_monorepo() -> Path:
    packages = ROOT / "packages"
    for src in sorted(packages.glob("*/src")):
        p = str(src)
        if p not in sys.path:
            sys.path.insert(0, p)
    return ROOT
