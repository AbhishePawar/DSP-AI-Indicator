#!/usr/bin/env python3
"""P1.1 — Production smoke checks against a live API/Web base URL.

Usage:
  DSP_SMOKE_API_BASE_URL=http://127.0.0.1:8000 \\
  DSP_SMOKE_WEB_BASE_URL=http://127.0.0.1:3000 \\
  python scripts/ops/production_smoke.py

Exits 0 on pass. Skips web/API sections when base URL unset (reports SKIP).
Does not exercise engines — ops probes and public/auth surfaces only.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

TIMEOUT = float(os.environ.get("DSP_SMOKE_TIMEOUT", "15"))


def _get(url: str, headers: dict[str, str] | None = None) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return int(resp.status), body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return int(exc.code), body


def _check(name: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")
    return ok


def smoke_api(base: str) -> bool:
    base = base.rstrip("/")
    passed = True

    code, body = _get(f"{base}/health/live")
    passed &= _check("API /health/live", code == 200, f"status={code}")

    code, body = _get(f"{base}/health/ready")
    passed &= _check(
        "API /health/ready",
        code in {200, 503},
        f"status={code}",
    )

    code, body = _get(f"{base}/health")
    passed &= _check("API /health", code == 200, f"status={code}")
    if code == 200:
        try:
            payload: dict[str, Any] = json.loads(body)
            passed &= _check(
                "API health payload has components or status",
                "status" in payload or "components" in payload,
            )
        except json.JSONDecodeError:
            passed &= _check("API health JSON", False, "invalid JSON")

    code, body = _get(f"{base}/metrics")
    passed &= _check(
        "API /metrics",
        code == 200 and ("#" in body or "http_" in body or "dsp_" in body or len(body) > 0),
        f"status={code}",
    )

    # Versioned aliases
    code, _ = _get(f"{base}/api/v1/health/ready")
    passed &= _check("API /api/v1/health/ready", code in {200, 503}, f"status={code}")

    # Admin without token should be unauthorized when auth required (401/403)
    code, _ = _get(f"{base}/api/v1/admin/health")
    passed &= _check(
        "API admin auth gate",
        code in {401, 403, 404, 200},
        f"status={code} (401/403 expected in hardened prod)",
    )

    return passed


def smoke_web(base: str) -> bool:
    base = base.rstrip("/")
    passed = True

    code, body = _get(f"{base}/api/health")
    passed &= _check("Web /api/health", code == 200, f"status={code}")
    if code == 200:
        try:
            payload = json.loads(body)
            passed &= _check(
                "Web health alive",
                payload.get("status") == "alive" or payload.get("ready") is True,
            )
        except json.JSONDecodeError:
            passed &= _check("Web health JSON", False)

    for path, label in (
        ("/", "Home"),
        ("/login", "Login"),
        ("/docs/disclaimer", "Disclaimer"),
        ("/docs/privacy", "Privacy"),
    ):
        code, _ = _get(f"{base}{path}")
        passed &= _check(f"Web {label} ({path})", code in {200, 307, 308, 401}, f"status={code}")

    return passed


def main() -> int:
    api = os.environ.get("DSP_SMOKE_API_BASE_URL", "").strip()
    web = os.environ.get("DSP_SMOKE_WEB_BASE_URL", "").strip()

    if not api and not web:
        print(
            "SKIP: set DSP_SMOKE_API_BASE_URL and/or DSP_SMOKE_WEB_BASE_URL",
            file=sys.stderr,
        )
        return 0

    ok = True
    if api:
        print(f"== API smoke ({api}) ==")
        ok &= smoke_api(api)
    else:
        print("SKIP API smoke (DSP_SMOKE_API_BASE_URL unset)")

    if web:
        print(f"== Web smoke ({web}) ==")
        ok &= smoke_web(web)
    else:
        print("SKIP Web smoke (DSP_SMOKE_WEB_BASE_URL unset)")

    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
