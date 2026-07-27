#!/usr/bin/env python3
"""Validate environment variables for DSP RC1 deployments."""

from __future__ import annotations

import os
import sys

PROFILES = {
    "development": {
        "required": [],
        "recommended": ["NEXT_PUBLIC_API_BASE_URL"],
    },
    "staging": {
        "required": ["DSP_ENVIRONMENT", "DSP_JWT_SECRET", "DSP_CORS_ORIGINS"],
        "recommended": ["DSP_APP_VERSION", "BUILD_TIMESTAMP", "GIT_SHA"],
    },
    "production": {
        "required": [
            "DSP_ENVIRONMENT",
            "DSP_JWT_SECRET",
            "DSP_CORS_ORIGINS",
            "DSP_ENABLE_SECURITY",
        ],
        "recommended": [
            "DSP_APP_VERSION",
            "BUILD_TIMESTAMP",
            "GIT_SHA",
            "OPENAI_API_KEY",
            "DEFAULT_AI_PROVIDER",
        ],
    },
}


def main() -> int:
    profile = os.environ.get("DSP_ENVIRONMENT", "development").lower()
    if profile not in PROFILES:
        print(f"Unknown DSP_ENVIRONMENT={profile!r}", file=sys.stderr)
        return 1

    spec = PROFILES[profile]
    missing = [k for k in spec["required"] if not os.environ.get(k)]
    if missing:
        print(f"[{profile}] Missing required variables: {', '.join(missing)}", file=sys.stderr)
        return 1

    absent = [k for k in spec["recommended"] if not os.environ.get(k)]
    if absent:
        print(f"[{profile}] Recommended variables not set: {', '.join(absent)}")

    if profile == "production" and os.environ.get("DSP_JWT_SECRET") == "dev-only-change-me":
        print("[production] DSP_JWT_SECRET must not use the development default", file=sys.stderr)
        return 1

    print(f"[{profile}] Environment validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
