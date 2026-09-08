"""SIMPLE-14I Gemini ListModels probe.

Uses GEMINI_API_KEY from the environment. Never prints the key.
Does not call generateContent on SIMPLE-11 blocked models.
"""

from __future__ import annotations

import json
import os
import sys

import httpx

BLOCKED_GENERATE_CONTENT = frozenset(
    {
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.5-flash-lite",
    }
)


def _redact(text: str, secret: str) -> str:
    if not secret:
        return text
    return text.replace(secret, "[REDACTED]")


def main() -> int:
    secret = (os.environ.get("GEMINI_API_KEY") or "").strip()
    print("configured", bool(secret))
    print("secret_len", len(secret))
    print(
        "secret_kind",
        "google_ai_studio_prefix" if secret.startswith("AIza") else "other_or_empty",
    )
    if not secret:
        print("status NOT_CONFIGURED")
        return 2

    endpoints = (
        "https://generativelanguage.googleapis.com/v1beta/models",
        "https://generativelanguage.googleapis.com/v1/models",
    )
    listed: list[str] = []
    for url in endpoints:
        try:
            response = httpx.get(
                url,
                headers={"x-goog-api-key": secret},
                timeout=30.0,
            )
        except httpx.TimeoutException:
            print("LIST", url, "TIMEOUT")
            continue
        except httpx.HTTPError as exc:
            print("LIST", url, "TRANSPORT", type(exc).__name__)
            continue
        print(
            "LIST",
            url.replace("https://generativelanguage.googleapis.com", ""),
            "http",
            response.status_code,
        )
        body = _redact(response.text, secret)
        if response.status_code != 200:
            print("error", body[:600])
            continue
        try:
            payload = response.json()
        except json.JSONDecodeError:
            print("INVALID_RESPONSE")
            continue
        models = payload.get("models") or []
        print("model_count", len(models))
        for model in models:
            name = str(model.get("name") or "").removeprefix("models/")
            methods = model.get("supportedGenerationMethods") or []
            listed.append(name)
            print("MODEL", name, "methods", ",".join(str(m) for m in methods))

    unique = sorted(set(listed))
    candidates = [n for n in unique if n not in BLOCKED_GENERATE_CONTENT]
    print("blocked_known", ",".join(sorted(BLOCKED_GENERATE_CONTENT)))
    print("non_blocked_candidates", ",".join(candidates) if candidates else "NONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
