"""CLI for Git Recovery Manager."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.git_recovery import __version__
from tools.git_recovery.git_ops import GitOps, GitSafetyError
from tools.git_recovery.models import RecoveryGroup, RecoveryPlan
from tools.git_recovery.planner import build_plan, write_plan


def _repo_root_from_cwd() -> Path:
    return Path.cwd()


def _prompt_yes_no(question: str) -> bool:
    while True:
        answer = input(f"{question} [Y/N]: ").strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please answer Y or N.")


def _print_group(idx: int, total: int, group: RecoveryGroup) -> None:
    print()
    print("=" * 60)
    print(f"GROUP {idx}/{total}: {group.title} ({group.key})")
    print("=" * 60)
    print(f"Purpose:     {group.purpose}")
    print(f"Epic:        {group.epic}")
    print(f"Package:     {group.package}")
    print(f"Action hint: {group.action}")
    print(f"Risk:        {group.risk.value}")
    deps = ", ".join(group.depends_on) if group.depends_on else "(none)"
    print(f"Depends on:  {deps}")
    print(f"Message:     {group.suggested_message}")
    print(f"Files ({len(group.files)}):")
    for item in group.files[:40]:
        print(f"  {item.status:2} {item.path}")
    if len(group.files) > 40:
        print(f"  ... +{len(group.files) - 40} more")


def cmd_plan(args: argparse.Namespace) -> int:
    git = GitOps(_repo_root_from_cwd(), dry_run=False)
    porcelain = git.status_porcelain()
    branch = git.current_branch()
    plan = build_plan(porcelain, branch=branch, remote=args.remote)
    out = Path(args.output)
    write_plan(plan, out)
    print(f"Wrote recovery plan: {out.resolve()}")
    print(f"Branch: {branch}")
    print(f"Files:  {plan.total_files}")
    print(f"Groups: {len(plan.commit_groups)}")
    print(f"Ignored:{len(plan.ignored)}")
    return 0


def _recover_group(
    git: GitOps,
    group: RecoveryGroup,
    *,
    remote: str,
    push: bool,
) -> None:
    paths = group.paths
    print(f"Staging {len(paths)} path(s)...")
    git.stage_paths(paths)
    print(f"Committing: {group.suggested_message!r}")
    result = git.commit(group.suggested_message)
    if result.stdout.strip():
        print(result.stdout.strip())
    if not git.verify_clean_commit():
        raise GitSafetyError("Staged files remain after commit — aborting group")
    if push:
        print(f"Pushing to {remote} (no force)...")
        push_result = git.push_current_branch(remote=remote)
        if push_result.stdout.strip():
            print(push_result.stdout.strip())
        if push_result.stderr.strip():
            print(push_result.stderr.strip())
    print(git.status_short().strip())


def cmd_recover(args: argparse.Namespace) -> int:
    git = GitOps(_repo_root_from_cwd(), dry_run=args.dry_run)
    porcelain = git.status_porcelain()
    branch = git.current_branch()
    plan = build_plan(porcelain, branch=branch, remote=args.remote)
    out = Path(args.output)
    write_plan(plan, out)
    print(f"Wrote recovery plan: {out.resolve()}")

    if not plan.commit_groups:
        print("Repository has no commit-eligible dirty groups.")
        if plan.ignored:
            print(f"Note: {len(plan.ignored)} ignored path(s) remain (not committed).")
        print(git.status_short())
        return 0

    total = len(plan.commit_groups)
    committed = 0
    skipped = 0

    for idx, group in enumerate(plan.commit_groups, start=1):
        _print_group(idx, total, group)
        if args.dry_run:
            print("[dry-run] Would ask: Commit this group? [Y/N]")
            continue
        if not _prompt_yes_no("Commit this group?"):
            print("Skipped.")
            skipped += 1
            continue
        try:
            _recover_group(git, group, remote=args.remote, push=not args.no_push)
            committed += 1
        except GitSafetyError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            print("Stopping recovery. Fix the issue, then re-run.")
            print(git.status_short())
            return 1

    print()
    print("=" * 60)
    print("Recovery pass complete")
    print(f"Committed groups: {committed}")
    print(f"Skipped groups:   {skipped}")
    if args.dry_run:
        print("Dry-run only — no commits or pushes performed.")
    print()
    print("Final git status:")
    print(git.status_short())

    # Re-check remaining dirty files
    remaining = git.status_porcelain().strip()
    if remaining:
        print()
        print("Repository is NOT fully clean. Re-run recover for remaining groups,")
        print("or inspect ignored/unclassified paths in the plan.")
        return 0
    print()
    print("Repository is clean (no porcelain entries).")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    git = GitOps(_repo_root_from_cwd())
    print(git.status_short())
    porcelain = git.status_porcelain()
    plan = build_plan(porcelain, branch=git.current_branch(), remote=args.remote)
    print(f"Files: {plan.total_files} | Groups: {len(plan.commit_groups)} | Ignored: {len(plan.ignored)}")
    for g in plan.commit_groups:
        print(f"  - {g.key:28} {len(g.files):4d} files  risk={g.risk.value}")
    return 0


def _add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--remote",
        default="origin",
        help="Git remote name for push (default: origin)",
    )
    p.add_argument(
        "--output",
        default="git_recovery_plan.md",
        help="Path for generated recovery plan markdown (default: ./git_recovery_plan.md)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="git-recovery",
        description="DSP Git Recovery Manager — logical commits from a dirty tree.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    p_plan = sub.add_parser("plan", help="Generate git_recovery_plan.md only")
    _add_common_args(p_plan)
    p_plan.set_defaults(func=cmd_plan)

    p_recover = sub.add_parser(
        "recover",
        help="Interactive recovery: confirm each group, commit, push",
    )
    _add_common_args(p_recover)
    p_recover.add_argument(
        "--dry-run",
        action="store_true",
        help="Show groups and plan without staging/committing/pushing",
    )
    p_recover.add_argument(
        "--no-push",
        action="store_true",
        help="Commit locally but do not push",
    )
    p_recover.set_defaults(func=cmd_recover)

    p_status = sub.add_parser("status", help="Show classified dirty groups")
    _add_common_args(p_status)
    p_status.set_defaults(func=cmd_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except GitSafetyError as exc:
        print(f"SAFETY ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
