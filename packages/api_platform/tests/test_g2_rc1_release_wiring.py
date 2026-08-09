"""G2 → RC1 release wiring contracts (unit fixtures only; no fake live drill)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
GATE = ROOT / "scripts" / "ci" / "rc1_hard_release_gate.py"
RELEASE_WF = ROOT / ".github" / "workflows" / "release.yml"
G2_WF = ROOT / ".github" / "workflows" / "g2-live-vendor-evidence.yml"


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
    return {
        gid: "PASS"
        for gid in (
            "G1",
            "G2",
            "G3",
            "G4",
            "G5",
            "G6",
            "G7",
            "G8",
            "G9",
            "G10",
            "G11",
        )
    }


def test_g2_missing_evidence_blocked(gate) -> None:
    status, reason = gate.classify_g2_artifact_status(None)
    assert status == "BLOCKED"
    assert "missing" in reason.lower() or "BLOCKED" in reason


def test_g2_credentials_unavailable_blocked(gate) -> None:
    status, reason = gate.classify_g2_artifact_status(
        {
            "ok": False,
            "g2_status": "BLOCKED",
            "evidence_class": "credentials_unavailable",
        }
    )
    assert status == "BLOCKED"
    assert "credentials_unavailable" in reason


def test_g2_fixture_evidence_blocked(gate) -> None:
    status, _reason = gate.classify_g2_artifact_status(
        {
            "ok": True,
            "g2_status": "CLEARED",
            "evidence_class": "test_fixture",
        }
    )
    assert status == "BLOCKED"


@pytest.mark.parametrize(
    "evidence_class",
    ["memory", "seed", "offline", "mock", "memory_seed_refused_as_live"],
)
def test_g2_fake_seed_memory_offline_mock_blocked(gate, evidence_class: str) -> None:
    status, reason = gate.classify_g2_artifact_status(
        {
            "ok": True,
            "g2_status": "CLEARED",
            "evidence_class": evidence_class,
        }
    )
    assert status == "BLOCKED"
    assert evidence_class in reason or "BLOCKED" in reason


def test_g2_real_live_without_cleared_blocked(gate) -> None:
    status, _reason = gate.classify_g2_artifact_status(
        {
            "ok": True,
            "g2_status": "PASS",
            "evidence_class": "real_live_authenticated_provider",
        }
    )
    assert status == "BLOCKED"


def test_g2_genuine_clearance_contract_pass(gate) -> None:
    """Isolated unit fixture for classifier only — not a live drill substitute."""
    status, reason = gate.classify_g2_artifact_status(
        {
            "ok": True,
            "g2_status": "CLEARED",
            "evidence_class": "real_live_authenticated_provider",
            "authenticated": True,
            "quote_adapter": "ConfiguredHttpMarketQuoteAdapter",
            "statement_adapter": "ConfiguredHttpFinancialStatementAdapter",
            "quote_retrieved_at": "2026-08-09T00:00:00+00:00",
            "steps": {"quote": {"retrieved_at": "2026-08-09T00:00:00+00:00"}},
        }
    )
    assert status == "PASS"
    assert "CLEARED" in reason


def test_g2_cleared_without_live_shape_blocked(gate) -> None:
    status, reason = gate.classify_g2_artifact_status(
        {
            "ok": True,
            "g2_status": "CLEARED",
            "evidence_class": "real_live_authenticated_provider",
        }
    )
    assert status == "BLOCKED"
    assert "live drill shape" in reason


def test_g2_pending_live_class_blocked(gate) -> None:
    status, _reason = gate.classify_g2_artifact_status(
        {
            "ok": False,
            "g2_status": "READY",
            "evidence_class": "credentials_present_pending_live",
        }
    )
    assert status == "BLOCKED"


def test_g2_public_web_never_clears(gate) -> None:
    status, _reason = gate.classify_g2_artifact_status(
        {
            "ok": True,
            "g2_status": "CLEARED",
            "evidence_class": "public_web",
            "authenticated": True,
            "quote_adapter": "x",
            "statement_adapter": "y",
            "quote_retrieved_at": "t",
        }
    )
    assert status == "BLOCKED"


def test_release_workflow_requires_g2_reusable() -> None:
    text = RELEASE_WF.read_text(encoding="utf-8")
    assert "g2-live-vendor" in text
    assert "uses: ./.github/workflows/g2-live-vendor-evidence.yml" in text
    assert "secrets: inherit" in text
    assert "needs: [p109-api, p110-authenticity, g11-postgres, g2-live-vendor]" in text
    assert "g2_live_vendor_evidence.json" in text
    assert "rc1-hard-gate" in text
    assert "needs: [rc1-hard-gate]" in text
    # Must not inject repo-level vendor secrets into P1-11 (artifact is authority).
    assert "DSP_FMP_API_KEY: ${{ secrets.DSP_FMP_API_KEY }}" not in text
    # Protected environment belongs to the reusable G2 workflow, not P1-11.
    rc1_section = text.split("rc1-hard-gate:")[1].split("publish:")[0]
    assert "environment: live-data-evidence" not in rc1_section
    assert "DSP_MARKET_QUOTE_API_KEY" not in rc1_section


def test_g2_workflow_uses_live_data_evidence_environment() -> None:
    text = G2_WF.read_text(encoding="utf-8")
    assert "environment: live-data-evidence" in text
    assert "workflow_call:" in text
    assert "workflow_dispatch:" in text
    assert "Assert G2 clearance contract" in text
    assert "g2_status" in text
    assert "real_live_authenticated_provider" in text
    assert "CLEARED" in text
    assert "g2_live_vendor_evidence_drill.py" in text
    assert "g2_provider_configuration_diagnostic.py" in text
    assert "pull_request:" not in text


def test_release_p111_consumes_g2_artifact_path() -> None:
    text = RELEASE_WF.read_text(encoding="utf-8")
    assert "Normalize evidence paths" in text
    assert "Require G2 clearance artifact before evaluate" in text
    assert "rc1_hard_release_gate.py --evaluate" in text
    # Artifact handoff from reusable G2 job.
    assert "download-artifact@v4" in text
    assert "g2_live_vendor_evidence.json" in text


def test_p111_nogo_when_g2_blocked(gate) -> None:
    statuses = _all_pass()
    statuses["G2"] = "BLOCKED"
    decision = gate.evaluate_gates(statuses, identity_ok=True)
    assert decision.decision == "NO-GO"
    assert decision.release_allowed is False
    assert "G2" in decision.blocking


def test_p111_go_only_when_all_gates_pass(gate) -> None:
    decision = gate.evaluate_gates(_all_pass(), identity_ok=True)
    assert decision.decision == "GO"
    assert decision.release_allowed is True
    assert decision.blocking == []


def test_p111_nogo_if_any_gate_not_pass(gate) -> None:
    for gid in ("G1", "G3", "G7", "G9", "G10", "G11"):
        statuses = _all_pass()
        statuses[gid] = "FAIL"
        decision = gate.evaluate_gates(statuses, identity_ok=True)
        assert decision.decision == "NO-GO", gid
        assert gid in decision.blocking


def test_collect_live_statuses_fixture_g2_never_pass(
    gate, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    path = artifacts / "g2_live_vendor_evidence.json"
    previous = path.read_text(encoding="utf-8") if path.is_file() else None
    try:
        path.write_text(
            json.dumps(
                {
                    "ok": True,
                    "g2_status": "CLEARED",
                    "evidence_class": "test_fixture",
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
        assert "test_fixture" in reasons["G2"]
    finally:
        if previous is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(previous, encoding="utf-8")


def test_collect_live_statuses_unit_fixture_marker_never_pass(
    gate, monkeypatch: pytest.MonkeyPatch
) -> None:
    """unit_fixture markers must never clear G2 via collect_live_statuses."""
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    path = artifacts / "g2_live_vendor_evidence.json"
    previous = path.read_text(encoding="utf-8") if path.is_file() else None
    try:
        path.write_text(
            json.dumps(
                {
                    "ok": True,
                    "g2_status": "CLEARED",
                    "evidence_class": "real_live_authenticated_provider",
                    "authenticated": True,
                    "quote_adapter": "ConfiguredHttpMarketQuoteAdapter",
                    "statement_adapter": "ConfiguredHttpFinancialStatementAdapter",
                    "quote_retrieved_at": "2026-08-09T00:00:00+00:00",
                    "unit_fixture": True,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        statuses, reasons, _ok, _identity = gate.collect_live_statuses(environ={})
        assert statuses["G2"] == "BLOCKED"
        assert "unit_fixture" in reasons["G2"]
    finally:
        if previous is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(previous, encoding="utf-8")


def test_release_discards_checked_in_g2_artifact() -> None:
    text = RELEASE_WF.read_text(encoding="utf-8")
    assert "Discard checked-in G2 artifact before download" in text
    assert "rm -f artifacts/g2_live_vendor_evidence.json" in text
