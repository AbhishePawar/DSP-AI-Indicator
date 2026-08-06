"""Safe git operations for recovery (never add -A, never force push)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


class GitSafetyError(RuntimeError):
    """Raised when a forbidden or unsafe git operation is attempted."""


FORBIDDEN_ADD_ARGS = {"-A", "--all", ".", "-u", "--update"}
FORBIDDEN_PUSH_FLAGS = {"--force", "-f", "--force-with-lease", "--force-if-includes"}


@dataclass
class GitResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class GitOps:
    """Thin wrapper around git with hard safety rails."""

    def __init__(self, repo_root: Path, *, dry_run: bool = False) -> None:
        self.repo_root = repo_root.resolve()
        self.dry_run = dry_run

    def run(self, args: list[str], *, check: bool = False) -> GitResult:
        if not args or args[0] != "git":
            raise GitSafetyError(f"Only git commands allowed, got: {args!r}")
        self._assert_safe(args)
        if self.dry_run and args[1] in {"add", "commit", "push"}:
            return GitResult(args=args, returncode=0, stdout="[dry-run] skipped", stderr="")
        completed = subprocess.run(
            args,
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        result = GitResult(
            args=args,
            returncode=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
        )
        if check and not result.ok:
            raise GitSafetyError(
                f"git command failed ({result.returncode}): {' '.join(args)}\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        return result

    def _assert_safe(self, args: list[str]) -> None:
        # Never allow force push / history rewrite
        lowered = [a.lower() for a in args[1:]]
        for flag in FORBIDDEN_PUSH_FLAGS:
            if flag in lowered:
                raise GitSafetyError(f"Forbidden push flag blocked: {flag}")
        if "push" in lowered and any(a.startswith("--force") for a in lowered):
            raise GitSafetyError("Force push blocked")
        if any(a in {"rebase", "filter-branch", "filter-repo"} for a in lowered):
            raise GitSafetyError("History rewrite commands are blocked")
        if "reset" in lowered and ("--hard" in lowered or "-h" in {a.lower() for a in args}):
            raise GitSafetyError("Hard reset is blocked")
        if args[1] == "add":
            add_args = args[2:]
            for token in add_args:
                if token in FORBIDDEN_ADD_ARGS:
                    raise GitSafetyError(
                        f"Forbidden git add argument blocked: {token!r}. "
                        "Stage explicit file paths only."
                    )
            if not add_args:
                raise GitSafetyError("git add requires explicit file paths")

    def status_porcelain(self) -> str:
        result = self.run(["git", "status", "--porcelain=v1", "-uall"], check=True)
        return result.stdout

    def current_branch(self) -> str:
        result = self.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], check=True)
        return result.stdout.strip()

    def status_short(self) -> str:
        result = self.run(["git", "status", "-sb"], check=True)
        return result.stdout

    def stage_paths(self, paths: list[str]) -> GitResult:
        if not paths:
            raise GitSafetyError("Refusing to stage empty path list")
        # Resolve and ensure paths stay inside repo; stage relative paths only
        rel_paths: list[str] = []
        for raw in paths:
            candidate = Path(raw)
            if candidate.is_absolute():
                try:
                    candidate = candidate.resolve().relative_to(self.repo_root)
                except ValueError as exc:
                    raise GitSafetyError(f"Path outside repository: {raw}") from exc
            normalized = candidate.as_posix()
            if normalized in {".", ""} or normalized.startswith(".."):
                raise GitSafetyError(f"Unsafe stage path: {raw!r}")
            if is_ignored_path_safe(normalized):
                raise GitSafetyError(f"Refusing to stage ignored/unsafe path: {normalized}")
            rel_paths.append(normalized)
        # Deduplicate preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for p in rel_paths:
            if p not in seen:
                seen.add(p)
                unique.append(p)
        return self.run(["git", "add", "--", *unique], check=True)

    def commit(self, message: str) -> GitResult:
        if not message.strip():
            raise GitSafetyError("Commit message must be non-empty")
        # Verify something is staged
        staged = self.run(["git", "diff", "--cached", "--name-only"], check=True)
        if not staged.stdout.strip() and not self.dry_run:
            raise GitSafetyError("Nothing staged — refusing empty commit")
        return self.run(["git", "commit", "-m", message], check=True)

    def push_current_branch(self, remote: str = "origin") -> GitResult:
        branch = self.current_branch()
        if not branch or branch == "HEAD":
            raise GitSafetyError("Detached HEAD — refusing push")
        # Explicit refspec; never --force
        return self.run(["git", "push", remote, f"HEAD:refs/heads/{branch}"], check=True)

    def verify_clean_commit(self) -> bool:
        """Return True if index has no staged leftovers after commit."""
        staged = self.run(["git", "diff", "--cached", "--name-only"], check=True)
        return staged.stdout.strip() == ""


def is_ignored_path_safe(path: str) -> bool:
    """Local copy to avoid circular import issues in safety checks."""
    from tools.git_recovery.classifier import is_ignored_path

    return is_ignored_path(path)
