"""Façade for educational Business & Buffett analysis (read-only)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.business_education import (
    build_business_education_report,
    business_education_schema,
)

__all__ = [
    "business_education_schema",
    "build_canonical_business_education",
]


def build_canonical_business_education(
    analysis_payload: Mapping[str, Any] | None = None,
    *,
    symbol: str | None = None,
    company: str | None = None,
    exchange: str | None = None,
    sector: str | None = None,
    industry: str | None = None,
    business_type_hint: str | None = None,
) -> dict[str, Any]:
    """Synthesize educational report without mutating quantitative engines."""
    return build_business_education_report(
        analysis_payload,
        symbol=symbol,
        company=company,
        exchange=exchange,
        sector=sector,
        industry=industry,
        business_type_hint=business_type_hint,
    )
