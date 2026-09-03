"""B1 — ValidatedExternalEvidencePackage structural contract tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from math import inf, nan

import pytest

from dsp_platform.external_evidence import (
    CURRENT_OUTSTANDING_FACT_IDS,
    WEIGHTED_AVERAGE_SHARES_FACT_IDS,
    EvidenceKind,
    EvidenceQuality,
    EvidenceValidationStatus,
    ExternalEvidenceIdentity,
    ExternalEvidenceRecord,
    ExternalEvidenceValidationError,
    QualitativeEvidenceTopic,
    SourceTier,
    SourceType,
    ValidatedExternalEvidencePackage,
    build_validated_external_evidence_package,
    validate_external_evidence_record,
)
from dsp_platform.research_package import (
    PackageSection,
    ResearchPackage,
    attach_validated_external_evidence,
)
from dsp_platform.research_package.models import RESEARCH_PACKAGE_SCHEMA_VERSION
from dsp_platform.research_prompt import build_private_research_prompt

FIXED_RETRIEVED = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
AS_OF = date(2024, 3, 31)
PUBLISHED = date(2024, 4, 15)
SUBJECT = ExternalEvidenceIdentity(
    symbol="TCS",
    exchange="NSE",
    isin="INE467B01029",
    company_name="Tata Consultancy Services",
)


def _identity(**overrides: object) -> ExternalEvidenceIdentity:
    payload = {
        "symbol": SUBJECT.symbol,
        "exchange": SUBJECT.exchange,
        "isin": SUBJECT.isin,
        "company_name": SUBJECT.company_name,
    }
    payload.update(overrides)
    return ExternalEvidenceIdentity(**payload)  # type: ignore[arg-type]


def _numerical(**overrides: object) -> ExternalEvidenceRecord:
    payload: dict[str, object] = {
        "fact_id": "installed_capacity_mw",
        "identity": _identity(),
        "evidence_kind": EvidenceKind.NUMERICAL,
        "numeric_value": 12.5,
        "unit": "MW",
        "as_of": AS_OF,
        "publication_date": PUBLISHED,
        "source_url": "https://www.nseindia.com/corporates/tcs-capacity",
        "source_type": SourceType.EXCHANGE_NOTICE,
        "source_tier": SourceTier.TIER_1_PRIMARY,
        "evidence_reference": "Installed capacity disclosed as 12.5 MW.",
        "retrieved_at": FIXED_RETRIEVED,
        "evidence_quality": EvidenceQuality.HIGH,
        "validation_status": EvidenceValidationStatus.VALIDATED,
        "may_influence_calculation": False,
    }
    payload.update(overrides)
    return ExternalEvidenceRecord(**payload)  # type: ignore[arg-type]


def _qualitative(**overrides: object) -> ExternalEvidenceRecord:
    payload: dict[str, object] = {
        "fact_id": "mgmt_commentary_fy24",
        "identity": _identity(),
        "evidence_kind": EvidenceKind.QUALITATIVE,
        "text_value": "Management reiterated a conservative capital-allocation policy.",
        "topic": QualitativeEvidenceTopic.MANAGEMENT_COMMENTARY,
        "publication_date": PUBLISHED,
        "source_url": "https://www.bseindia.com/xml-data/corpfiling/tcs-transcript",
        "source_type": SourceType.TRANSCRIPT,
        "source_tier": SourceTier.TIER_1_PRIMARY,
        "evidence_reference": "Q&A: capital allocation remains internally funded.",
        "retrieved_at": FIXED_RETRIEVED,
        "evidence_quality": EvidenceQuality.HIGH,
        "validation_status": EvidenceValidationStatus.VALIDATED,
        "may_influence_calculation": False,
    }
    payload.update(overrides)
    return ExternalEvidenceRecord(**payload)  # type: ignore[arg-type]


def _package(*records: ExternalEvidenceRecord) -> ValidatedExternalEvidencePackage:
    return build_validated_external_evidence_package(records, subject=SUBJECT)


def _section(name: str, payload: dict[str, object] | None = None) -> PackageSection:
    return PackageSection(
        name=name,
        status="succeeded",
        available=payload is not None,
        payload=payload,
        provenance={"source": "test"},
    )


def _research_package(
    *, ticker: str = "TCS", exchange: str | None = "NSE"
) -> ResearchPackage:
    sections = {
        name: _section(name, {})
        for name in (
            "market_data",
            "financial_statements",
            "financials",
            "valuation",
            "economic_moat",
            "management_quality",
            "financial_strength",
            "earnings_quality",
            "growth_quality",
            "business_quality",
            "risk",
            "investment_recommendation",
            "investment_committee",
            "buffett_authority",
            "evidence",
            "entry_exit",
        )
    }
    return ResearchPackage(
        schema_version=RESEARCH_PACKAGE_SCHEMA_VERSION,
        methodology_version="test",
        source_pipeline="compose_intelligence",
        identity=_section(
            "identity",
            {
                "ticker": ticker,
                "company": "Tata Consultancy Services",
                "exchange": exchange,
            },
        ),
        **sections,
        limitations=(),
        errors=(),
        pipeline_ok=True,
    )


def test_valid_numerical_evidence() -> None:
    record = _numerical()
    validate_external_evidence_record(record)
    package = _package(record)
    assert package.records[0].numeric_value == 12.5
    assert package.records[0].unit == "MW"
    assert package.records[0].may_influence_calculation is False


def test_valid_qualitative_evidence() -> None:
    record = _qualitative()
    validate_external_evidence_record(record)
    package = _package(record)
    assert package.records[0].topic is QualitativeEvidenceTopic.MANAGEMENT_COMMENTARY
    assert package.records[0].numeric_value is None


def test_immutable_evidence_record() -> None:
    record = _numerical()
    with pytest.raises(FrozenInstanceError):
        record.numeric_value = 99.0  # type: ignore[misc]


def test_immutable_evidence_package() -> None:
    package = _package(_numerical())
    with pytest.raises(FrozenInstanceError):
        package.records = ()  # type: ignore[misc]


def test_missing_fact_id_rejected() -> None:
    record = _numerical(fact_id="")
    with pytest.raises(ExternalEvidenceValidationError, match="fact_id"):
        validate_external_evidence_record(record)


def test_missing_identity_rejected_where_required() -> None:
    with pytest.raises(ExternalEvidenceValidationError, match="identity"):
        validate_external_evidence_record(
            _numerical(identity=_identity(symbol="", exchange=None, isin=None))
        )
    with pytest.raises(ExternalEvidenceValidationError, match="exchange or ISIN"):
        validate_external_evidence_record(
            _numerical(identity=_identity(exchange=None, isin=None))
        )
    with pytest.raises(
        ExternalEvidenceValidationError, match="company name is not sufficient"
    ):
        validate_external_evidence_record(
            _numerical(
                identity=ExternalEvidenceIdentity(
                    symbol="",
                    company_name="Tata Consultancy Services",
                )
            )
        )


def test_invalid_url_rejected() -> None:
    with pytest.raises(ExternalEvidenceValidationError, match="source_url"):
        validate_external_evidence_record(_numerical(source_url=""))
    with pytest.raises(ExternalEvidenceValidationError, match="source_url"):
        validate_external_evidence_record(_numerical(source_url="not-a-url"))
    with pytest.raises(ExternalEvidenceValidationError, match="source_url"):
        validate_external_evidence_record(_numerical(source_url="javascript:alert(1)"))


def test_missing_source_type_rejected() -> None:
    record = _numerical()
    object.__setattr__(record, "source_type", None)
    with pytest.raises(ExternalEvidenceValidationError, match="source_type"):
        validate_external_evidence_record(record)


def test_missing_source_tier_rejected() -> None:
    record = _numerical()
    object.__setattr__(record, "source_tier", None)
    with pytest.raises(ExternalEvidenceValidationError, match="source_tier"):
        validate_external_evidence_record(record)


def test_missing_retrieved_at_rejected() -> None:
    record = _numerical()
    object.__setattr__(record, "retrieved_at", None)
    with pytest.raises(ExternalEvidenceValidationError, match="retrieved_at"):
        validate_external_evidence_record(record)


def test_nan_rejected() -> None:
    with pytest.raises(ExternalEvidenceValidationError, match="finite"):
        validate_external_evidence_record(_numerical(numeric_value=nan))


def test_infinity_rejected() -> None:
    with pytest.raises(ExternalEvidenceValidationError, match="finite"):
        validate_external_evidence_record(_numerical(numeric_value=inf))
    with pytest.raises(ExternalEvidenceValidationError, match="finite"):
        validate_external_evidence_record(_numerical(numeric_value=-inf))


def test_invalid_numeric_value_rejected() -> None:
    with pytest.raises(ExternalEvidenceValidationError, match="numeric"):
        validate_external_evidence_record(_numerical(numeric_value=True))
    record = _numerical()
    object.__setattr__(record, "numeric_value", "12.5")
    with pytest.raises(ExternalEvidenceValidationError, match="finite number"):
        validate_external_evidence_record(record)


def test_missing_unit_rejected_where_required() -> None:
    with pytest.raises(ExternalEvidenceValidationError, match="unit"):
        validate_external_evidence_record(_numerical(unit=None))
    with pytest.raises(ExternalEvidenceValidationError, match="unit"):
        validate_external_evidence_record(_numerical(unit=""))


def test_candidate_evidence_cannot_enter_validated_package() -> None:
    record = _numerical(validation_status=EvidenceValidationStatus.CANDIDATE)
    validate_external_evidence_record(record)
    with pytest.raises(ExternalEvidenceValidationError, match="candidate"):
        _package(record)


def test_rejected_evidence_cannot_enter_validated_package() -> None:
    record = _numerical(validation_status=EvidenceValidationStatus.REJECTED)
    validate_external_evidence_record(record)
    with pytest.raises(ExternalEvidenceValidationError, match="rejected"):
        _package(record)


def test_tier_3_cannot_become_authoritative_automatically() -> None:
    record = _numerical(source_tier=SourceTier.TIER_3_DISCOVERY)
    with pytest.raises(ExternalEvidenceValidationError, match="Tier 3"):
        validate_external_evidence_record(record)
    with pytest.raises(ExternalEvidenceValidationError, match="Tier 3"):
        _package(record)


def test_search_snippet_cannot_become_authoritative() -> None:
    record = _numerical(source_type=SourceType.SEARCH_SNIPPET)
    with pytest.raises(ExternalEvidenceValidationError, match="snippet"):
        validate_external_evidence_record(record)
    with pytest.raises(ExternalEvidenceValidationError, match="snippet"):
        _package(
            _numerical(
                source_type=SourceType.SEARCH_RESULT,
                source_tier=SourceTier.TIER_4_NEWS_CONTEXT,
            )
        )


def test_may_influence_calculation_defaults_false() -> None:
    record = ExternalEvidenceRecord(
        fact_id="installed_capacity_mw",
        identity=_identity(),
        evidence_kind=EvidenceKind.NUMERICAL,
        source_url="https://www.nseindia.com/corporates/tcs-capacity",
        source_type=SourceType.EXCHANGE_NOTICE,
        source_tier=SourceTier.TIER_1_PRIMARY,
        retrieved_at=FIXED_RETRIEVED,
        evidence_quality=EvidenceQuality.HIGH,
        validation_status=EvidenceValidationStatus.VALIDATED,
        evidence_reference="Installed capacity disclosed as 12.5 MW.",
        numeric_value=12.5,
        unit="MW",
        as_of=AS_OF,
        publication_date=PUBLISHED,
    )
    assert record.may_influence_calculation is False
    validate_external_evidence_record(record)
    with pytest.raises(
        ExternalEvidenceValidationError, match="may_influence_calculation"
    ):
        validate_external_evidence_record(_numerical(may_influence_calculation=True))


def test_numerical_evidence_cannot_directly_mutate_dsp_calculations() -> None:
    package = _package(_numerical())
    assert dict(package.canonical_calculation_inputs()) == {}
    dumped = package.to_dict()
    assert dumped["may_influence_calculation"] is False
    assert dumped["calculation_inputs"] == {}
    assert not hasattr(package, "intrinsic_value")
    assert not hasattr(package, "margin_of_safety")
    assert not hasattr(package, "recommendation")


def test_current_outstanding_cannot_be_populated_through_evidence_alone() -> None:
    record = _numerical(
        fact_id="current_outstanding",
        numeric_value=1_000_000.0,
        unit="shares",
    )
    validate_external_evidence_record(record)
    package = _package(record)
    assert record.fact_id in CURRENT_OUTSTANDING_FACT_IDS
    assert dict(package.canonical_calculation_inputs()) == {}
    assert not hasattr(package, "shares")
    assert not hasattr(package, "current_outstanding")
    with pytest.raises(
        ExternalEvidenceValidationError, match="canonical DSP calculation field"
    ):
        validate_external_evidence_record(
            _numerical(
                fact_id="supporting_share_mention",
                claimed_dsp_field="current_outstanding",
                numeric_value=1_000_000.0,
                unit="shares",
            )
        )


def test_weighted_average_shares_cannot_be_treated_as_current_outstanding() -> None:
    assert "weighted_average_shares" in WEIGHTED_AVERAGE_SHARES_FACT_IDS
    with pytest.raises(
        ExternalEvidenceValidationError, match="weighted-average shares"
    ):
        validate_external_evidence_record(
            _numerical(
                fact_id="weighted_average_shares",
                claimed_dsp_field="current_outstanding",
                numeric_value=900_000.0,
                unit="shares",
            )
        )


def test_identity_mismatch_rejected() -> None:
    other = _numerical(identity=_identity(symbol="INFY", isin="INE009A01021"))
    with pytest.raises(ExternalEvidenceValidationError, match="identity mismatch"):
        build_validated_external_evidence_package([other], subject=SUBJECT)
    nse = SUBJECT
    bse = _numerical(identity=_identity(exchange="BSE"))
    with pytest.raises(ExternalEvidenceValidationError, match="NSE/BSE"):
        build_validated_external_evidence_package([bse], subject=nse)
    with pytest.raises(ExternalEvidenceValidationError, match="suffixes"):
        validate_external_evidence_record(_numerical(identity=_identity(symbol="TCS.NS")))


def test_publication_date_and_as_of_remain_distinct() -> None:
    record = _numerical(as_of=AS_OF, publication_date=PUBLISHED)
    assert record.as_of == AS_OF
    assert record.publication_date == PUBLISHED
    assert record.as_of != record.publication_date
    assert record.retrieved_at.date() != record.as_of
    assert record.retrieved_at.date() != record.publication_date


def test_retrieved_at_cannot_substitute_for_as_of() -> None:
    record = _numerical(as_of=None)
    validate_external_evidence_record(record)
    assert record.as_of is None
    assert record.retrieved_at is not None
    package = _package(record)
    assert package.records[0].as_of is None
    assert package.records[0].may_influence_calculation is False
    assert dict(package.canonical_calculation_inputs()) == {}


def test_no_secrets_prompts_or_llm_metadata_in_evidence_objects() -> None:
    package = _package(_numerical(), _qualitative())
    blob = str(package.to_dict()).lower()
    for token in (
        "api_key",
        "prompt",
        "system_prompt",
        "chain_of_thought",
        "provider_id",
        "routing_tier",
        "openai",
        "anthropic",
        "gemini",
        "token_count",
    ):
        assert token not in blob
    for key in package.records[0].to_dict():
        assert key not in {"api_key", "prompt", "provider", "model", "secret"}


def test_research_package_defaults_external_evidence_none() -> None:
    package = _research_package()
    assert package.external_evidence is None
    dumped = package.to_dict()
    assert dumped["external_evidence"] is None


def test_attach_validated_evidence_is_additive_and_prompt_safe() -> None:
    research = _research_package()
    evidence = _package(_qualitative())
    attached = attach_validated_external_evidence(research, evidence)
    assert research.external_evidence is None
    assert attached.external_evidence is evidence
    prompt = build_private_research_prompt(attached)
    assert "validated_external_evidence" in prompt.data_block
    assert "mgmt_commentary_fy24" in prompt.data_block
    assert "supporting_research_context_not_dsp_calculation_input" in prompt.data_block
    assert "ShareCountPort" in prompt.instructions
    with pytest.raises(ExternalEvidenceValidationError, match="identity mismatch"):
        attach_validated_external_evidence(_research_package(ticker="INFY"), evidence)


def test_empty_package_is_valid() -> None:
    package = build_validated_external_evidence_package((), subject=SUBJECT)
    assert package.records == ()
    assert dict(package.canonical_calculation_inputs()) == {}
