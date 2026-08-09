"""P1-11 — hard RC1 release gate aggregator tests (negative + positive)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
GATE = ROOT / "scripts" / "ci" / "rc1_hard_release_gate.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("rc1_hard_release_gate", GATE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def gate():
    return _load_gate()


def _all_pass() -> dict[str, str]:
    return {gid: "PASS" for gid in (
        "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10", "G11"
    )}


def test_case_a_all_required_gates_pass(gate) -> None:
    decision = gate.evaluate_gates(_all_pass(), identity_ok=True)
    assert decision.release_allowed is True
    assert decision.decision == "GO"
    assert decision.exit_code == 0
    assert decision.blocking == []


def test_case_b_g2_blocked(gate) -> None:
    statuses = _all_pass()
    statuses["G2"] = "BLOCKED"
    decision = gate.evaluate_gates(statuses, identity_ok=True)
    assert decision.release_allowed is False
    assert decision.decision == "NO-GO"
    assert decision.exit_code != 0
    assert "G2" in decision.blocking


def test_case_c_g9_fails(gate) -> None:
    statuses = _all_pass()
    statuses["G9"] = "FAIL"
    decision = gate.evaluate_gates(statuses, identity_ok=True)
    assert decision.release_allowed is False
    assert "G9" in decision.blocking


def test_case_d_g10_or_p110_fails(gate) -> None:
    statuses = _all_pass()
    statuses["G10"] = "FAIL"
    decision = gate.evaluate_gates(statuses, identity_ok=True)
    assert decision.release_allowed is False
    assert "G10" in decision.blocking


def test_case_e_g11_fails(gate) -> None:
    statuses = _all_pass()
    statuses["G11"] = "FAIL"
    decision = gate.evaluate_gates(statuses, identity_ok=True)
    assert decision.release_allowed is False
    assert "G11" in decision.blocking


def test_case_f_stale_release_identity(gate) -> None:
    decision = gate.evaluate_gates(
        _all_pass(),
        identity_ok=False,
        identity={
            "epic": "EPS-003",
            "product_version": "2.0.0",
            "channel": "ga",
            "decision": "GENERAL_AVAILABILITY",
        },
    )
    assert decision.release_allowed is False
    assert "RELEASE_IDENTITY" in decision.blocking


def test_case_g_soft_fail_attempt_propagates_nonzero() -> None:
    """Critical command non-zero must not be swallowed."""
    completed = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--simulate-critical-failure",
            "7",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 7
    evidence = ROOT / "artifacts" / "rc1_hard_release_gate.json"
    assert evidence.is_file()
    data = json.loads(evidence.read_text(encoding="utf-8"))
    assert data["release_allowed"] is False
    assert data["decision"] == "NO-GO"
    assert "CRITICAL_CMD" in data["blocking"]


def test_cli_inject_g2_blocked_exits_nonzero() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--inject",
            "G2=BLOCKED",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "NO-GO" in completed.stdout or "NO-GO" in completed.stderr


def test_cli_inject_all_pass_exits_zero() -> None:
    # Default inject baseline is all PASS; a single explicit PASS is enough.
    completed = subprocess.run(
        [sys.executable, str(GATE), "--inject", "G1=PASS"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["release_allowed"] is True
    assert payload["decision"] == "GO"


def test_cli_stale_identity_blocks_even_if_gates_pass() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--inject",
            "G1=PASS",
            "--stale-identity",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0


def test_fixture_evidence_does_not_clear_g2(gate, monkeypatch: pytest.MonkeyPatch) -> None:
    """test_fixture must never be treated as real_live_authenticated_provider."""
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    fixture_path = artifacts / "g2_live_vendor_evidence.json"
    previous = fixture_path.read_text(encoding="utf-8") if fixture_path.is_file() else None
    try:
        fixture_path.write_text(
            json.dumps(
                {
                    "ok": True,
                    "evidence_class": "test_fixture",
                    "g2_status": "PASS",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        for name in (
            "DSP_FMP_API_KEY",
            "DSP_INVESTMENT_FMP_API_KEY",
            "DSP_MARKET_QUOTE_API_KEY",
            "DSP_MARKET_QUOTE_BASE_URL",
            "DSP_FINANCIAL_STATEMENT_API_KEY",
            "DSP_FINANCIAL_STATEMENT_BASE_URL",
        ):
            monkeypatch.delenv(name, raising=False)
        statuses, reasons, _ok, _identity = gate.collect_live_statuses(environ={})
        assert statuses["G2"] == "BLOCKED"
        assert "test_fixture" in reasons["G2"] or "BLOCKED" in reasons["G2"]
    finally:
        if previous is None:
            fixture_path.unlink(missing_ok=True)
        else:
            fixture_path.write_text(previous, encoding="utf-8")


def test_required_identity_constants(gate) -> None:
    assert gate.REQUIRED_IDENTITY == {
        "epic": "EPS-003",
        "product_version": "2.0.0-rc.1",
        "channel": "rc",
        "decision": "RELEASE_CANDIDATE",
    }
    ok, identity, _reason = gate.check_release_identity()
    assert ok is True
    assert identity["product_version"] == "2.0.0-rc.1"
