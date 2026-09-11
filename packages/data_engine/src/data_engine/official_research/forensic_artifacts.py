"""Quarantine historical forensic files so they cannot enter VERIFIED_DATASET.

``artifacts/simple14nd_reconstruct.json`` is an earlier full-document pass.
It is STALE / FORENSIC_ONLY / NOT_PROMOTABLE. Focused-page reconstruction
is the authoritative 14N-D evidence.
"""

from __future__ import annotations

from pathlib import Path

__all__ = [
    "STALE_FORENSIC_ARTIFACTS",
    "STALE_REJECTED_CANDIDATES",
    "classify_forensic_artifact",
    "is_promotable_artifact",
    "is_stale_rejected_candidate",
]

STALE_FORENSIC_ARTIFACTS: frozenset[str] = frozenset(
    {
        "artifacts/simple14nd_reconstruct.json",
    }
)

STALE_REJECTED_CANDIDATES: frozenset[tuple[str, str, str]] = frozenset(
    {
        ("TCS", "revenue", "220938"),
        ("ASIANPAINT", "net_income", "33626.82"),
        ("RELIANCE", "total_assets", "21781401950121"),
        ("RELIANCE", "cash", "10145977106502"),
        ("HINDUNILVR", "revenue", "-59"),
    }
)


def _normalize(path: str | Path) -> str:
    text = str(path).replace("\\", "/")
    return text[text.find("artifacts/") :] if "artifacts/" in text else text


def classify_forensic_artifact(path: str | Path) -> dict[str, str | bool]:
    """Label a forensic file. Artifacts never become investment truth."""
    key = _normalize(path)
    if key in STALE_FORENSIC_ARTIFACTS or key.endswith("simple14nd_reconstruct.json"):
        return {
            "status": "STALE",
            "use": "FORENSIC_ONLY",
            "promotable": False,
        }
    if key.startswith("artifacts/"):
        return {
            "status": "FORENSIC_ONLY",
            "use": "FORENSIC_ONLY",
            "promotable": False,
        }
    return {"status": "UNKNOWN", "use": "NOT_EVIDENCE", "promotable": False}


def is_promotable_artifact(path: str | Path) -> bool:
    return bool(classify_forensic_artifact(path)["promotable"])


def is_stale_rejected_candidate(company: str, field: str, raw_value: str) -> bool:
    """True when a stale full-document token must not override focused-page evidence."""
    key = (str(company).strip().upper(), str(field).strip().lower(), str(raw_value).strip())
    return key in STALE_REJECTED_CANDIDATES
