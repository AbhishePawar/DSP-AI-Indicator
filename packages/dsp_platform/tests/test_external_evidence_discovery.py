"""B5 — OFF-only external evidence discovery seam tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime

import pytest

from data_engine.share_count import ShareCountAcceptanceError, ShareCountSnapshot
from dsp_platform.canonical_research_ai import CanonicalAIDraft
from dsp_platform.external_evidence import (
    EvidenceValidationStatus,
    ExternalEvidenceIdentity,
    ExternalEvidenceRecord,
    ExternalEvidenceValidationError,
    ValidatedExternalEvidencePackage,
    build_validated_external_evidence_package,
    validate_external_evidence_record,
)
from dsp_platform.external_evidence_discovery import (
    DISCOVERY_NOT_CONFIGURED,
    ExternalEvidenceDiscoveryBlockedError,
    ExternalEvidenceDiscoveryRequest,
    ExternalEvidenceDiscoveryResult,
    ProductionBlockedExternalEvidenceDiscovery,
    validate_discovery_request,
)
from dsp_platform.external_evidence_discovery.testing import (
    FIXTURE_AS_OF,
    FIXTURE_IDENTITY,
    FIXTURE_PUBLICATION_DATE,
    FIXTURE_SHARES,
    FIXTURE_SOURCE_URL,
    TEST_ONLY,
    DeterministicExternalEvidenceDiscovery,
)
from dsp_platform.research_validation.models import CanonicalAIResearchOutput
from dsp_platform.share_count_evidence import (
    accept_share_count_from_validated_evidence,
)

FIXED = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


def _request(**overrides: object) -> ExternalEvidenceDiscoveryRequest:
    payload: dict[str, object] = {
        "identity": FIXTURE_IDENTITY,
        "fact_id": "current_outstanding",
        "retrieved_at": FIXED,
        "as_of_target": None,
    }
    payload.update(overrides)
    return ExternalEvidenceDiscoveryRequest(**payload)  # type: ignore[arg-type]


def _validated_copy(record: ExternalEvidenceRecord) -> ExternalEvidenceRecord:
    return replace(record, validation_status=EvidenceValidationStatus.VALIDATED)


class TestDeterministicDiscovery:
    def test_test_only_flag(self) -> None:
        assert TEST_ONLY is True
        assert DeterministicExternalEvidenceDiscovery.TEST_ONLY is True

    def test_discovers_candidate_current_outstanding(self) -> None:
        result = DeterministicExternalEvidenceDiscovery().discover(_request())
        assert isinstance(result, ExternalEvidenceDiscoveryResult)
        assert result.discovery_status == "candidate"
        assert result.handling.startswith("candidate_discovery")
        assert result.to_dict()["canonical"] is False
        assert result.to_dict()["may_influence_calculation"] is False
        assert len(result.records) == 1
        record = result.records[0]
        assert record.validation_status is EvidenceValidationStatus.CANDIDATE
        assert record.identity == FIXTURE_IDENTITY
        assert record.numeric_value == pytest.approx(FIXTURE_SHARES)
        assert record.unit == "shares"
        assert record.fact_id == "current_outstanding"
        assert record.as_of == FIXTURE_AS_OF
        assert record.publication_date == FIXTURE_PUBLICATION_DATE
        assert record.source_url == FIXTURE_SOURCE_URL
        assert record.source_tier.value == "TIER_1_PRIMARY"
        assert "outstanding" in record.evidence_reference.lower()
        assert "SYNTHETIC" in record.evidence_reference
        assert record.retrieved_at == FIXED
        assert record.as_of != record.retrieved_at
        assert record.may_influence_calculation is False
        validate_external_evidence_record(record)

    def test_retrieved_at_is_not_copied_into_as_of(self) -> None:
        later = datetime(2025, 1, 1, 8, 0, 0, tzinfo=UTC)
        record = DeterministicExternalEvidenceDiscovery().discover(
            _request(retrieved_at=later)
        ).records[0]
        assert record.retrieved_at == later
        assert record.as_of == FIXTURE_AS_OF
        assert record.as_of != later.date()

    def test_identity_mismatch_returns_no_records(self) -> None:
        other = ExternalEvidenceIdentity(
            symbol="INFY",
            exchange="NSE",
            isin="INE009A01021",
        )
        result = DeterministicExternalEvidenceDiscovery().discover(
            _request(identity=other)
        )
        assert result.records == ()

    def test_nse_bse_are_not_substituted(self) -> None:
        nse = ExternalEvidenceIdentity(
            symbol="DSPX",
            exchange="NSE",
            isin="DSPX00000001",
        )
        result = DeterministicExternalEvidenceDiscovery().discover(
            _request(identity=nse)
        )
        assert result.records == ()

    def test_suffix_symbol_rejected(self) -> None:
        with pytest.raises(ExternalEvidenceValidationError, match="suffix"):
            DeterministicExternalEvidenceDiscovery().discover(
                _request(
                    identity=ExternalEvidenceIdentity(
                        symbol="DSPX.NS",
                        exchange="TESTEX",
                    )
                )
            )

    def test_company_name_only_rejected(self) -> None:
        with pytest.raises(ExternalEvidenceValidationError, match="exchange or ISIN"):
            validate_discovery_request(
                _request(
                    identity=ExternalEvidenceIdentity(
                        symbol="DSPX",
                        company_name="DSP Test Synthetic Co",
                    )
                )
            )

    def test_does_not_infer_from_weighted_average_or_eps(self) -> None:
        port = DeterministicExternalEvidenceDiscovery()
        for fact_id in (
            "weighted_average_shares_diluted",
            "equity_capital",
            "eps",
            "market_cap",
            "volume",
            "open_interest",
        ):
            result = port.discover(_request(fact_id=fact_id))
            assert result.records == (), fact_id

    def test_as_of_target_mismatch_returns_empty_not_invented(self) -> None:
        result = DeterministicExternalEvidenceDiscovery().discover(
            _request(as_of_target=date(2020, 1, 1))
        )
        assert result.records == ()

    def test_production_blocked_does_not_use_fixture(self) -> None:
        with pytest.raises(
            ExternalEvidenceDiscoveryBlockedError, match=DISCOVERY_NOT_CONFIGURED
        ) as exc:
            ProductionBlockedExternalEvidenceDiscovery().discover(_request())
        assert exc.value.discovery_state == DISCOVERY_NOT_CONFIGURED


class TestDiscoveryCannotBypassBoundaries:
    def test_candidate_cannot_enter_validated_package(self) -> None:
        record = DeterministicExternalEvidenceDiscovery().discover(
            _request()
        ).records[0]
        validate_external_evidence_record(record)
        with pytest.raises(ExternalEvidenceValidationError, match="candidate"):
            build_validated_external_evidence_package(
                [record], subject=FIXTURE_IDENTITY
            )

    def test_candidate_cannot_become_sharecount_snapshot(self) -> None:
        result = DeterministicExternalEvidenceDiscovery().discover(_request())
        with pytest.raises(ShareCountAcceptanceError, match="AI narrative"):
            accept_share_count_from_validated_evidence(result, symbol="DSPX")
        with pytest.raises(ShareCountAcceptanceError, match="AI narrative"):
            accept_share_count_from_validated_evidence(
                result.records[0], symbol="DSPX"
            )
        assert not isinstance(result, ShareCountSnapshot)
        assert not isinstance(result.records[0], ShareCountSnapshot)

    def test_ai_output_is_not_discovery_authority(self) -> None:
        draft = CanonicalAIDraft(
            output=CanonicalAIResearchOutput(
                executive_summary="Outstanding shares appear to be 123456789.",
            )
        )
        with pytest.raises(ShareCountAcceptanceError, match="AI narrative"):
            accept_share_count_from_validated_evidence(draft, symbol="DSPX")

    def test_explicit_b1_validation_then_package_then_b4(self) -> None:
        candidate = DeterministicExternalEvidenceDiscovery().discover(
            _request()
        ).records[0]
        validate_external_evidence_record(candidate)
        validated = _validated_copy(candidate)
        package = build_validated_external_evidence_package(
            [validated], subject=FIXTURE_IDENTITY
        )
        assert isinstance(package, ValidatedExternalEvidencePackage)
        assert package.canonical_calculation_inputs() == {}
        snap = accept_share_count_from_validated_evidence(
            package,
            symbol="DSPX",
            exchange="TESTEX",
            isin="DSPX00000001",
        )
        assert isinstance(snap, ShareCountSnapshot)
        assert snap.shares_value() == pytest.approx(FIXTURE_SHARES)
        assert snap.provenance.endpoint == FIXTURE_SOURCE_URL
        assert snap.provenance.metadata["as_of_date"] == "2024-03-31"

    def test_discovery_result_is_not_valuation_or_recommendation_input(self) -> None:
        result = DeterministicExternalEvidenceDiscovery().discover(_request())
        payload = result.to_dict()
        assert "intrinsic_value" not in payload
        assert "margin_of_safety" not in payload
        assert "recommendation" not in payload
        assert payload["may_influence_calculation"] is False
        for record in result.records:
            assert record.may_influence_calculation is False
            blob = str(record.to_dict())
            assert "api_key" not in blob
            assert "bearer" not in blob
            assert "system_prompt" not in blob
