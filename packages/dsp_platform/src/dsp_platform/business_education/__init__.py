"""Educational Business & Buffett analysis — read-only synthesis.

Does not run valuation or Buffett engines. Does not write valuation_signals.
"""

from __future__ import annotations

from dsp_platform.business_education.models import (
    BUSINESS_EDUCATION_SCHEMA_VERSION,
    UNAVAILABLE_MESSAGE,
    ClaimKind,
)
from dsp_platform.business_education.synthesizer import (
    build_business_education_report,
    business_education_schema,
)

__all__ = [
    "BUSINESS_EDUCATION_SCHEMA_VERSION",
    "UNAVAILABLE_MESSAGE",
    "ClaimKind",
    "build_business_education_report",
    "business_education_schema",
]
