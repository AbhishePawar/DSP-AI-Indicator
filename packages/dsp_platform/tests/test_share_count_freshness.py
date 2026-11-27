from datetime import date, timedelta

import pytest

from data_engine.share_count import (
    ShareCount,
    is_share_count_current,
    resolve_verified_share_count,
)

from dsp_platform.research_retrieval.share_count_retriever import (
    resolve_share_count_from_evidence,
)


TODAY = date(2026, 11, 27)


def candidate(age, shares=1000, source="NSE", purpose="fundamental"):
    return ShareCount(
        ticker="TCS",
        shares=shares,
        as_of=TODAY - timedelta(days=age),
        source=source,
        verified=True,
        purpose=purpose,
    )


@pytest.mark.parametrize("age", [0, 1, 30, 90, 120])
def test_current_share_count(age):
    assert is_share_count_current(
        candidate(age),
        reference_date=TODAY,
    )


@pytest.mark.parametrize("age", [-1, -30, 121, 365, 1000])
def test_invalid_or_stale_share_count(age):
    assert not is_share_count_current(
        candidate(age),
        reference_date=TODAY,
    )


def test_stale_primary_not_authoritative():
    assert resolve_verified_share_count(
        "TCS",
        [candidate(121)],
        reference_date=TODAY,
    ) is None


def test_future_primary_not_authoritative():
    assert resolve_verified_share_count(
        "TCS",
        [candidate(-1)],
        reference_date=TODAY,
    ) is None


def test_stale_conflict_does_not_block_current_count():
    fresh = candidate(10, 1000)
    stale = candidate(150, 500, source="BSE")

    assert resolve_verified_share_count(
        "TCS",
        [fresh, stale],
        reference_date=TODAY,
    ) == fresh


def test_current_conflict_fails_closed():
    with pytest.raises(ValueError, match="disagree"):
        resolve_verified_share_count(
            "TCS",
            [
                candidate(10, 1000),
                candidate(10, 500, source="BSE"),
            ],
            reference_date=TODAY,
        )


def test_stale_secondary_not_reported_as_cross_checked():
    result = resolve_share_count_from_evidence(
        "TCS",
        [
            candidate(10),
            candidate(
                150,
                source="SCREENER",
                purpose="cross_check",
            ),
        ],
        reference_date=TODAY,
    )

    assert result is not None
    assert result.verified
    assert not result.cross_checked
    assert not result.secondary_sources


def test_current_secondary_cross_check():
    result = resolve_share_count_from_evidence(
        "TCS",
        [
            candidate(10),
            candidate(
                10,
                source="SCREENER",
                purpose="cross_check",
            ),
        ],
        reference_date=TODAY,
    )

    assert result is not None
    assert result.verified
    assert result.cross_checked


def test_research_resolver_rejects_stale_primary():
    assert resolve_share_count_from_evidence(
        "TCS",
        [candidate(121)],
        reference_date=TODAY,
    ) is None


def test_configurable_freshness():
    assert not is_share_count_current(
        candidate(31),
        reference_date=TODAY,
        max_age_days=30,
    )


@pytest.mark.parametrize("invalid", [-1, 1.5, True])
def test_invalid_freshness_configuration(invalid):
    with pytest.raises(ValueError):
        resolve_verified_share_count(
            "TCS",
            [],
            reference_date=TODAY,
            max_age_days=invalid,
        )
