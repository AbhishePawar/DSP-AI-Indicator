#!/usr/bin/env python3
"""Fail if the git-tracked tree has an active Upstox runtime/config dependency.

Mentions that *forbid* Upstox (retired, not in, scanner self-tests) are
HISTORICAL_REFERENCE / COMMENT, not ACTIVE_DEPENDENCY.

Git history is not scanned. Target: ACTIVE_UPSTOX_REFERENCES = 0.

Usage:
  python scripts/ops/assert_no_upstox_dependency.py
  python scripts/ops/assert_no_upstox_dependency.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_SELF = frozenset(
    {
        "scripts/ops/assert_no_upstox_dependency.py",
        "tests/test_no_upstox_dependency.py",
    }
)

_ACTIVE_LINE_RE = re.compile(
    r"(?:"
    r"api\.upstox\.com"
    r"|upstox\.com/v2"
    r"|data_engine\.upstox_"
    r"|from data_engine\.upstox"
    r"|UpstoxQuoteAdapter"
    r"|UpstoxStatementAdapter"
    r"|UpstoxInstrument"
    r"|UpstoxFundamentals"
    r"|UpstoxHistorical"
    r"|UpstoxConnectivity"
    r"|DSP_UPSTOX_[A-Z0-9_]*\s*="
    r"|dsp-upstox-analytics-token"
    r"|DSP_INVESTMENT_DATA_PROVIDER\s*=\s*upstox"
    r")",
    re.IGNORECASE,
)

_TOKEN_RE = re.compile(r"upstox", re.IGNORECASE)

_FORBID_HINTS = (
    "not in",
    "is retired",
    "retired",
    "must not",
    "do not",
    "does not",
    "forbidden",
    "never",
    "no longer",
    "removed",
    "simple-14g",
    "delenv",
    "raising=false",
    "no upstox",
    "zero-upstox",
    "without upstox",
    "does not import",
    "do not import",
)

_BINARY_SUFFIXES = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".ico",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".pdf",
        ".zip",
        ".gz",
        ".pyc",
        ".wasm",
    }
)


@dataclass(frozen=True)
class Hit:
    path: str
    classification: str
    active: bool
    detail: str


def _git_tracked_files() -> list[str]:
    tracked = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    others = subprocess.run(
        ["git", "ls-files", "-z", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    names = set()
    for blob in (tracked.stdout, others.stdout):
        names.update(p for p in blob.decode("utf-8", "replace").split("\0") if p)
    return sorted(names)


def _posix(path: str) -> str:
    return path.replace("\\", "/")


def _is_generated(posix: str) -> bool:
    return any(
        part == ".next" or part.startswith(".next-") or part == "node_modules"
        for part in posix.split("/")
    )


def _forbid_context(line: str) -> bool:
    lowered = line.lower()
    return any(hint in lowered for hint in _FORBID_HINTS)


def _read_text(path: Path) -> str | None:
    if path.suffix.lower() in _BINARY_SUFFIXES:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def classify_tree() -> list[Hit]:
    hits: list[Hit] = []
    for rel in _git_tracked_files():
        posix = _posix(rel)
        disk = ROOT / rel
        if not disk.exists():
            continue
        if posix in _SELF or _is_generated(posix):
            continue
        name = Path(posix).name.lower()
        if name.startswith("upstox") or "upstox_" in name:
            # Tests that exist only to delete Upstox are active until removed.
            kind = "ADAPTER" if "/src/" in f"/{posix}/" else "TEST"
            hits.append(
                Hit(
                    path=posix,
                    classification=kind,
                    active=True,
                    detail="filename contains upstox",
                )
            )
            continue

        body = _read_text(ROOT / rel)
        if body is None:
            continue
        if not _TOKEN_RE.search(body):
            continue
        for lineno, line in enumerate(body.splitlines(), start=1):
            if not _TOKEN_RE.search(line):
                continue
            if _ACTIVE_LINE_RE.search(line) and not _forbid_context(line):
                hits.append(
                    Hit(
                        path=f"{posix}:{lineno}",
                        classification="ACTIVE_DEPENDENCY",
                        active=True,
                        detail=line.strip()[:200],
                    )
                )
                continue
            kind = (
                "DOCUMENTATION"
                if posix.startswith("docs/")
                else "HISTORICAL_REFERENCE" if _forbid_context(line) else "COMMENT"
            )
            hits.append(
                Hit(
                    path=f"{posix}:{lineno}",
                    classification=kind,
                    active=False,
                    detail=line.strip()[:200],
                )
            )
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    hits = classify_tree()
    active = [h for h in hits if h.active]
    report = {
        "ACTIVE_DEPENDENCY": len(active),
        "ACTIVE_UPSTOX_REFERENCES": len(active),
        "DOCUMENTATION": sum(1 for h in hits if h.classification == "DOCUMENTATION"),
        "HISTORICAL_REFERENCE": sum(
            1 for h in hits if h.classification == "HISTORICAL_REFERENCE"
        ),
        "COMMENT": sum(1 for h in hits if h.classification == "COMMENT"),
        "hits": [asdict(h) for h in hits],
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"ACTIVE_DEPENDENCY={report['ACTIVE_DEPENDENCY']}")
        print(f"ACTIVE_UPSTOX_REFERENCES={report['ACTIVE_UPSTOX_REFERENCES']}")
        print(f"DOCUMENTATION={report['DOCUMENTATION']}")
        print(f"HISTORICAL_REFERENCE={report['HISTORICAL_REFERENCE']}")
        print(f"COMMENT={report['COMMENT']}")
        if active:
            print("ACTIVE hits:")
            for hit in active:
                print(f"  {hit.path}: {hit.detail}")
        else:
            print("No active Upstox dependency in the git tree.")

    return 1 if active else 0


if __name__ == "__main__":
    sys.exit(main())
