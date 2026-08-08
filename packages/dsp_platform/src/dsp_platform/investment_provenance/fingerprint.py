"""Deterministic fingerprints for investment provenance (P1-06)."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

__all__ = ["canonical_fingerprint", "canonical_json"]


def canonical_json(payload: Mapping[str, Any] | list[Any] | Any) -> str:
    """Stable JSON serialization — sorted keys, no whitespace."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def canonical_fingerprint(payload: Mapping[str, Any] | list[Any] | Any) -> str:
    """SHA-256 over canonical JSON. Never hash secrets — redact first."""
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
