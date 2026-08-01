"""Tests for recovery plan rendering."""

from __future__ import annotations

from pathlib import Path

from tools.git_recovery.planner import build_plan, render_plan_markdown, write_plan


SAMPLE = """\
 M .gitignore
?? docs/EPIC_F000_README.md
?? packages/api_platform/src/api_platform/api/routers/research.py
?? apps/web/.next/cache/webpack.pack
"""


def test_build_plan_summary() -> None:
    plan = build_plan(SAMPLE, branch="feature/x", remote="origin")
    assert plan.branch == "feature/x"
    assert plan.total_files == 4
    assert len(plan.ignored) == 1
    assert any(g.key == "configuration" for g in plan.commit_groups)
    assert any(g.key == "api" for g in plan.commit_groups)


def test_render_contains_safety_and_groups() -> None:
    plan = build_plan(SAMPLE, branch="feature/x")
    md = render_plan_markdown(plan)
    assert "# Git Recovery Plan" in md
    assert "Never `git add -A`" in md
    assert "Estimated Risk" in md
    assert "Suggested Commit Message" in md
    assert ".gitignore" in md


def test_write_plan(tmp_path: Path) -> None:
    plan = build_plan(SAMPLE, branch="feature/x")
    out = tmp_path / "git_recovery_plan.md"
    write_plan(plan, out)
    assert out.is_file()
    assert "Groups" in out.read_text(encoding="utf-8")
