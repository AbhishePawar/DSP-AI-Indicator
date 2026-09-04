"""Source-tier assignment for retrieved internet documents.

Discovery/retrieval does not make a URL authoritative. T2 hosts stay
empty until governance registers them. Screener remains T3.
"""

from __future__ import annotations

from dsp_platform.current_outstanding_protocol.web_research import (
    APPROVED_SECONDARY_WEB_HOSTS,
)
from dsp_platform.external_evidence import SourceTier, SourceType
from dsp_platform.primary_source_retrieval import PrimarySourceDocumentType

__all__ = [
    "SCREENER_WEB_HOSTS",
    "TIER_1_WEB_HOSTS",
    "source_tier_for_host",
    "source_type_for_host",
]

# Empty until governance explicitly registers primary filing hosts.
TIER_1_WEB_HOSTS: frozenset[str] = frozenset()
SCREENER_WEB_HOSTS = frozenset({"screener.in", "www.screener.in"})


def source_tier_for_host(
    hostname: str,
    *,
    tier_1_hosts: frozenset[str] | None = None,
) -> SourceTier:
    host = (hostname or "").strip().lower()
    primary = TIER_1_WEB_HOSTS if tier_1_hosts is None else tier_1_hosts
    if host in primary:
        return SourceTier.TIER_1_PRIMARY
    if host in APPROVED_SECONDARY_WEB_HOSTS:
        return SourceTier.TIER_2_SECONDARY
    return SourceTier.TIER_3_DISCOVERY


def source_type_for_host(
    hostname: str,
    *,
    document_type: PrimarySourceDocumentType,
    tier: SourceTier,
) -> SourceType:
    host = (hostname or "").strip().lower()
    if host in SCREENER_WEB_HOSTS:
        return SourceType.COMPANY_WEBSITE
    if tier is SourceTier.TIER_1_PRIMARY and document_type in {
        PrimarySourceDocumentType.ANNUAL_REPORT,
        PrimarySourceDocumentType.AUDITED_FINANCIAL_STATEMENTS,
        PrimarySourceDocumentType.EXCHANGE_FILING,
        PrimarySourceDocumentType.REGULATORY_FILING,
    }:
        return SourceType.FILING
    if tier is SourceTier.TIER_4_NEWS_CONTEXT:
        return SourceType.NEWS
    return SourceType.COMPANY_WEBSITE
