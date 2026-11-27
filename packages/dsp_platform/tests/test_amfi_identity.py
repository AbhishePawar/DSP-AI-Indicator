import pytest

from data_engine.reference_catalog import (
    ReferenceCatalog,
    ReferenceInstrument,
)

from dsp_platform.research_retrieval.amfi_identity import (
    valid_isin,
    reconcile_amfi_nav,
)


@pytest.mark.parametrize(
    "isin",
    [
        "INE009A01021",
        "INE040A01034",
        "INF846K01WO1",
        "INF769K01DM9",
        "INF769K01DK3",
    ],
)
def test_valid_isin(isin):

    assert valid_isin(isin)


@pytest.mark.parametrize(
    "isin",
    [
        "INE009A01022",
        "INF846K01WO2",
        "",
        None,
        "INVALID",
        "ine009a01021",
        "INE009A0102",
        "INE009A010210",
    ],
)
def test_invalid_isin(isin):

    assert not valid_isin(isin)


def catalog():

    return ReferenceCatalog([
        ReferenceInstrument(
            instrument_id="AMFI:135762",
            symbol="135762",
            name="Axis Children's Fund",
            exchange="AMFI",
            category="fund",
            source="amfi_nav_report",
            isins=("INF846K01WO1",),
            plan="Direct Plan",
            option="Growth Option",
        )
    ])


def snapshot(**changes):

    row = {
        "scheme_code": "135762",
        "scheme_name": "Axis Children's Fund",
        "isin_growth_or_payout": "INF846K01WO1",
        "isin_reinvestment": None,
        "plan": "Direct Plan",
        "option": "Growth Option",
        "nav": "31.4008",
        "nav_date": "2026-11-27",
        "freshness": "recent",
    }

    row.update(changes)

    return {
        "source_url": (
            "https://portal.amfiindia.com/spages/NAVAll.txt"
        ),
        "records": {
            "135762": row,
        },
    }


def test_valid_identity_reconciliation():

    result = reconcile_amfi_nav(
        snapshot(), catalog()
    )

    assert result["matched_count"] == 1
    assert result["quarantined_count"] == 0

    assert not result["authorized_for_valuation"]

    assert result["records"]["135762"][
        "isin_checksum_valid"
    ] is True


@pytest.mark.parametrize(
    "changes,reason",
    [
        (
            {"scheme_code": "999999"},
            "scheme_code_mismatch",
        ),
        (
            {"isin_growth_or_payout": None},
            "missing_isin",
        ),
        (
            {"isin_growth_or_payout": "INF846K01WO2"},
            "invalid_isin_checksum",
        ),
        (
            {"isin_growth_or_payout": "INF769K01DM9"},
            "isin_mismatch",
        ),
        (
            {"scheme_name": "Different Fund"},
            "name_mismatch",
        ),
        (
            {"plan": "Regular Plan"},
            "plan_mismatch",
        ),
        (
            {"option": "IDCW Option"},
            "option_mismatch",
        ),
    ],
)
def test_invalid_identity_quarantined(changes, reason):

    result = reconcile_amfi_nav(
        snapshot(**changes),
        catalog(),
    )

    assert result["matched_count"] == 0
    assert result["quarantined_count"] == 1
    assert result["quarantined"]["135762"] == reason


def test_missing_reference():

    result = reconcile_amfi_nav(
        snapshot(),
        ReferenceCatalog([]),
    )

    assert result["quarantined"]["135762"] == (
        "missing_or_ambiguous_identity"
    )


def test_historical_identity_not_classified_as_recent():

    result = reconcile_amfi_nav(
        snapshot(freshness="historical"),
        catalog(),
    )

    assert result["matched_count"] == 1

    assert result["counts"].get(
        "recent_identity_matched", 0
    ) == 0


def test_independent_verification_not_fabricated():

    result = reconcile_amfi_nav(
        snapshot(), catalog()
    )

    assert not result["independent_identity_verified"]

    assert not result["records"]["135762"][
        "independent_identity_verified"
    ]
