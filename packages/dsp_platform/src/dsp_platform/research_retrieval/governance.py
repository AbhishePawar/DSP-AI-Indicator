"""Central source governance, domain allowlists, and authority boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from data_engine.source_governance import (
    APPROVED_SOURCES,
    MARKET_DATA_PURPOSES,
    MARKET_DATA_SOURCES,
    PRIMARY_SOURCES,
    SECONDARY_SOURCES,
    is_approved_source as is_approved_engine_source,
)
from dsp_platform.research_retrieval.models import EvidenceStatus, SourceTier

__all__ = [
    "GovernanceDecision",
    "RetrievalGovernance",
    "is_approved_host",
    "normalize_source_name",
]

# Authoritative primary regulator and issuer domains
PRIMARY_DOMAIN_SUFFIXES = frozenset(
    {
        "bseindia.com",
        "nseindia.com",
        "sec.gov",
        "camskra.com",
        "cdslindia.com",
    }
)

SECONDARY_DOMAIN_SUFFIXES = frozenset(
    {
        "screener.in",
        "finance.yahoo.com",
    }
)


def normalize_source_name(source: str) -> str:
    """Normalize source identifier to standard uppercase naming."""
    cleaned = source.strip().upper()
    if cleaned in {"BSE", "BSE_INDIA", "BOMBAY_STOCK_EXCHANGE"}:
        return "BSE"
    if cleaned in {"NSE", "NSE_INDIA", "NATIONAL_STOCK_EXCHANGE"}:
        return "NSE"
    if cleaned in {"SEC", "SEC_EDGAR", "EDGAR"}:
        return "SEC"
    if cleaned in {"SCREENER", "SCREENER_IN"}:
        return "SCREENER"
    if cleaned in {"YAHOO", "YAHOO_FINANCE"}:
        return "YAHOO_FINANCE"
    if cleaned in {"UPSTOX", "UPSTOX_GATEWAY"}:
        return "UPSTOX"
    return cleaned


def is_approved_host(url: str) -> tuple[bool, SourceTier]:
    """Check if the URL's hostname matches approved primary or secondary registries."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().strip()
    if not host:
        return False, SourceTier.UNAPPROVED

    # Primary regulator and official domains
    for suffix in PRIMARY_DOMAIN_SUFFIXES:
        if host == suffix or host.endswith(f".{suffix}"):
            return True, SourceTier.PRIMARY

    # Secondary cross-check domains
    for suffix in SECONDARY_DOMAIN_SUFFIXES:
        if host == suffix or host.endswith(f".{suffix}"):
            return True, SourceTier.SECONDARY

    # Official investor relations portals (must be specific subdomain or verified issuer)
    if host.startswith("investors.") or host.startswith("ir."):
        return True, SourceTier.PRIMARY

    return False, SourceTier.UNAPPROVED


@dataclass(frozen=True, slots=True)
class GovernanceDecision:
    source_name: str
    source_tier: SourceTier
    is_approved: bool
    status: EvidenceStatus
    permitted_roles: tuple[str, ...]
    rejection_reason: str | None = None


class RetrievalGovernance:
    """Central authority evaluator for all retrieved financial evidence."""

    def evaluate_source(
        self,
        source: str,
        url: str,
        purpose: str = "fundamental",
        publisher: str = "",
    ) -> GovernanceDecision:
        norm_source = normalize_source_name(source)
        purpose_lower = purpose.strip().lower()

        # 1. Market Data Boundary Check (Upstox)
        if norm_source in MARKET_DATA_SOURCES:
            if purpose_lower not in MARKET_DATA_PURPOSES:
                return GovernanceDecision(
                    source_name=norm_source,
                    source_tier=SourceTier.MARKET_DATA,
                    is_approved=False,
                    status=EvidenceStatus.REJECTED,
                    permitted_roles=tuple(MARKET_DATA_PURPOSES),
                    rejection_reason=(
                        f"Upstox market data cannot serve as authority for '{purpose}'. "
                        "Upstox is strictly licensed for quotes and historical market series."
                    ),
                )
            return GovernanceDecision(
                source_name=norm_source,
                source_tier=SourceTier.MARKET_DATA,
                is_approved=True,
                status=EvidenceStatus.VERIFIED,
                permitted_roles=tuple(MARKET_DATA_PURPOSES),
            )

        # 2. Host and domain authority check
        host_approved, host_tier = is_approved_host(url)

        # 3. Primary Sources
        if norm_source in PRIMARY_SOURCES or norm_source == "SEC":
            if url and not host_approved:
                return GovernanceDecision(
                    source_name=norm_source,
                    source_tier=SourceTier.UNAPPROVED,
                    is_approved=False,
                    status=EvidenceStatus.REJECTED,
                    permitted_roles=(),
                    rejection_reason=f"URL host in '{url}' is not an approved domain for primary source '{norm_source}'",
                )
            if url and host_tier is SourceTier.SECONDARY:
                return GovernanceDecision(
                    source_name=norm_source,
                    source_tier=SourceTier.SECONDARY,
                    is_approved=True,
                    status=EvidenceStatus.UNVERIFIED,
                    permitted_roles=("cross_check", "verification"),
                    rejection_reason=f"Source declared primary '{norm_source}' but URL host is secondary tier",
                )
            return GovernanceDecision(
                source_name=norm_source,
                source_tier=SourceTier.PRIMARY,
                is_approved=True,
                status=EvidenceStatus.VERIFIED,
                permitted_roles=("fundamental", "share_count", "cross_check", "verification"),
            )

        # 4. Secondary Sources
        if norm_source in SECONDARY_SOURCES:
            if url and not host_approved:
                return GovernanceDecision(
                    source_name=norm_source,
                    source_tier=SourceTier.UNAPPROVED,
                    is_approved=False,
                    status=EvidenceStatus.REJECTED,
                    permitted_roles=(),
                    rejection_reason=f"URL host in '{url}' is not an approved domain for secondary source '{norm_source}'",
                )
            if purpose_lower in {"cross_check", "sanity_check", "verification"}:
                return GovernanceDecision(
                    source_name=norm_source,
                    source_tier=SourceTier.SECONDARY,
                    is_approved=True,
                    status=EvidenceStatus.VERIFIED,
                    permitted_roles=("cross_check", "verification"),
                )
            # Secondary sources cannot be sole primary authority
            return GovernanceDecision(
                source_name=norm_source,
                source_tier=SourceTier.SECONDARY,
                is_approved=True,
                status=EvidenceStatus.UNVERIFIED,
                permitted_roles=("cross_check", "verification"),
                rejection_reason="Secondary source cannot act as primary financial authority",
            )

        # 5. Domain-derived classification
        if host_approved and host_tier is SourceTier.PRIMARY:
            return GovernanceDecision(
                source_name=norm_source,
                source_tier=SourceTier.PRIMARY,
                is_approved=True,
                status=EvidenceStatus.VERIFIED,
                permitted_roles=("fundamental", "share_count", "cross_check"),
            )

        # 6. Unapproved sources fail-closed
        return GovernanceDecision(
            source_name=norm_source,
            source_tier=SourceTier.UNAPPROVED,
            is_approved=False,
            status=EvidenceStatus.REJECTED,
            permitted_roles=(),
            rejection_reason=f"Source '{source}' and host are not on the DSP approved source allowlist",
        )
