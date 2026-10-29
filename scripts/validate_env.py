#!/usr/bin/env python3
"""Validate environment variables for DSP deployments (P1.1 production hardening)."""

from __future__ import annotations

import os
import sys

FORBIDDEN_JWT = {
    "dev-only-change-me",
    "CHANGE_ME_USE_SECRET_MANAGER",
    "change-me",
    "secret",
}

_HOST_LABEL_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789-")


def hostname_error(value: str | None) -> str | None:
    """Return why ``value`` is not a single bare hostname, or None if valid/empty.

    DSP_PUBLIC_DOMAIN feeds the Caddy site address and the deploy script's
    ``https://${DSP_PUBLIC_DOMAIN}/api/health`` smoke URL, so it must be exactly
    one hostname: no scheme, path, port, spaces or comma-separated list.
    """
    raw = (value or "").strip()
    if not raw:
        return None
    if any(ch.isspace() for ch in raw) or "," in raw:
        return (
            "must be a single hostname (no spaces or lists); put the www "
            "alias in DSP_WWW_REDIRECT_DOMAIN"
        )
    if "://" in raw or "/" in raw or ":" in raw:
        return "must be a hostname only (no scheme, path or port)"
    labels = raw.lower().split(".")
    if raw.lower() != "localhost" and len(labels) < 2:
        return "must be a fully qualified hostname"
    for label in labels:
        if (
            not label
            or len(label) > 63
            or label.startswith("-")
            or label.endswith("-")
            or set(label) - _HOST_LABEL_CHARS
        ):
            return "contains an invalid hostname label"
    return None


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
            "DSP_REQUIRE_ADMIN_AUTH",
            "DSP_RATE_LIMIT_ENABLED",
            "DSP_HSTS_ENABLED",
            "DSP_INDIA_TIMEZONE",
            "DSP_INDIA_CURRENCY",
            "DSP_APP_VERSION",
            "DSP_DATABASE_URL",
            "DSP_PUBLIC_DOMAIN",
        ],
        "recommended": [
            "BUILD_TIMESTAMP",
            "GIT_SHA",
            "DSP_REDIS_URL",
            "DSP_REGION",
            "DSP_BACKUP_DIR",
            "DSP_TEMP_DIR",
            "DEFAULT_AI_PROVIDER",
            "NEXT_PUBLIC_API_BASE_URL",
            "DSP_API_DOMAIN",
            "DSP_WWW_REDIRECT_DOMAIN",
            "DSP_ACME_EMAIL",
            "DSP_PLATFORM_VERSION",
        ],
        "truthy": [
            "DSP_ENABLE_SECURITY",
            "DSP_REQUIRE_ADMIN_AUTH",
            "DSP_RATE_LIMIT_ENABLED",
            "DSP_HSTS_ENABLED",
        ],
    },
}


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if argv and argv[0].startswith("--profile"):
        # Accept both "--profile NAME" and "--profile=NAME" as well as positional NAME.
        flag = argv.pop(0)
        if "=" in flag:
            argv.insert(0, flag.split("=", 1)[1])
        elif not argv:
            print("--profile requires a value", file=sys.stderr)
            return 1
    profile = (
        argv[0].lower()
        if argv
        else os.environ.get("DSP_ENVIRONMENT", "development").lower()
    )
    if profile not in PROFILES:
        print(f"Unknown profile={profile!r}", file=sys.stderr)
        return 1

    spec = PROFILES[profile]
    missing = [k for k in spec["required"] if not os.environ.get(k)]
    if missing:
        print(
            f"[{profile}] Missing required variables: {', '.join(missing)}",
            file=sys.stderr,
        )
        return 1

    if profile == "production":
        env_name = (os.environ.get("DSP_ENVIRONMENT") or "").lower()
        if env_name != "production":
            print(
                "[production] DSP_ENVIRONMENT must be 'production'",
                file=sys.stderr,
            )
            return 1

        jwt = os.environ.get("DSP_JWT_SECRET", "")
        if jwt in FORBIDDEN_JWT or len(jwt) < 24:
            print(
                "[production] DSP_JWT_SECRET must be a strong secret "
                "(≥24 chars, not a template/default)",
                file=sys.stderr,
            )
            return 1

        for key in spec.get("truthy", []):
            if not _is_truthy(os.environ.get(key)):
                print(
                    f"[production] {key} must be enabled (true)",
                    file=sys.stderr,
                )
                return 1

        cors = os.environ.get("DSP_CORS_ORIGINS", "")
        if "http://" in cors and "https://" not in cors:
            print(
                "[production] DSP_CORS_ORIGINS should use HTTPS origins",
                file=sys.stderr,
            )
            return 1

        domain = (os.environ.get("DSP_PUBLIC_DOMAIN") or "").strip()
        if not domain or domain in {"localhost", "your-domain.example"}:
            print(
                "[production] Warning: DSP_PUBLIC_DOMAIN looks like a placeholder "
                f"({domain!r}) — set a real public hostname before launch",
            )
        for var_name in ("DSP_PUBLIC_DOMAIN", "DSP_WWW_REDIRECT_DOMAIN"):
            host_error = hostname_error(os.environ.get(var_name))
            if host_error:
                print(f"[production] {var_name} {host_error}", file=sys.stderr)
                return 1
        hosts = {
            name: (os.environ.get(name) or "").strip().lower()
            for name in (
                "DSP_PUBLIC_DOMAIN",
                "DSP_WWW_REDIRECT_DOMAIN",
                "DSP_API_DOMAIN",
            )
        }
        named = [(n, h) for n, h in hosts.items() if h]
        for i, (name_a, host_a) in enumerate(named):
            for name_b, host_b in named[i + 1 :]:
                if host_a == host_b:
                    # Caddy refuses duplicate site blocks ("ambiguous site
                    # definition"), so the proxy would never start.
                    print(
                        f"[production] {name_a} and {name_b} must be different "
                        f"hostnames (both are {host_a!r})",
                        file=sys.stderr,
                    )
                    return 1
        if domain.startswith("http://") or domain.startswith("https://"):
            print(
                "[production] DSP_PUBLIC_DOMAIN must be a hostname only " "(no scheme)",
                file=sys.stderr,
            )
            return 1

        db_url = os.environ.get("DSP_DATABASE_URL", "")
        if not db_url.startswith(("postgresql://", "postgres://")):
            print(
                "[production] DSP_DATABASE_URL must be a postgresql:// URL",
                file=sys.stderr,
            )
            return 1

        tz = os.environ.get("DSP_INDIA_TIMEZONE", "")
        if tz and tz != "Asia/Kolkata":
            print(
                f"[production] Warning: DSP_INDIA_TIMEZONE={tz!r} "
                "(expected Asia/Kolkata for India posture)",
            )

        seed = os.environ.get("DSP_SEED_ADMIN_PASSWORD", "")
        if seed and (
            seed.startswith("CHANGE_ME") or seed in {"admin", "password", "dsp"}
        ):
            print(
                "[production] DSP_SEED_ADMIN_PASSWORD looks like a template "
                "or weak password",
                file=sys.stderr,
            )
            return 1

        pg_pass = os.environ.get("POSTGRES_PASSWORD", "")
        if pg_pass and (
            pg_pass.startswith("CHANGE_ME") or pg_pass in {"dsp", "password"}
        ):
            print(
                "[production] POSTGRES_PASSWORD looks like a template "
                "or weak password",
                file=sys.stderr,
            )
            return 1

    absent = [k for k in spec["recommended"] if not os.environ.get(k)]
    if absent:
        print(f"[{profile}] Recommended variables not set: {', '.join(absent)}")

    print(f"[{profile}] Environment validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
