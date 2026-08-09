"""Canonical evidence-class taxonomy for investment data paths.

Layers must not conflate these labels:

* Gate ``evidence_class`` (G2 / P1-09 / RC1) — release and authenticity gates
* Connector ``source_type`` (licensed_vendor, public_endpoint, …) — provenance
* Financial ``source`` strings — statement period tags only

Public / fixture / memory classes must NEVER clear G2
(``real_live_authenticated_provider``).
CMIE and other future vendors plug in as authenticated providers without
changing Buffett/valuation logic — only adapters + factories.
"""

from __future__ import annotations

from typing import Final

# --- Gate evidence classes (release / authenticity) ---------------------------

REAL_LIVE_AUTHENTICATED_PROVIDER: Final = "real_live_authenticated_provider"
CREDENTIALS_UNAVAILABLE: Final = "credentials_unavailable"
CREDENTIALS_PRESENT_PENDING_LIVE: Final = "credentials_present_pending_live"
LIVE_EXECUTION_FAILED: Final = "live_execution_failed"
MEMORY_SEED_REFUSED_AS_LIVE: Final = "memory_seed_refused_as_live"
TEST_FIXTURE: Final = "test_fixture"

# Development / public-data evidence (never G2-clearing)
PUBLIC_WEB: Final = "public_web"
PUBLIC_FILING: Final = "public_filing"
AUTHENTICATED_PROVIDER: Final = "authenticated_provider"  # non-live generic tag

G2_CLEARING_CLASS: Final = REAL_LIVE_AUTHENTICATED_PROVIDER

NEVER_CLEARS_G2: Final[frozenset[str]] = frozenset(
    {
        CREDENTIALS_UNAVAILABLE,
        CREDENTIALS_PRESENT_PENDING_LIVE,
        LIVE_EXECUTION_FAILED,
        MEMORY_SEED_REFUSED_AS_LIVE,
        TEST_FIXTURE,
        PUBLIC_WEB,
        PUBLIC_FILING,
        "memory",
        "seed",
        "offline",
        "mock",
        AUTHENTICATED_PROVIDER,  # generic tag ≠ live clearance
    }
)

# --- Connector provenance source_type (adapters) ------------------------------

SOURCE_LICENSED_VENDOR: Final = "licensed_vendor"
SOURCE_PUBLIC_ENDPOINT: Final = "public_endpoint"
SOURCE_REGULATORY_FILING: Final = "regulatory_filing"
SOURCE_EXCHANGE_FEED: Final = "exchange_feed"
SOURCE_TEST_FIXTURE: Final = "test_fixture"
SOURCE_MEMORY: Final = "memory"


def may_clear_g2(evidence_class: str | None) -> bool:
    """True only for the sole G2-clearing class (still needs ok+CLEARED)."""
    return (evidence_class or "") == G2_CLEARING_CLASS


def is_development_evidence(evidence_class: str | None) -> bool:
    return (evidence_class or "") in {
        PUBLIC_WEB,
        PUBLIC_FILING,
        TEST_FIXTURE,
        MEMORY_SEED_REFUSED_AS_LIVE,
    }
