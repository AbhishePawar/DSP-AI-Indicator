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
