"""Validate portfolio intelligence results (EPIC-A002)."""

from __future__ import annotations

from dsp_platform.portfolio_intelligence.models import (
    PORTFOLIO_SCHEMA_VERSION,
    PortfolioIntelligenceResult,
)

__all__ = [
    "PortfolioIntelligenceValidationError",
    "validate_portfolio_intelligence",
]


class PortfolioIntelligenceValidationError(ValueError):
    """Portfolio intelligence result failed validation."""


def validate_portfolio_intelligence(result: PortfolioIntelligenceResult) -> None:
    if result.schema_version != PORTFOLIO_SCHEMA_VERSION:
        raise PortfolioIntelligenceValidationError(
            f"unsupported schema_version {result.schema_version!r}"
        )
    if not result.result_id.strip():
        raise PortfolioIntelligenceValidationError("missing result_id")
    if not result.created_at:
        raise PortfolioIntelligenceValidationError("missing created_at")
    if result.portfolio is None and result.watchlist is None:
        raise PortfolioIntelligenceValidationError(
            "portfolio or watchlist is required"
        )
    if result.provenance is None or result.audit is None:
        raise PortfolioIntelligenceValidationError("missing provenance/audit")
    for citation in result.citations:
        if not citation.get("path") or not citation.get("section"):
            raise PortfolioIntelligenceValidationError("citation missing path/section")
