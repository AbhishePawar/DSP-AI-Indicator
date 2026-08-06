"""Canonical application version resolution (EPIC-011A).

Package versions (e.g. ``production_platform.__version__``) remain independent.
Application / service version is resolved from env or the repo ``VERSION`` file.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Mapping

__all__ = [
    "DEFAULT_APPLICATION_VERSION",
    "normalize_version",
    "resolve_application_version",
    "resolve_service_version",
]

DEFAULT_APPLICATION_VERSION = "1.0.0"


def normalize_version(raw: str | None) -> str | None:
    """Strip whitespace and optional leading ``v``; empty → None."""
    if raw is None:
        return None
    value = raw.strip()
    if not value:
        return None
    if value.lower().startswith("v") and len(value) > 1 and value[1].isdigit():
        value = value[1:]
    return value


@lru_cache(maxsize=1)
def _read_version_file() -> str | None:
    """Locate nearest ``VERSION`` file walking up from this package."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "VERSION"
        if candidate.is_file():
            try:
                text = candidate.read_text(encoding="utf-8").splitlines()
            except OSError:
                return None
            if not text:
                return None
            return normalize_version(text[0])
    return None


def resolve_application_version(
    environ: Mapping[str, str] | None = None,
) -> str:
    """Resolve application version: env → VERSION file → default."""
    env = environ if environ is not None else os.environ
    for key in ("DSP_APP_VERSION", "DSP_SERVICE_VERSION"):
        found = normalize_version(env.get(key))
        if found:
            return found
    file_version = _read_version_file()
    if file_version:
        return file_version
    return DEFAULT_APPLICATION_VERSION


def resolve_service_version(
    environ: Mapping[str, str] | None = None,
) -> str:
    """Alias used by ProductionConfiguration defaults."""
    return resolve_application_version(environ)
