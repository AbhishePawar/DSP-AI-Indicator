"""Sanitize acquisition artifacts. Never persist cookies or secrets."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

_SECRET_KEYS = frozenset(
    {
        "cookie",
        "cookies",
        "set-cookie",
        "authorization",
        "proxy-authorization",
        "x-api-key",
        "api_key",
        "apikey",
        "token",
        "access_token",
        "session",
        "secret",
        "password",
    }
)


def public_json(payload: Mapping[str, Any]) -> dict[str, Any]:
    cleaned = _scrub(dict(payload))
    encoded = json.dumps(cleaned, sort_keys=True, separators=(",", ":"), default=_default)
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    cleaned["artifact_integrity"] = {"sha256": digest}
    return cleaned


def write_artifact(path: Path, payload: Mapping[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = public_json(payload)
    path.write_text(json.dumps(body, indent=2, default=_default) + "\n", encoding="utf-8")
    return path


def _scrub(value: Any) -> Any:
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).strip().lower() in _SECRET_KEYS:
                continue
            out[str(key)] = _scrub(item)
        return out
    if isinstance(value, (list, tuple)):
        return [_scrub(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)
