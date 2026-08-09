#!/usr/bin/env python3
"""P1-11 — Hard RC1 release gate aggregator.

Authoritative model:

    required gate statuses
            ↓
      gate aggregator
            ↓
     PASS / NO-GO
            ↓
 release/tag/publish only on PASS

G2 BLOCKED (no genuine live vendor evidence) ⇒ RC1 NO-GO.
test_fixture ≠ real_live_authenticated_provider.

Soft-fail / swallowed non-zero critical commands are forbidden.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_PATH = ROOT / "artifacts" / "rc1_hard_release_gate.json"

REQUIRED_IDENTITY = {
    "epic": "EPS-003",
    "product_version": "2.0.0-rc.1",
    "channel": "rc",
    "decision": "RELEASE_CANDIDATE",
}

GATE_IDS = ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10", "G11")
BLOCKING_STATUSES = frozenset({"FAIL", "BLOCKED"})
PASS_STATUSES = frozenset({"PASS"})

# G2 PASS only when ok + CLEARED + real_live_authenticated_provider.
# These classes (and similar tokens) must never clear G2.
REFUSED_G2_EVIDENCE_CLASSES = frozenset(
    {
        "test_fixture",
        "credentials_unavailable",
        "memory",
        "seed",
        "offline",
        "mock",
        "memory_seed_refused_as_live",
    }
)
REFUSED_G2_CLASS_TOKENS = ("memory", "seed", "offline", "mock", "fixture")


def classify_g2_artifact_status(
    evidence: Mapping[str, Any] | None,
) -> tuple[str, str]:
    """Return (PASS|BLOCKED, reason) for a G2 evidence artifact.

    Only ``ok=true`` + ``g2_status=CLEARED`` +
    ``evidence_class=real_live_authenticated_provider`` may PASS.
    Unit fixtures may exercise this helper; never use fake live evidence
    against the production release gate path.
    """
    if not evidence:
        return "BLOCKED", "G2 BLOCKED — missing g2_live_vendor_evidence.json"

    evidence_class = str(evidence.get("evidence_class") or "")
    ok = evidence.get("ok") is True
    g2_status = str(evidence.get("g2_status") or "")
    lowered = evidence_class.lower()

    if evidence_class in REFUSED_G2_EVIDENCE_CLASSES:
        return (
            "BLOCKED",
            f"G2 BLOCKED — evidence_class={evidence_class} "
            "(not real_live_authenticated_provider)",
        )
    for token in REFUSED_G2_CLASS_TOKENS:
        if token in lowered and evidence_class != "real_live_authenticated_provider":
            return (
                "BLOCKED",
                f"G2 BLOCKED — evidence_class={evidence_class} "
                f"(refused token={token})",
            )

    if (
        ok
        and g2_status == "CLEARED"
        and evidence_class == "real_live_authenticated_provider"
    ):
        return "PASS", "live vendor evidence artifact ok (CLEARED)"

    return (
        "BLOCKED",
        "G2 BLOCKED — clearance contract failed "
        f"(ok={ok!r}, g2_status={g2_status!r}, evidence_class={evidence_class!r})",
    )


class GateDecision:
    """Plain decision object (avoid dataclass + dynamic import quirks)."""

    def __init__(
        self,
        *,
        release_allowed: bool,
        decision: str,
        statuses: dict[str, str],
        blocking: list[str] | None = None,
        identity_ok: bool = True,
        identity: dict[str, str] | None = None,
        reasons: dict[str, str] | None = None,
        exit_code: int = 0,
    ) -> None:
        self.release_allowed = release_allowed
        self.decision = decision
        self.statuses = statuses
        self.blocking = list(blocking or [])
        self.identity_ok = identity_ok
        self.identity = dict(identity or {})
        self.reasons = dict(reasons or {})
        self.g2_claim = False
        self.hard_fail = True
        self.soft_fail_forbidden = True
        self.gate = "P1-11"
        self.exit_code = exit_code

    def to_dict(self) -> dict[str, Any]:
        return {
            "release_allowed": self.release_allowed,
            "decision": self.decision,
            "statuses": self.statuses,
            "blocking": self.blocking,
            "identity_ok": self.identity_ok,
            "identity": self.identity,
            "reasons": self.reasons,
            "g2_claim": self.g2_claim,
            "hard_fail": self.hard_fail,
            "soft_fail_forbidden": self.soft_fail_forbidden,
            "gate": self.gate,
            "exit_code": self.exit_code,
        }


def evaluate_gates(
    statuses: Mapping[str, str],
    *,
    identity_ok: bool = True,
    identity: Mapping[str, str] | None = None,
    reasons: Mapping[str, str] | None = None,
) -> GateDecision:
    """Pure aggregator — no I/O. Any FAIL/BLOCKED or bad identity ⇒ NO-GO."""
    normalized = {gid: str(statuses.get(gid, "BLOCKED")).upper() for gid in GATE_IDS}
    blocking = [gid for gid, status in normalized.items() if status in BLOCKING_STATUSES]
    if not identity_ok:
        blocking.append("RELEASE_IDENTITY")
    # Deduplicate while preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for item in blocking:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    release_allowed = len(ordered) == 0
    return GateDecision(
        release_allowed=release_allowed,
        decision="GO" if release_allowed else "NO-GO",
        statuses=normalized,
        blocking=ordered,
        identity_ok=identity_ok,
        identity=dict(identity or REQUIRED_IDENTITY),
        reasons=dict(reasons or {}),
        exit_code=0 if release_allowed else 2,
    )


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _load_g2_classify():
    drill = ROOT / "scripts" / "ops" / "g2_live_vendor_evidence_drill.py"
    spec = importlib.util.spec_from_file_location("g2_live_vendor_evidence_drill", drill)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load G2 drill module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_release_identity(
    *,
    prod_manifest: Mapping[str, Any] | None = None,
    provenance_identity: Mapping[str, str] | None = None,
) -> tuple[bool, dict[str, str], str]:
    """Verify EPS-003 · 2.0.0-rc.1 · rc · RELEASE_CANDIDATE (no stale GA)."""
    prod_path = ROOT / "PRODUCTION_VERSION_MANIFEST.json"
    prod = dict(prod_manifest) if prod_manifest is not None else (load_json(prod_path) or {})
    identity = {
        "epic": str(prod.get("milestone") or ""),
        "product_version": str(
            prod.get("productVersion") or prod.get("frontendVersion") or ""
        ),
        "channel": str(prod.get("channel") or ""),
        "decision": str(prod.get("decision") or ""),
    }
    if provenance_identity:
        # Prefer authoritative provenance release identity when supplied.
        identity = {
            "epic": str(provenance_identity.get("epic") or identity["epic"]),
            "product_version": str(
                provenance_identity.get("product_version") or identity["product_version"]
            ),
            "channel": str(provenance_identity.get("channel") or identity["channel"]),
            "decision": str(
                provenance_identity.get("decision") or identity["decision"]
            ),
        }

    mismatches: list[str] = []
    for key, expected in REQUIRED_IDENTITY.items():
        actual = identity.get(key)
        if actual != expected:
            mismatches.append(f"{key}: expected {expected!r}, got {actual!r}")

    # Explicit stale-GA refusal
    if identity.get("channel") == "ga" or identity.get("decision") in {
        "GA",
        "GENERAL_AVAILABILITY",
        "GO",
    }:
        mismatches.append("stale GA identity refused for RC1 hard gate")

    ok = not mismatches
    reason = "ok" if ok else "; ".join(mismatches)
    return ok, identity, reason


def _status_from_ok_evidence(
    path: Path, *, require_ok: bool = True
) -> tuple[str, str]:
    data = load_json(path)
    if data is None:
        return "BLOCKED", f"missing evidence: {path.name}"
    if require_ok and data.get("ok") is True:
        return "PASS", f"evidence ok: {path.name}"
    return "FAIL", f"evidence not ok: {path.name}"


def collect_live_statuses(
    environ: Mapping[str, str] | None = None,
) -> tuple[dict[str, str], dict[str, str], bool, dict[str, str]]:
    """Collect G1–G11 from evidence + G2 classifier (no fabricated live claims)."""
    env = {k: str(v) for k, v in (environ or os.environ).items()}
    reasons: dict[str, str] = {}
    statuses: dict[str, str] = {}

    # G1 — source/repository integrity (manifest/profile)
    try:
        sys.path.insert(0, str(ROOT / "scripts" / "release"))
        from release_identity import (  # type: ignore
            profile_matches_manifest,
            resolve_profile,
        )

        prod = load_json(ROOT / "PRODUCTION_VERSION_MANIFEST.json") or {}
        profile = resolve_profile(prod)
        mismatches = profile_matches_manifest(profile, prod)
        if mismatches:
            statuses["G1"] = "FAIL"
            reasons["G1"] = "; ".join(mismatches)
        else:
            statuses["G1"] = "PASS"
            reasons["G1"] = f"profile={profile['channel']}"
    except Exception as exc:  # noqa: BLE001 — gate must fail closed
        statuses["G1"] = "FAIL"
        reasons["G1"] = f"integrity error: {exc}"

    # G2 — real live authenticated vendor evidence only
    # Artifact is authoritative (produced by live-data-evidence G2 job).
    g2_mod = _load_g2_classify()
    g2_gate = g2_mod.classify_gate(environ=env)
    g2_evidence = load_json(ROOT / "artifacts" / "g2_live_vendor_evidence.json")
    g2_status, g2_reason = classify_g2_artifact_status(g2_evidence)
    statuses["G2"] = g2_status
    if g2_status == "PASS":
        reasons["G2"] = g2_reason
    else:
        # Prefer artifact refusal reason; fall back to credential classifier.
        reasons["G2"] = g2_reason
        if g2_evidence is None and g2_gate.get("reason"):
            reasons["G2"] = str(g2_gate["reason"])

    # G3 / G10 — authenticity hard-fail (P1-10)
    p110_summary = load_json(ROOT / "artifacts" / "p110_authenticity_ci_summary.json")
    p110_detail = load_json(
        ROOT / "artifacts" / "p110_authenticity_hard_fail_evidence.json"
    )
    if (p110_summary and p110_summary.get("ok") is True) or (
        p110_detail and p110_detail.get("ok") is True
    ):
        statuses["G3"] = "PASS"
        statuses["G10"] = "PASS"
        reasons["G3"] = "P1-10 authenticity hard-fail PASS"
        reasons["G10"] = "P1-10 authenticity hard-fail required and PASS"
    else:
        statuses["G3"] = "FAIL"
        statuses["G10"] = "FAIL"
        reasons["G3"] = "P1-10 authenticity evidence missing or failed"
        reasons["G10"] = "P1-10 authenticity evidence missing or failed"

    # G4–G6, G8 — covered by authenticity suite when P1-10 summary ok
    for gid, label in (
        ("G4", "valuation integrity (P1-01/P1-02/P1-04 via P1-10 suite)"),
        ("G5", "Buffett authority (P1-05 via P1-10 suite)"),
        ("G6", "identity/authz (P0-05 via P1-10 suite)"),
        ("G8", "provenance/audit (P1-06 via P1-10 suite)"),
    ):
        if statuses.get("G3") == "PASS":
            statuses[gid] = "PASS"
            reasons[gid] = label
        else:
            statuses[gid] = "FAIL"
            reasons[gid] = f"{label}: blocked by G3/P1-10 failure"

    # G9 — P1-09 critical journey evidence
    p109 = load_json(ROOT / "artifacts" / "p109_critical_investment_evidence.json")
    if p109 and p109.get("ok") is True and p109.get("evidence_class") == "test_fixture":
        statuses["G9"] = "PASS"
        reasons["G9"] = "P1-09 API critical journey evidence ok (test_fixture)"
    elif p109 and p109.get("ok") is True:
        statuses["G9"] = "PASS"
        reasons["G9"] = "P1-09 evidence ok"
    else:
        statuses["G9"] = "FAIL"
        reasons["G9"] = "P1-09 critical journey evidence missing or failed"

    # G11 — real PostgreSQL restore evidence (never in-memory substitute)
    g11 = load_json(ROOT / "artifacts" / "g11_postgres_restore_evidence.json")
    if g11 and g11.get("ok") is True:
        statuses["G11"] = "PASS"
        reasons["G11"] = "G11 postgres restore evidence ok"
    elif g11 is not None:
        statuses["G11"] = "FAIL"
        reasons["G11"] = "G11 evidence present but ok=false"
    else:
        statuses["G11"] = "BLOCKED"
        reasons["G11"] = "G11 postgres restore evidence missing"

    # G7 — durable multi-tenant proof requires G11 + authenticity suite
    if statuses.get("G11") == "PASS" and statuses.get("G3") == "PASS":
        statuses["G7"] = "PASS"
        reasons["G7"] = "P0-06/P1-07 suite via P1-10 + G11 restore PASS"
    elif statuses.get("G11") in BLOCKING_STATUSES:
        statuses["G7"] = statuses["G11"]
        reasons["G7"] = f"G7 blocked by G11={statuses['G11']}"
    else:
        statuses["G7"] = "FAIL"
        reasons["G7"] = "G7 durable state incomplete"

    identity_ok, identity, id_reason = check_release_identity()
    reasons["RELEASE_IDENTITY"] = id_reason
    return statuses, reasons, identity_ok, identity


def run_critical_command(command: list[str], *, cwd: Path | None = None) -> int:
    """Run a critical command; never soft-fail / swallow non-zero."""
    print(f"CRITICAL_CMD: {' '.join(command)}", file=sys.stderr)
    completed = subprocess.run(command, cwd=str(cwd or ROOT), check=False)
    if completed.returncode != 0:
        print(
            f"CRITICAL_CMD_FAILED exit={completed.returncode} "
            "(soft-fail forbidden)",
            file=sys.stderr,
        )
    return completed.returncode


def write_evidence(decision: GateDecision) -> Path:
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = decision.to_dict()
    payload["required_identity"] = dict(REQUIRED_IDENTITY)
    payload["note"] = (
        "G2 BLOCKED without real_live_authenticated_provider evidence ⇒ RC1 NO-GO. "
        "test_fixture must never clear G2."
    )
    EVIDENCE_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"evidence_written={EVIDENCE_PATH}", file=sys.stderr)
    return EVIDENCE_PATH


def parse_inject(values: list[str]) -> dict[str, str]:
    out: dict[str, str] = {gid: "PASS" for gid in GATE_IDS}
    for raw in values:
        if "=" not in raw:
            raise ValueError(f"inject must be GATE=STATUS, got {raw!r}")
        key, value = raw.split("=", 1)
        key = key.strip().upper()
        value = value.strip().upper()
        if key not in GATE_IDS:
            raise ValueError(f"unknown gate {key!r}")
        if value not in {"PASS", "FAIL", "BLOCKED"}:
            raise ValueError(f"unknown status {value!r} for {key}")
        out[key] = value
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P1-11 RC1 hard release gate")
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Collect live statuses from evidence + G2 classifier",
    )
    parser.add_argument(
        "--inject",
        action="append",
        default=[],
        help="Inject GATE=STATUS (repeatable). Defaults unset gates to PASS.",
    )
    parser.add_argument(
        "--stale-identity",
        action="store_true",
        help="Force stale GA identity for negative tests",
    )
    parser.add_argument(
        "--simulate-critical-failure",
        type=int,
        metavar="EXIT_CODE",
        help="Simulate a critical command non-zero exit and propagate it (no soft-fail)",
    )
    args = parser.parse_args(argv)

    if args.simulate_critical_failure is not None:
        code = int(args.simulate_critical_failure)
        if code == 0:
            print("simulate-critical-failure requires non-zero EXIT_CODE", file=sys.stderr)
            return 1
        print(
            f"CRITICAL_CMD_FAILED exit={code} (soft-fail forbidden)",
            file=sys.stderr,
        )
        decision = evaluate_gates({gid: "PASS" for gid in GATE_IDS}, identity_ok=True)
        decision.release_allowed = False
        decision.decision = "NO-GO"
        decision.blocking = ["CRITICAL_CMD"]
        decision.exit_code = code
        decision.reasons = {"CRITICAL_CMD": f"exit={code}"}
        write_evidence(decision)
        return code

    if args.evaluate and args.inject:
        print("Use either --evaluate or --inject, not both", file=sys.stderr)
        return 1

    if args.inject:
        statuses = parse_inject(args.inject)
        reasons = {k: f"injected={v}" for k, v in statuses.items()}
        if args.stale_identity:
            identity_ok = False
            identity = {
                "epic": "EPS-003",
                "product_version": "2.0.0",
                "channel": "ga",
                "decision": "GENERAL_AVAILABILITY",
            }
            reasons["RELEASE_IDENTITY"] = "stale GA identity forced"
        else:
            identity_ok, identity, id_reason = check_release_identity()
            reasons["RELEASE_IDENTITY"] = id_reason
    elif args.evaluate:
        statuses, reasons, identity_ok, identity = collect_live_statuses()
        if args.stale_identity:
            identity_ok = False
            identity = {
                "epic": "EPS-003",
                "product_version": "2.0.0",
                "channel": "ga",
                "decision": "GENERAL_AVAILABILITY",
            }
            reasons["RELEASE_IDENTITY"] = "stale GA identity forced"
    else:
        parser.error("one of --evaluate / --inject / --critical-cmd is required")

    decision = evaluate_gates(
        statuses,
        identity_ok=identity_ok,
        identity=identity,
        reasons=reasons,
    )
    write_evidence(decision)

    print(
        json.dumps(
            {
                "release_allowed": decision.release_allowed,
                "decision": decision.decision,
                "blocking": decision.blocking,
                "exit_code": decision.exit_code,
            },
            indent=2,
        )
    )
    if decision.release_allowed:
        print("RC1 HARD GATE PASS — release_allowed=true", file=sys.stderr)
    else:
        print(
            "RC1 HARD GATE NO-GO — release_allowed=false — "
            f"blocking={','.join(decision.blocking)}",
            file=sys.stderr,
        )
        if "G2" in decision.blocking:
            print(
                "G2 BLOCKED — awaiting legitimate FMP credential ⇒ RC1 NO-GO",
                file=sys.stderr,
            )
    return decision.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
