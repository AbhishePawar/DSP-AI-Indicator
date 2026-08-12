"""CLI smoke tests (no live git mutations)."""

from __future__ import annotations

from tools.git_recovery.cli import build_parser


def test_parser_requires_command() -> None:
    parser = build_parser()
    assert parser.parse_args(["plan"]).command == "plan"
    assert parser.parse_args(["status"]).command == "status"
    assert parser.parse_args(["recover", "--dry-run"]).dry_run is True
    assert parser.parse_args(["recover", "--no-push"]).no_push is True


def test_default_output_path() -> None:
    args = build_parser().parse_args(["plan"])
    assert args.output == "git_recovery_plan.md"
