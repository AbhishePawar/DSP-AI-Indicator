"""Tests for the Evidence domain contract."""

import pytest

from contracts.domain.evidence import Evidence
from contracts.domain.explanation import Explanation
from contracts.enums import EngineSource
from contracts.exceptions import ContractValidationError


class TestEvidence:
    """Tests for Evidence construction and validation."""

    def test_minimal_evidence(self, source_engine: EngineSource) -> None:
        evidence = Evidence(
            source_engine=source_engine, claim="RSI(14) is overbought."
        )
        assert evidence.value is None
        assert evidence.weight is None

    def test_evidence_with_explanation(self, source_engine: EngineSource) -> None:
        explanation = Explanation(
            source_engine=source_engine, summary="Derived from 14-day RSI."
        )
        evidence = Evidence(
            source_engine=source_engine,
            claim="P/E of 15.2 is below the sector median of 22.4.",
            value=15.2,
            reference="fundamental_engine:pe_ratio",
            explanation=explanation,
            weight=0.7,
        )
        assert evidence.explanation is explanation
        assert evidence.weight == 0.7

    def test_string_value_supported(self, source_engine: EngineSource) -> None:
        evidence = Evidence(
            source_engine=source_engine,
            claim="Sector is Technology.",
            value="Technology",
        )
        assert evidence.value == "Technology"

    def test_empty_claim_raises(self, source_engine: EngineSource) -> None:
        with pytest.raises(ContractValidationError, match="claim"):
            Evidence(source_engine=source_engine, claim="")

    def test_weight_out_of_range_raises(self, source_engine: EngineSource) -> None:
        with pytest.raises(ContractValidationError, match="weight"):
            Evidence(source_engine=source_engine, claim="valid claim", weight=1.2)

    def test_immutable(self, source_engine: EngineSource) -> None:
        evidence = Evidence(source_engine=source_engine, claim="valid claim")
        with pytest.raises(AttributeError):
            evidence.claim = "changed"  # type: ignore[misc]
