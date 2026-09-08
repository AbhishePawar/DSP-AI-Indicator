#!/usr/bin/env python3
"""Fail if the git-tracked tree has an active Vercel hosting/deploy dependency.

Next.js is still allowed. GitHub URLs under github.com/vercel/{next.js,ms,styled-jsx}
are package provenance (SBOM / lockfile metadata), not Vercel hosting.

Usage:
  python scripts/ops/assert_no_vercel_hosting.py
  python scripts/ops/assert_no_vercel_hosting.py --json
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

# Files that mention retired hosting in order to forbid it.
_SELF = frozenset(
    {
        "scripts/ops/assert_no_vercel_hosting.py",
        "tests/test_no_vercel_hosting.py",
    }
)

# Next.js / styled-jsx / ms live in the Vercel GitHub org. Not a deploy target.
_ALLOWED_GITHUB_ORG_RE = re.compile(
    r"https?://github\.com/vercel/(?:next\.js|ms|styled-jsx)"
    r"(?:\.git)?(?:[/#?][^\s\"']*)?",
    re.IGNORECASE,
)
_ALLOWED_GIT_GITHUB_ORG_RE = re.compile(
    r"git\+https://github\.com/vercel/(?:next\.js|ms|styled-jsx)"
    r"(?:\.git)?(?:[/#?][^\s\"']*)?",
    re.IGNORECASE,
)

_ACTIVE_LINE_RE = re.compile(
    r"(?:"
    r"vercel\.app"
    r"|vercel\.com"
    r"|@vercel/"
    r"|VERCEL_TOKEN"
    r"|VERCEL_ORG_ID"
    r"|VERCEL_PROJECT_ID"
    r"|VERCEL_URL"
    r"|VERCEL_ENV"
    r"|NEXT_PUBLIC_VERCEL"
    r"|process\.env\.VERCEL"
    r"|amondnet/vercel-action"
    r"|vercel/action"
    r'|["\']vercel["\']\s*:'
    r")",
    re.IGNORECASE,
)

# Residual token after allowlists are stripped. Used for DOCUMENTATION vs ACTIVE.
_TOKEN_RE = re.compile(r"vercel", re.IGNORECASE)

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
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    return [p for p in proc.stdout.decode("utf-8", "replace").split("\0") if p]


def _posix(path: str) -> str:
    return path.replace("\\", "/")


def _is_generated_next_output(posix: str) -> bool:
    """Next build trees mention @vercel/turbopack internally. Not hosting."""
    return any(
        part == ".next" or part.startswith(".next-") or part == "node_modules"
        for part in posix.split("/")
    )


def _is_gitignore_vercel_ignore(path: str, line: str) -> bool:
    if _posix(path) != ".gitignore":
        return False
    stripped = line.strip()
    return stripped in {".vercel", ".vercel/", "**/.vercel/", "**/.vercel"}


def _strip_allowed(text: str) -> str:
    text = _ALLOWED_GIT_GITHUB_ORG_RE.sub("", text)
    return _ALLOWED_GITHUB_ORG_RE.sub("", text)


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
        if posix in _SELF or _is_generated_next_output(posix):
            continue
        name = Path(posix).name.lower()
        if (
            name == "vercel.json"
            or posix == "vercel.json"
            or "/.vercel/" in f"/{posix}"
        ):
            hits.append(
                Hit(
                    path=posix,
                    classification="DEPLOYMENT",
                    active=True,
                    detail="Vercel project file or .vercel directory",
                )
            )
            continue
        if "vercel" in name:
            hits.append(
                Hit(
                    path=posix,
                    classification="DEPLOYMENT",
                    active=True,
                    detail="filename contains vercel",
                )
            )
            continue

        body = _read_text(ROOT / rel)
        if body is None:
            continue
        residual = _strip_allowed(body)
        if not _TOKEN_RE.search(residual):
            continue
        for lineno, line in enumerate(residual.splitlines(), start=1):
            if _is_gitignore_vercel_ignore(posix, line):
                hits.append(
                    Hit(
                        path=f"{posix}:{lineno}",
                        classification="ENVIRONMENT",
                        active=False,
                        detail="gitignore excludes accidental local CLI output",
                    )
                )
                continue
            if _ACTIVE_LINE_RE.search(line):
                hits.append(
                    Hit(
                        path=f"{posix}:{lineno}",
                        classification="ACTIVE_DEPENDENCY",
                        active=True,
                        detail=line.strip()[:200],
                    )
                )
                continue
            if _TOKEN_RE.search(line):
                kind = "DOCUMENTATION" if posix.startswith("docs/") else "COMMENT"
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
        "DOCUMENTATION": sum(1 for h in hits if h.classification == "DOCUMENTATION"),
        "HISTORICAL": sum(1 for h in hits if h.classification == "HISTORICAL"),
        "COMMENT": sum(1 for h in hits if h.classification == "COMMENT"),
        "hits": [asdict(h) for h in hits],
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"ACTIVE_DEPENDENCY={report['ACTIVE_DEPENDENCY']}")
        print(f"DOCUMENTATION={report['DOCUMENTATION']}")
        print(f"COMMENT={report['COMMENT']}")
        if active:
            print("ACTIVE hits:")
            for hit in active:
                print(f"  {hit.path}: {hit.detail}")
        else:
            print(
                "No active Vercel hosting/deploy/package/CI dependency in the git tree."
            )

    return 1 if active else 0


if __name__ == "__main__":
    sys.exit(main())
