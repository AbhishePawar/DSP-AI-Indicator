"""DSP-owned Economic Moat presentation contract.

Projects already-computed ResearchPackage moat components into six
canonical public rows plus a one-decimal X/10 display rating.

Does not import ``economic_moat``. Does not call EconomicEngine.
Does not change canonical 0–100 scores. Does not write ratings back
into engines, Business Quality, Buffett, or recommendation.

AI ``score_10`` remains a separate, still-forbidden field.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from dsp_platform.research_report.models import (
    EvidenceRefPublic,
    MoatDimensionPublic,
    empty_ai_narrative,
)

__all__ = [
    "CANONICAL_MOAT_DIMENSIONS",
    "CANONICAL_MOAT_DISPLAY_NAMES",
    "MOAT_PRESENTATION_RATING_POLICY",
    "PRESENTATION_STATUS_ASSESSED",
    "PRESENTATION_STATUS_INSUFFICIENT_DATA",
    "PRESENTATION_STATUS_NOT_IMPLEMENTED",
    "PRESENTATION_STATUS_UNAVAILABLE",
    "canonical_moat_dimensions_for_prompt",
    "format_presentation_rating_10",
    "presentation_rating_from_canonical_score",
    "project_canonical_moat_dimensions",
]

CANONICAL_MOAT_DIMENSIONS: tuple[str, ...] = (
    "brand",
    "network_effects",
    "switching_costs",
    "cost_advantage",
    "intangible_assets",
    "efficient_scale",
)

CANONICAL_MOAT_DISPLAY_NAMES: dict[str, str] = {
    "brand": "Brand",
    "network_effects": "Network Effects",
    "switching_costs": "Switching Costs",
    "cost_advantage": "Cost Advantage",
    "intangible_assets": "Intangible Assets",
    "efficient_scale": "Efficient Scale",
}

MOAT_PRESENTATION_RATING_POLICY = (
    "one_decimal_half_up"  # matches apps/web scoreOutOf10FromExisting toFixed(1)
)

PRESENTATION_STATUS_ASSESSED = "assessed"
PRESENTATION_STATUS_INSUFFICIENT_DATA = "insufficient_data"
PRESENTATION_STATUS_UNAVAILABLE = "unavailable"
PRESENTATION_STATUS_NOT_IMPLEMENTED = "not_implemented"

_EVIDENCE_GAP = (
    "Per-dimension public evidence IDs are not assigned; "
    "citations remain stage:economic_moat."
)


def format_presentation_rating_10(canonical_score_100: float) -> str:
    """Format an assessed 0–100 score as one-decimal ``X.X/10``.

    76 → ``7.6/10``. 75 → ``7.5/10``. 80 → ``8.0/10``.
    Rounding is half-up to one decimal, matching the existing web
    institutional-rating display helper. Never used for missing data.
    """
    tenths = (Decimal(str(canonical_score_100)) / Decimal("10")).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP
    )
    return f"{tenths}/10"


def presentation_rating_from_canonical_score(
    canonical_score_100: float | None,
    *,
    engine_status: str | None,
) -> tuple[str | None, str]:
    """Return ``(presentation_rating_10, presentation_rating_status)``.

    Assessed finite 0–100 → ``X.X/10``. Missing/unsupported → ``None``
    (UI N/A), never ``0/10``.
    """
    status = _normalize_engine_status(engine_status)
    if status == PRESENTATION_STATUS_NOT_IMPLEMENTED:
        return None, PRESENTATION_STATUS_NOT_IMPLEMENTED
    if canonical_score_100 is None:
        if status == PRESENTATION_STATUS_ASSESSED:
            return None, PRESENTATION_STATUS_INSUFFICIENT_DATA
        return None, status
    if isinstance(canonical_score_100, bool):
        return None, PRESENTATION_STATUS_UNAVAILABLE
    value = float(canonical_score_100)
    if not math.isfinite(value) or value < 0.0 or value > 100.0:
        return None, PRESENTATION_STATUS_UNAVAILABLE
    if status != PRESENTATION_STATUS_ASSESSED:
        return None, status
    return format_presentation_rating_10(value), PRESENTATION_STATUS_ASSESSED


def project_canonical_moat_dimensions(
    payload: Mapping[str, Any] | None,
    *,
    section_available: bool,
    section_status: str,
    evidence_refs: tuple[EvidenceRefPublic, ...] = (),
) -> tuple[MoatDimensionPublic, ...]:
    """Copy six canonical dimensions from an EconomicAnalysis payload.

    Extra / invented payload dimensions are ignored. Missing dimensions
    are emitted as unavailable. Aggregate ``overall_moat_score`` is never
    used to fill an individual row.
    """
    by_id = _index_components(payload if section_available else None)
    rows: list[MoatDimensionPublic] = []
    for identifier in CANONICAL_MOAT_DIMENSIONS:
        rows.append(
            _project_one(
                identifier,
                by_id.get(identifier),
                section_available=section_available,
                section_status=section_status,
                evidence_refs=evidence_refs,
            )
        )
    return tuple(rows)


def canonical_moat_dimensions_for_prompt(
    dimensions: Sequence[MoatDimensionPublic],
) -> list[dict[str, Any]]:
    """DSP-owned prompt rows. No AI narrative, no score_10 field."""
    rows: list[dict[str, Any]] = []
    for item in dimensions:
        rows.append(
            {
                "identifier": item.identifier,
                "name": item.name,
                "canonical_score_100": item.canonical_score_100,
                "presentation_rating_10": item.presentation_rating_10,
                "presentation_rating_status": item.presentation_rating_status,
                "engine_status": item.engine_status,
                "limitations": list(item.limitations),
                "allowed_evidence_ids": [ref.id for ref in item.evidence_refs],
                "scores_authoritative": True,
                "presentation_authoritative": True,
            }
        )
    return rows


def _index_components(
    payload: Mapping[str, Any] | None,
) -> dict[str, Mapping[str, Any]]:
    if not isinstance(payload, Mapping):
        return {}
    raw = payload.get("components")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return {}
    indexed: dict[str, Mapping[str, Any]] = {}
    allowed = set(CANONICAL_MOAT_DIMENSIONS)
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        identifier = str(item.get("dimension") or "").strip()
        if identifier not in allowed or identifier in indexed:
            continue
        indexed[identifier] = item
    return indexed


def _project_one(
    identifier: str,
    component: Mapping[str, Any] | None,
    *,
    section_available: bool,
    section_status: str,
    evidence_refs: tuple[EvidenceRefPublic, ...],
) -> MoatDimensionPublic:
    if not section_available or component is None:
        engine_status = (
            PRESENTATION_STATUS_UNAVAILABLE
            if not section_available
            else _section_missing_status(section_status)
        )
        rating, presentation_status = presentation_rating_from_canonical_score(
            None, engine_status=engine_status
        )
        limitations = (
            "Canonical score unavailable for this dimension.",
            _EVIDENCE_GAP,
        )
        return MoatDimensionPublic(
            identifier=identifier,
            name=CANONICAL_MOAT_DISPLAY_NAMES[identifier],
            canonical_score_100=None,
            presentation_rating_10=rating,
            presentation_rating_status=presentation_status,
            engine_status=engine_status,
            evidence_refs=evidence_refs,
            narrative=empty_ai_narrative(),
            durability=empty_ai_narrative(),
            threats=empty_ai_narrative(),
            limitations=limitations,
        )
    score_value, engine_status = _component_score(component)
    rating, presentation_status = presentation_rating_from_canonical_score(
        score_value, engine_status=engine_status
    )
    canonical = (
        float(score_value)
        if presentation_status == PRESENTATION_STATUS_ASSESSED
        and score_value is not None
        else None
    )
    limitations = _component_limitations(component, presentation_status)
    return MoatDimensionPublic(
        identifier=identifier,
        name=CANONICAL_MOAT_DISPLAY_NAMES[identifier],
        canonical_score_100=canonical,
        presentation_rating_10=rating,
        presentation_rating_status=presentation_status,
        engine_status=engine_status,
        evidence_refs=evidence_refs,
        narrative=empty_ai_narrative(),
        durability=empty_ai_narrative(),
        threats=empty_ai_narrative(),
        limitations=limitations,
    )


def _component_score(
    component: Mapping[str, Any],
) -> tuple[float | None, str]:
    raw = component.get("score")
    if isinstance(raw, Mapping):
        status = _normalize_engine_status(raw.get("status"))
        return _as_float(raw.get("value")), status
    value = _as_float(raw)
    if value is None:
        return None, PRESENTATION_STATUS_INSUFFICIENT_DATA
    return value, PRESENTATION_STATUS_ASSESSED


def _component_limitations(
    component: Mapping[str, Any],
    presentation_status: str,
) -> tuple[str, ...]:
    rows: list[str] = []
    evidence = component.get("evidence")
    if isinstance(evidence, Sequence) and not isinstance(evidence, (str, bytes)):
        for item in evidence:
            if not isinstance(item, Mapping):
                continue
            notes = item.get("limitations")
            if isinstance(notes, Sequence) and not isinstance(notes, (str, bytes)):
                for note in notes:
                    text = str(note).strip()
                    if text:
                        rows.append(text)
    if presentation_status != PRESENTATION_STATUS_ASSESSED:
        rows.append("Canonical score unavailable for this dimension.")
    rows.append(_EVIDENCE_GAP)
    return tuple(dict.fromkeys(rows))


def _section_missing_status(section_status: str) -> str:
    status = str(section_status or "").strip()
    if status == PRESENTATION_STATUS_NOT_IMPLEMENTED:
        return PRESENTATION_STATUS_NOT_IMPLEMENTED
    if status == PRESENTATION_STATUS_INSUFFICIENT_DATA:
        return PRESENTATION_STATUS_INSUFFICIENT_DATA
    return PRESENTATION_STATUS_UNAVAILABLE


def _normalize_engine_status(value: object) -> str:
    status = str(value or "").strip()
    if status == PRESENTATION_STATUS_ASSESSED:
        return PRESENTATION_STATUS_ASSESSED
    if status == PRESENTATION_STATUS_INSUFFICIENT_DATA:
        return PRESENTATION_STATUS_INSUFFICIENT_DATA
    if status == PRESENTATION_STATUS_NOT_IMPLEMENTED:
        return PRESENTATION_STATUS_NOT_IMPLEMENTED
    if status == "not_assessed":
        return PRESENTATION_STATUS_INSUFFICIENT_DATA
    return PRESENTATION_STATUS_UNAVAILABLE


def _as_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Mapping):
        return _as_float(value.get("value"))
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number
