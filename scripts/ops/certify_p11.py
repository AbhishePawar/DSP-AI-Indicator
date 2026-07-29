#!/usr/bin/env python3
"""Compatibility wrapper — living offline certification is EPIC-P7.0."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    target = Path(__file__).with_name("certify_p7.py")
    return subprocess.call([sys.executable, str(target)], cwd=str(target.parents[2]))


if __name__ == "__main__":
    raise SystemExit(main())
