"""Post-P1-11 G2-independent hardening — fail-closed integrity (no live creds)."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from data_engine.evidence_classes import (
    NEVER_CLEARS_G2,
    PUBLIC_FILING,
    PUBLIC_WEB,
    REAL_LIVE_AUTHENTICATED_PROVIDER,
    TEST_FIXTURE,
    is_development_evidence,
    may_clear_g2,
)
from dsp_platform.composition.authenticated_valuation import (
    AuthenticatedValuationError,
    ShareCountResearchEvidence,
    _resolve_shares,
    _select_homogeneous_periods,
)


def test_evidence_class_taxonomy_public_never_clears_g2() -> None:
    assert may_clear_g2(REAL_LIVE_AUTHENTICATED_PROVIDER) is True
    assert may_clear_g2(PUBLIC_WEB) is False
    assert may_clear_g2(PUBLIC_FILING) is False
    assert may_clear_g2(TEST_FIXTURE) is False
    assert PUBLIC_WEB in NEVER_CLEARS_G2
    assert is_development_evidence(PUBLIC_WEB) is True
    assert is_development_evidence(REAL_LIVE_AUTHENTICATED_PROVIDER) is False


def test_quarterly_only_statements_refused_for_valuation() -> None:
    q = SimpleNamespace(
        period_type="quarterly",
        period_end=date(2024, 3, 31),
        fiscal_year=2024,
    )
    with pytest.raises(AuthenticatedValuationError, match="quarterly-only"):
        _select_homogeneous_periods((q,))  # type: ignore[arg-type]


def test_annual_periods_preferred_over_quarterly() -> None:
    a = SimpleNamespace(
        period_type="annual",
        period_end=date(2024, 12, 31),
        fiscal_year=2024,
    )
    q = SimpleNamespace(
        period_type="quarterly",
        period_end=date(2024, 3, 31),
        fiscal_year=2024,
    )
    selected = _select_homogeneous_periods((a, q))  # type: ignore[arg-type]
    assert selected == (a,)


def test_shares_not_derived_from_ni_eps() -> None:
    quote = SimpleNamespace(
        shares_outstanding=SimpleNamespace(available=False, value=None)
    )
    latest = SimpleNamespace(
        net_income=SimpleNamespace(available=True, value=1_000_000.0),
        eps_basic=SimpleNamespace(available=True, value=2.0),
        eps_diluted=SimpleNamespace(available=True, value=2.0),
    )
    with pytest.raises(AuthenticatedValuationError, match="shares outstanding"):
        _resolve_shares(quote, latest)  # type: ignore[arg-type]


def test_shares_from_authenticated_quote() -> None:
    quote = SimpleNamespace(
        shares_outstanding=SimpleNamespace(available=True, value=50_000_000.0)
    )
    latest = SimpleNamespace(
        net_income=SimpleNamespace(available=True, value=1.0),
        eps_basic=SimpleNamespace(available=True, value=1.0),
        eps_diluted=SimpleNamespace(available=True, value=1.0),
    )
    assert _resolve_shares(quote, latest) == 50_000_000.0  # type: ignore[arg-type]



def test_researched_shares_require_explicit_valid_evidence() -> None:
    from dsp_platform.composition.authenticated_valuation import _resolve_researched_shares

    evidence = ShareCountResearchEvidence(
        ticker="ABC",
        shares_outstanding=50_000_000,
        source="Issuer annual report",
        evidence_url="https://example.com/annual-report.pdf",
        as_of="2025-03-31",
    )
    shares, provenance = _resolve_researched_shares(
        "ABC", "ABC Ltd", "NSE", lambda *_: evidence
    )
    assert shares == 50_000_000
    assert provenance["evidence_url"] == "https://example.com/annual-report.pdf"
    assert provenance["evidence_class"] == "public_research_unverified_for_g2"
    assert provenance["unit"] == "shares"


@pytest.mark.parametrize(
    "evidence",
    [
        None,
        ShareCountResearchEvidence(
            ticker="OTHER",
            shares_outstanding=50_000_000,
            source="Issuer report",
            evidence_url="https://example.com/report",
        ),
        ShareCountResearchEvidence(
            ticker="ABC",
            shares_outstanding=-1,
            source="Issuer report",
            evidence_url="https://example.com/report",
        ),
        ShareCountResearchEvidence(
            ticker="ABC",
            shares_outstanding=float("nan"),
            source="Issuer report",
            evidence_url="https://example.com/report",
        ),
        ShareCountResearchEvidence(
            ticker="ABC",
            shares_outstanding=50_000_000,
            source="",
            evidence_url="",
        ),
    ],
)
def test_researched_shares_reject_invalid_or_unverifiable_evidence(evidence) -> None:
    from dsp_platform.composition.authenticated_valuation import (
        ShareCountResearchEvidence,
        _resolve_researched_shares,
    )

    with pytest.raises(AuthenticatedValuationError):
        _resolve_researched_shares("ABC", "ABC Ltd", "NSE", lambda *_: evidence)


def test_researched_shares_fail_closed_when_adapter_not_configured() -> None:
    from dsp_platform.composition.authenticated_valuation import _resolve_researched_shares

    with pytest.raises(AuthenticatedValuationError, match="not configured"):
        _resolve_researched_shares("ABC", "ABC Ltd", "NSE", None)

def test_researched_shares_require_valid_unit_and_as_of_date() -> None:
    from dsp_platform.composition.authenticated_valuation import _resolve_researched_shares

    base = {
        "ticker": "ABC",
        "shares_outstanding": 50_000_000,
        "source": "Issuer annual report",
        "evidence_url": "https://example.com/annual-report.pdf",
    }
    invalid_evidence = (
        ShareCountResearchEvidence(**base, as_of="2025-03-31", unit="lots"),
        ShareCountResearchEvidence(**base, as_of=None),
        ShareCountResearchEvidence(**base, as_of="not-a-date"),
        ShareCountResearchEvidence(
            **base, as_of=(date.today().replace(year=date.today().year + 1)).isoformat()
        ),
    )
    for evidence in invalid_evidence:
        with pytest.raises(AuthenticatedValuationError):
            _resolve_researched_shares("ABC", "ABC Ltd", "NSE", lambda *_: evidence)
