"""Tests for porcelain parsing."""

from __future__ import annotations

from tools.git_recovery.parser import parse_porcelain


def test_parse_modified_and_untracked() -> None:
    text = " M apps/web/src/app/page.tsx\n?? docs/NEW.md\n"
    files = parse_porcelain(text)
    assert len(files) == 2
    assert files[0].status == "M"
    assert files[0].path == "apps/web/src/app/page.tsx"
    assert files[1].is_untracked
    assert files[1].path == "docs/NEW.md"


def test_parse_rename() -> None:
    text = "R  old/path.py -> new/path.py\n"
    files = parse_porcelain(text)
    assert len(files) == 1
    assert files[0].path == "new/path.py"
    assert files[0].original_path == "old/path.py"


def test_parse_ignores_blank_lines() -> None:
    assert parse_porcelain("\n\n") == []


def test_normalize_backslashes() -> None:
    files = parse_porcelain("?? apps\\web\\src\\x.ts\n")
    assert files[0].path == "apps/web/src/x.ts"
