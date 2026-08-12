"""Content hashing for immutable research intelligence snapshots."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


def content_sha256(payload: Mapping[str, Any]) -> str:
    """Deterministic SHA-256 over a JSON-canonical snapshot payload."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
