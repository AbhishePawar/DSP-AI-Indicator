"""DSP_PUBLIC_DOMAIN must be one bare hostname; www goes in DSP_WWW_REDIRECT_DOMAIN."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "validate_env", _REPO / "scripts" / "validate_env.py"
)
assert _spec and _spec.loader
validate_env = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate_env)


@pytest.mark.parametrize(
    "value", ["dspaiindicator.com", "www.dspaiindicator.com", "localhost", ""]
)
def test_valid_hostnames(value: str) -> None:
    assert validate_env.hostname_error(value) is None


@pytest.mark.parametrize(
    "value",
    [
        "dspaiindicator.com www.dspaiindicator.com",
        "dspaiindicator.com,www.dspaiindicator.com",
        "https://dspaiindicator.com",
        "dspaiindicator.com/app",
        "dspaiindicator.com:443",
        "dspaiindicator",
        "-bad.example.com",
        "bad_label.example.com",
    ],
)
def test_invalid_hostnames(value: str) -> None:
    assert validate_env.hostname_error(value) is not None


def _deploy_precheck(tmp_path: Path, line: str) -> subprocess.CompletedProcess[str]:
    env_file = tmp_path / ".env.production"
    env_file.write_text(f"DSP_ENVIRONMENT=production\n{line}\n", encoding="utf-8")
    script = (_REPO / "scripts" / "deploy_production.sh").read_text(encoding="utf-8")
    start = script.index("# Unquoted values containing spaces")
    end = script.index("# shellcheck disable=SC1090\nset -a")
    snippet = (
        'set -euo pipefail\nENV_FILE="$1"\n' + script[start:end] + "echo PRECHECK_OK\n"
    )
    return subprocess.run(
        ["bash", "-c", snippet, "precheck", str(env_file)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_deploy_refuses_unquoted_space_before_sourcing(tmp_path: Path) -> None:
    out = _deploy_precheck(
        tmp_path, "DSP_PUBLIC_DOMAIN=dspaiindicator.com www.dspaiindicator.com"
    )
    assert out.returncode == 1
    assert "DSP_PUBLIC_DOMAIN" in out.stderr
    assert "PRECHECK_OK" not in out.stdout


@pytest.mark.parametrize(
    "line",
    [
        "DSP_PUBLIC_DOMAIN=dspaiindicator.com",
        "DSP_PUBLIC_DOMAIN=dspaiindicator.com  # primary host",
        'DSP_APP_NAME="DSP AI Indicator"',
        "",
    ],
)
def test_deploy_precheck_allows_valid_lines(tmp_path: Path, line: str) -> None:
    out = _deploy_precheck(tmp_path, line)
    assert out.returncode == 0, out.stderr
    assert "PRECHECK_OK" in out.stdout


def test_caddy_redirects_www_alias_to_public_domain() -> None:
    caddy = (_REPO / "docker" / "Caddyfile").read_text(encoding="utf-8")
    assert "{$DSP_WWW_REDIRECT_DOMAIN:www.localhost} {" in caddy
    assert "redir https://{$DSP_PUBLIC_DOMAIN:localhost}{uri} permanent" in caddy
    compose = (_REPO / "docker" / "docker-compose.production.yml").read_text(
        encoding="utf-8"
    )
    assert (
        "DSP_WWW_REDIRECT_DOMAIN: ${DSP_WWW_REDIRECT_DOMAIN:-www.localhost}" in compose
    )
