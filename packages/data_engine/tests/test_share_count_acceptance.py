"""DSP ShareCount evidence acceptance — CURRENT_OUTSTANDING claims only."""

from __future__ import annotations

from datetime import UTC, date, datetime
from math import inf, nan

import pytest

from data_engine.share_count import (
    ACCEPTANCE_PROVIDER_ID,
    ShareCountAcceptanceError,
    ShareCountBasis,
    ShareCountEvidenceClaim,
    ShareCountUnit,
    accept_current_outstanding_claims,
)

FIXED = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
AS_OF = date(2024, 3, 31)
PUBLISHED = date(2024, 4, 15)


def _claim(**overrides: object) -> ShareCountEvidenceClaim:
    payload: dict[str, object] = {
        "symbol": "TEST",
        "exchange": "NYSE",
        "isin": "US0000000001",
        "shares": 100,
        "unit": "shares",
        "basis": "current_outstanding",
        "as_of": AS_OF,
        "publication_date": PUBLISHED,
        "source_url": "https://www.sec.gov/Archives/edgar/test-outstanding",
        "source_type": "filing",
        "source_tier": "TIER_1_PRIMARY",
        "evidence_reference": "Issued and outstanding shares were 100.",
        "retrieved_at": FIXED,
        "fact_id": "current_outstanding",
        "validation_status": "validated",
    }
    payload.update(overrides)
    return ShareCountEvidenceClaim(**payload)  # type: ignore[arg-type]


class TestShareCountAcceptanceHappyPath:
    def test_validated_current_outstanding_becomes_snapshot(self) -> None:
        snap = accept_current_outstanding_claims(
            [_claim()],
            symbol="TEST",
            exchange="NYSE",
            isin="US0000000001",
        )
        assert snap.shares_value() == pytest.approx(100.0)
        assert snap.basis is ShareCountBasis.CURRENT_OUTSTANDING
        assert snap.unit is ShareCountUnit.SHARES
        assert snap.provenance.provider_id == ACCEPTANCE_PROVIDER_ID
        assert snap.provenance.endpoint == (
            "https://www.sec.gov/Archives/edgar/test-outstanding"
        )
        assert snap.provenance.source_type == "filing"
        meta = snap.provenance.metadata
        assert meta["source_tier"] == "TIER_1_PRIMARY"
        assert meta["source_url"].startswith("https://www.sec.gov/")
        assert "outstanding" in meta["evidence_reference"].lower()
        assert meta["as_of_date"] == "2024-03-31"
        assert meta["publication_date"] == "2024-04-15"
        assert meta["as_of_age_days"] == str((FIXED.date() - AS_OF).days)
        assert snap.as_of is not None
        assert snap.as_of.date() == AS_OF
        assert snap.provenance.retrieved_at == FIXED

    def test_agreeing_tier1_and_tier2_are_unconflicted(self) -> None:
        snap = accept_current_outstanding_claims(
            [
                _claim(source_tier="TIER_2_SECONDARY", fact_id="shares_outstanding"),
                _claim(),
            ],
            symbol="TEST",
            exchange="NYSE",
        )
        assert snap.shares_value() == pytest.approx(100.0)
        assert snap.provenance.metadata["source_tier"] == "TIER_1_PRIMARY"


class TestShareCountAcceptanceNegatives:
    def test_candidate_rejected(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="validated"):
            accept_current_outstanding_claims(
                [_claim(validation_status="candidate")],
                symbol="TEST",
            )

    def test_rejected_status_rejected(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="validated"):
            accept_current_outstanding_claims(
                [_claim(validation_status="rejected")],
                symbol="TEST",
            )

    def test_tier3_rejected(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="Tier 3/4"):
            accept_current_outstanding_claims(
                [_claim(source_tier="TIER_3_DISCOVERY")],
                symbol="TEST",
            )

    def test_tier4_rejected(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="Tier 3/4"):
            accept_current_outstanding_claims(
                [_claim(source_tier="TIER_4_NEWS_CONTEXT")],
                symbol="TEST",
            )

    def test_weighted_average_basis_rejected(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="current_outstanding"):
            accept_current_outstanding_claims(
                [_claim(basis="weighted_average_shares_diluted")],
                symbol="TEST",
            )

    def test_identity_mismatch_rejected(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="identity mismatch"):
            accept_current_outstanding_claims(
                [_claim(symbol="TCS", exchange="NSE")],
                symbol="INFY",
                exchange="NSE",
            )

    def test_nse_bse_substitution_rejected(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="exchange mismatch"):
            accept_current_outstanding_claims(
                [_claim(symbol="TCS", exchange="NSE")],
                symbol="TCS",
                exchange="BSE",
            )

    def test_suffix_symbol_rejected(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="canonical"):
            accept_current_outstanding_claims(
                [_claim(symbol="TCS.NS")],
                symbol="TCS.NS",
            )

    def test_company_name_only_rejected(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="exchange or ISIN"):
            accept_current_outstanding_claims(
                [_claim(exchange=None, isin=None)],
                symbol="TEST",
            )

    def test_missing_as_of_rejected(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="as_of"):
            accept_current_outstanding_claims(
                [_claim(as_of=None)],
                symbol="TEST",
            )

    def test_retrieved_at_datetime_cannot_be_as_of(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="as_of"):
            accept_current_outstanding_claims(
                [_claim(as_of=FIXED)],
                symbol="TEST",
            )

    @pytest.mark.parametrize(
        "shares",
        [0, -1, nan, inf, -inf, "not-a-number"],
    )
    def test_malformed_numerical_values_rejected(self, shares: object) -> None:
        with pytest.raises(ShareCountAcceptanceError):
            accept_current_outstanding_claims(
                [_claim(shares=shares)],
                symbol="TEST",
            )

    def test_currency_unit_rejected(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="shares"):
            accept_current_outstanding_claims(
                [_claim(unit="INR")],
                symbol="TEST",
            )

    def test_percentage_unit_rejected(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="shares"):
            accept_current_outstanding_claims(
                [_claim(unit="%")],
                symbol="TEST",
            )

    def test_millions_unit_not_scaled(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="shares"):
            accept_current_outstanding_claims(
                [_claim(unit="million shares")],
                symbol="TEST",
            )

    def test_excerpt_without_outstanding_rejected(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="outstanding"):
            accept_current_outstanding_claims(
                [_claim(evidence_reference="Equity capital was 100.")],
                symbol="TEST",
            )

    def test_unresolved_value_conflict_rejected(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="conflict"):
            accept_current_outstanding_claims(
                [
                    _claim(shares=100, fact_id="current_outstanding"),
                    _claim(
                        shares=200,
                        fact_id="shares_outstanding",
                        source_url="https://www.sec.gov/Archives/edgar/other",
                    ),
                ],
                symbol="TEST",
            )

    def test_same_value_different_as_of_rejected(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="conflict"):
            accept_current_outstanding_claims(
                [
                    _claim(as_of=date(2024, 3, 31), fact_id="current_outstanding"),
                    _claim(
                        as_of=date(2023, 3, 31),
                        fact_id="shares_outstanding",
                    ),
                ],
                symbol="TEST",
            )

    def test_empty_claims_rejected(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="no admissible"):
            accept_current_outstanding_claims([], symbol="TEST")

    def test_non_claim_object_rejected(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="ShareCountEvidenceClaim"):
            accept_current_outstanding_claims(
                ["The company has 100 outstanding shares"],  # type: ignore[list-item]
                symbol="TEST",
            )
