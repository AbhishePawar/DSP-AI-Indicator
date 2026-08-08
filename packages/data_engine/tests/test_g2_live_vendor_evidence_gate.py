"""G2 — live vendor evidence gate (fail-closed; no fabricated live claims)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DRILL = ROOT / "scripts" / "ops" / "g2_live_vendor_evidence_drill.py"


def _load_drill():
    spec = importlib.util.spec_from_file_location(
        "g2_live_vendor_evidence_drill", DRILL
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_gate_blocked_when_credentials_absent() -> None:
    mod = _load_drill()
    gate = mod.classify_gate(environ={})
    assert gate["ready"] is False
    assert gate["status"] == "BLOCKED"
    assert gate["evidence_class"] == "credentials_unavailable"
    assert all(v == "ABSENT" for v in gate["credential_presence"].values())


def test_gate_refuses_memory_flags_as_live() -> None:
    mod = _load_drill()
    env = {
        "DSP_MARKET_QUOTE_API_KEY": "k",
        "DSP_MARKET_QUOTE_BASE_URL": "https://example.invalid/quote",
        "DSP_FINANCIAL_STATEMENT_API_KEY": "k",
        "DSP_FINANCIAL_STATEMENT_BASE_URL": "https://example.invalid/stmt",
        "DSP_MARKET_QUOTE_MEMORY": "true",
    }
    gate = mod.classify_gate(environ=env)
    assert gate["ready"] is False
    assert gate["evidence_class"] == "memory_seed_refused_as_live"
    assert "DSP_MARKET_QUOTE_MEMORY" in gate["memory_flags_enabled"]


def test_gate_ready_only_with_full_http_credentials() -> None:
    mod = _load_drill()
    env = {
        "DSP_MARKET_QUOTE_API_KEY": "k",
        "DSP_MARKET_QUOTE_BASE_URL": "https://example.invalid/quote",
        "DSP_FINANCIAL_STATEMENT_API_KEY": "k",
        "DSP_FINANCIAL_STATEMENT_BASE_URL": "https://example.invalid/stmt",
    }
    gate = mod.classify_gate(environ=env)
    assert gate["ready"] is True
    assert gate["route"] == "configured_http"
    assert gate["evidence_class"] == "real_live_authenticated_provider"


def test_gate_ready_with_single_fmp_key() -> None:
    mod = _load_drill()
    gate = mod.classify_gate(environ={"DSP_FMP_API_KEY": "k"})
    assert gate["ready"] is True
    assert gate["route"] == "fmp"
    assert gate["evidence_class"] == "real_live_authenticated_provider"
    assert gate["credential_presence"]["DSP_FMP_API_KEY"] == "PRESENT"


def test_drill_fails_closed_without_credentials(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for name in (
        "DSP_MARKET_QUOTE_API_KEY",
        "DSP_MARKET_QUOTE_BASE_URL",
        "DSP_FINANCIAL_STATEMENT_API_KEY",
        "DSP_FINANCIAL_STATEMENT_BASE_URL",
        "DSP_FMP_API_KEY",
        "DSP_INVESTMENT_FMP_API_KEY",
        "DSP_MARKET_QUOTE_MEMORY",
        "DSP_FINANCIAL_STATEMENT_MEMORY",
    ):
        monkeypatch.delenv(name, raising=False)

    completed = subprocess.run(
        [sys.executable, str(DRILL)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 2
    evidence_path = ROOT / "artifacts" / "g2_live_vendor_evidence.json"
    assert evidence_path.is_file()
    data = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert data["ok"] is False
    assert data["gate"] == "G2"
    assert data["g2_status"] == "BLOCKED"
    assert data["evidence_class"] == "credentials_unavailable"
    assert data["secrets_logged"] is False
    # Presence labels only — never raw secret values.
    for label in data["credential_presence"].values():
        assert label in {"PRESENT", "ABSENT"}
    blob = json.dumps(data)
    assert "Bearer " not in blob
    assert "sk-" not in blob.lower()


def test_workflow_scaffolding_exists() -> None:
    wf = ROOT / ".github" / "workflows" / "g2-live-vendor-evidence.yml"
    text = wf.read_text(encoding="utf-8")
    assert "live-data-evidence" in text
    assert "workflow_dispatch" in text
    assert "DSP_FMP_API_KEY" in text
    assert "DSP_MARKET_QUOTE_API_KEY" in text
    assert "g2_live_vendor_evidence_drill.py" in text
    assert "g2_provider_configuration_diagnostic.py" in text
    # Must not run automatically on every PR push.
    assert "pull_request:" not in text
