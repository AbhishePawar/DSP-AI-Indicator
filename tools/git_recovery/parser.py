"""Parse `git status --porcelain=v1 -uall` output."""

from __future__ import annotations

import re
from pathlib import Path

from tools.git_recovery.models import ChangedFile

# XY path | XY orig -> path  (rename)
_RENAME_RE = re.compile(r"^(.+?) -> (.+)$")


def parse_porcelain(text: str) -> list[ChangedFile]:
    """Parse porcelain v1 lines into ChangedFile records.

    Supports:
    - `` M path``
    - ``?? path``
    - ``R  old -> new``
    - ``A  path``
    - ``D  path``
    """
    files: list[ChangedFile] = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        if len(raw) < 4:
            continue
        status = raw[:2]
        remainder = raw[3:]
        original: str | None = None
        path = remainder
        match = _RENAME_RE.match(remainder)
        if match:
            original = match.group(1).strip()
            path = match.group(2).strip()
        # Normalize separators for classification consistency
        path = path.replace("\\", "/")
        if original:
            original = original.replace("\\", "/")
        files.append(ChangedFile(status=status.strip() or status, path=path, original_path=original))
    return files


def parse_porcelain_file(path: Path) -> list[ChangedFile]:
    return parse_porcelain(path.read_text(encoding="utf-8", errors="replace"))
