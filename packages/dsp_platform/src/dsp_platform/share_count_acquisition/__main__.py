"""Operator CLI for listed-equity share-count acquisition.

Never auto-promotes production snapshots.

  python -m dsp_platform.share_count_acquisition acquire --isin <ISIN> --mic <MIC>
  python -m dsp_platform.share_count_acquisition acquire-universe
  python -m dsp_platform.share_count_acquisition promote --candidate FILE --promoter NAME --human-approved
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from dsp_platform.promoted_share_count import DEFAULT_PROMOTED_SHARE_COUNT_DIR
from dsp_platform.share_count_acquisition.operator import (
    acquire_listed_equity,
    acquire_universe,
    promote_candidate_file,
)
from dsp_platform.share_count_acquisition.policy import iter_source_policy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m dsp_platform.share_count_acquisition",
        description="Acquire and validate listed-equity share-count evidence. No auto-promote.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    acquire = sub.add_parser("acquire", help="Acquire one instrument")
    acquire.add_argument("--isin", required=True)
    acquire.add_argument("--mic", required=True)
    acquire.add_argument("--horizon", default="")
    acquire.add_argument("--out", default="artifacts/stage_1l")
    acquire.add_argument("--dry-run", action="store_true")
    acquire.add_argument("--no-issuer", action="store_true")

    universe = sub.add_parser("acquire-universe", help="Acquire catalog instruments")
    universe.add_argument("--horizon", default="")
    universe.add_argument("--out", default="artifacts/stage_1l")
    universe.add_argument("--no-issuer", action="store_true")

    promote = sub.add_parser("promote", help="Human-promote a VALIDATED candidate")
    promote.add_argument("--candidate", required=True)
    promote.add_argument("--promoter", required=True)
    promote.add_argument("--human-approved", action="store_true")
    promote.add_argument("--destination", default=str(DEFAULT_PROMOTED_SHARE_COUNT_DIR))
    promote.add_argument("--history", default="artifacts/stage_1l/promotion_history")
    promote.add_argument("--horizon", default="")

    sources = sub.add_parser("sources", help="Print source selection policy")
    del sources

    args = parser.parse_args(argv)
    if args.command == "sources":
        rows = [
            {
                "source_id": row.source_id,
                "tier": str(row.tier),
                "authority": str(row.authority),
                "availability": str(row.availability),
                "exchanges": list(row.supported_exchanges),
                "evidence": list(row.supported_evidence_types),
                "implemented": row.implemented,
            }
            for row in iter_source_policy()
        ]
        print(json.dumps(rows, indent=2))
        return 0
    horizon = _parse_horizon(getattr(args, "horizon", ""))
    if args.command == "acquire":
        run = acquire_listed_equity(
            isin=args.isin,
            mic=args.mic,
            lookup_horizon=horizon,
            artifact_dir=Path(args.out),
            fetch_issuer=not args.no_issuer,
            dry_run=args.dry_run,
        )
        print(json.dumps(_run_view(run), indent=2))
        return 0 if run.state.value != "UNKNOWN" else 2
    if args.command == "acquire-universe":
        runs = acquire_universe(
            lookup_horizon=horizon,
            artifact_dir=Path(args.out),
            fetch_issuer=not args.no_issuer,
        )
        print(json.dumps([_run_view(run) for run in runs], indent=2))
        return 0
    record = promote_candidate_file(
        Path(args.candidate),
        destination_dir=Path(args.destination),
        history_dir=Path(args.history),
        promoter=args.promoter,
        human_approved=bool(args.human_approved),
        lookup_horizon=horizon or datetime.now(tz=UTC),
    )
    print(
        json.dumps(
            {
                "promoted": record.promoted,
                "path": str(record.path) if record.path else None,
                "integrity": record.integrity,
                "reason": record.reason,
            },
            indent=2,
        )
    )
    return 0 if record.promoted else 1


def _parse_horizon(raw: str) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise SystemExit("horizon must be timezone-aware")
    return parsed


def _run_view(run) -> dict[str, object]:
    identity = run.identity
    return {
        "symbol": identity.symbol,
        "isin": identity.isin,
        "mic": identity.mic,
        "state": str(run.state),
        "reason": run.reason,
        "shares_outstanding": (
            str(run.shares_outstanding) if run.shares_outstanding is not None else None
        ),
        "as_of": run.as_of.isoformat() if run.as_of else None,
        "complete_through": (
            run.complete_through.isoformat() if run.complete_through else None
        ),
        "nse_records": run.nse_records,
        "bse_records": run.bse_records,
        "nse_exhausted": run.nse_exhausted,
        "bse_exhausted": run.bse_exhausted,
        "issuer_observation": run.issuer_observation,
        "has_candidate": run.candidate is not None,
        "artifact": str(run.artifact_path) if run.artifact_path else None,
        "production_written": run.production_written,
    }


if __name__ == "__main__":
    raise SystemExit(main())
