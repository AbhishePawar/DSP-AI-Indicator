#!/usr/bin/env python3
"""EPIC-P7.4 — Post-restore / DR recovery validation (ops only)."""

from __future__ import annotations

import argparse
import os
import sys
import urllib.error
import urllib.request


def _get(url: str, timeout: float = 10.0) -> tuple[int, str]:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return int(resp.status), body
    except urllib.error.HTTPError as exc:
        return int(exc.code), str(exc)
    except Exception as exc:  # noqa: BLE001 — surface connectivity failures
        return 0, str(exc)


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    mark = "PASS" if passed else "FAIL"
    extra = f" — {detail}" if detail else ""
    print(f"[{mark}] {name}{extra}")
    return passed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api-base",
        default=os.environ.get("DSP_SMOKE_API_BASE_URL", "http://127.0.0.1:8000"),
    )
    args = parser.parse_args(argv)
    base = args.api_base.rstrip("/")
    passed = True

    for path in ("/health/live", "/health/ready", "/health", "/metrics"):
        code, body = _get(f"{base}{path}")
        ok = code == 200
        if path == "/metrics":
            ok = code == 200 and ("dsp_" in body or "HELP" in body or len(body) > 20)
        passed &= _ok(f"GET {path}", ok, f"status={code}")

    # Optional TCP-less URL presence checks (do not invent connectivity).
    if os.environ.get("DSP_DATABASE_URL"):
        passed &= _ok("DSP_DATABASE_URL configured", True, "present")
    else:
        print("[WARN] DSP_DATABASE_URL not set — skipped DB URL check")

    if os.environ.get("DSP_REDIS_URL"):
        passed &= _ok("DSP_REDIS_URL configured", True, "present")
    else:
        print("[WARN] DSP_REDIS_URL not set — skipped Redis URL check")

    print("VALIDATE_RECOVERY", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
