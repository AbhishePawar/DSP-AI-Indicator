"""Safety tests — forbidden git operations must be blocked."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.git_recovery.git_ops import FORBIDDEN_ADD_ARGS, GitOps, GitSafetyError


def test_forbidden_add_args_constant() -> None:
    assert "-A" in FORBIDDEN_ADD_ARGS
    assert "--all" in FORBIDDEN_ADD_ARGS
    assert "." in FORBIDDEN_ADD_ARGS


def test_blocks_git_add_all(tmp_path: Path) -> None:
    git = GitOps(tmp_path, dry_run=True)
    with pytest.raises(GitSafetyError, match="Forbidden git add"):
        git.run(["git", "add", "-A"])
    with pytest.raises(GitSafetyError, match="Forbidden git add"):
        git.run(["git", "add", "."])
    with pytest.raises(GitSafetyError, match="Forbidden git add"):
        git.run(["git", "add", "--all"])


def test_blocks_force_push(tmp_path: Path) -> None:
    git = GitOps(tmp_path, dry_run=True)
    with pytest.raises(GitSafetyError, match="Forbidden push flag|Force push"):
        git.run(["git", "push", "--force", "origin", "main"])
    with pytest.raises(GitSafetyError, match="Forbidden push flag|Force push"):
        git.run(["git", "push", "-f", "origin", "main"])
    with pytest.raises(GitSafetyError, match="Forbidden push flag|Force push"):
        git.run(["git", "push", "--force-with-lease", "origin", "main"])


def test_blocks_history_rewrite(tmp_path: Path) -> None:
    git = GitOps(tmp_path, dry_run=True)
    with pytest.raises(GitSafetyError, match="History rewrite"):
        git.run(["git", "rebase", "main"])
    with pytest.raises(GitSafetyError, match="Hard reset"):
        git.run(["git", "reset", "--hard", "HEAD~1"])


def test_stage_paths_rejects_empty_and_dot(tmp_path: Path) -> None:
    git = GitOps(tmp_path, dry_run=True)
    with pytest.raises(GitSafetyError, match="empty"):
        git.stage_paths([])
    with pytest.raises(GitSafetyError, match="Unsafe stage path"):
        git.stage_paths(["."])


def test_stage_paths_rejects_ignored(tmp_path: Path) -> None:
    git = GitOps(tmp_path, dry_run=True)
    with pytest.raises(GitSafetyError, match="ignored"):
        git.stage_paths(["apps/web/node_modules/x.js"])


def test_dry_run_skips_mutating_commands(tmp_path: Path) -> None:
    git = GitOps(tmp_path, dry_run=True)
    result = git.run(["git", "add", "--", "README.md"])
    assert result.ok
    assert "[dry-run]" in result.stdout


def test_commit_requires_message(tmp_path: Path) -> None:
    git = GitOps(tmp_path, dry_run=True)
    with pytest.raises(GitSafetyError, match="Commit message"):
        git.commit("   ")
