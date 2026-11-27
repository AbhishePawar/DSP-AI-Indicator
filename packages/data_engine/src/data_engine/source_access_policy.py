"""Purpose-specific public source acquisition policy.

Registry membership is not permission to fetch documents.
Acquisition permission is not financial evidence verification.
"""

from dataclasses import dataclass
from types import MappingProxyType
from urllib.parse import urlsplit
import re

from data_engine.universal_source_registry import (
    get_source,
    source_matches_url,
)


@dataclass(frozen=True, slots=True)
class SourceAccessDecision:

    permitted: bool
    source_id: str
    capability: str
    reason: str

    authorized_for_valuation: bool = False


# Narrow, server-controlled endpoint policies.
# Additional connectors require individual review.

_ENDPOINTS = MappingProxyType({

    ("SEC_COMPANY_FACTS", "structured_fundamentals"): (
        "data.sec.gov",
        r"/api/xbrl/companyfacts/CIK\d{10}\.json",
    ),

    ("SEC_SUBMISSIONS", "filing_discovery"): (
        "data.sec.gov",
        r"/submissions/CIK\d{10}\.json",
    ),

    ("AMFI", "fund_nav"): (
        "portal.amfiindia.com",
        r"/spages/NAVAll\.txt",
    ),

    ("WORLD_BANK", "economics"): (
        "api.worldbank.org",
        r"/v2/country/[A-Z]{3}/indicator/[A-Z0-9.]+",
    ),
})


def evaluate_source_access(
    source_id,
    capability,
    url,
):

    source_id = str(source_id).strip().upper()
    capability = str(capability).strip().lower()

    def decision(permitted, reason):

        return SourceAccessDecision(
            permitted=permitted,
            source_id=source_id,
            capability=capability,
            reason=reason,
        )

    source = get_source(source_id)

    if source is None:
        return decision(False, "unknown_source")

    if capability not in source.capabilities:
        return decision(False, "unsupported_capability")

    if source.authority == "discovery_only":
        return decision(False, "discovery_only_source")

    if not source_matches_url(source_id, url):
        return decision(False, "source_identity_mismatch")

    policy = _ENDPOINTS.get((source_id, capability))

    if policy is None:
        return decision(False, "access_review_required")

    host, path_pattern = policy

    parsed = urlsplit(url)

    if parsed.hostname != host:
        return decision(False, "endpoint_host_mismatch")

    if not re.fullmatch(path_pattern, parsed.path):
        return decision(False, "endpoint_path_mismatch")

    if parsed.fragment:
        return decision(False, "url_fragment_prohibited")

    if (
        source_id.startswith("SEC_")
        or source_id == "AMFI"
    ) and parsed.query:
        return decision(False, "unexpected_query")

    return decision(True, "reviewed_public_endpoint")
