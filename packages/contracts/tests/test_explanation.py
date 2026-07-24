"""Tests for the Explanation domain contract."""

from datetime import datetime

import pytest

from contracts.domain.explanation import Explanation
from contracts.enums import EngineSource
from contracts.exceptions import ContractValidationError


class TestExplanation:
    """Tests for Explanation construction and validation."""

    def test_minimal_explanation(self, source_engine: EngineSource) -> None:
        explanation = Explanation(
            source_engine=source_engine, summary="RSI(14) is overbought."
        )
        assert explanation.detail is None
        assert explanation.confidence is None
        assert explanation.inputs_used == ()

    def test_full_explanation(
        self, source_engine: EngineSource, utc_now: datetime
    ) -> None:
        explanation = Explanation(
            source_engine=source_engine,
            summary="RSI(14) = 72.4 indicates an overbought condition.",
            inputs_used=["close_price", "period=14"],
            detail="Computed via Wilder's smoothing method over 14 periods.",
            confidence=0.8,
            generated_at=utc_now,
        )
        assert explanation.inputs_used == ("close_price", "period=14")
        assert explanation.confidence == 0.8

    def test_empty_summary_raises(self, source_engine: EngineSource) -> None:
        with pytest.raises(ContractValidationError, match="summary"):
            Explanation(source_engine=source_engine, summary="   ")

    def test_confidence_out_of_range_raises(self, source_engine: EngineSource) -> None:
        with pytest.raises(ContractValidationError, match="confidence"):
            Explanation(source_engine=source_engine, summary="valid", confidence=1.5)

    def test_naive_generated_at_raises(self, source_engine: EngineSource) -> None:
        with pytest.raises(ContractValidationError, match="timezone-aware"):
            Explanation(
                source_engine=source_engine,
                summary="valid",
                generated_at=datetime(2026, 1, 1),
            )

    def test_immutable(self, source_engine: EngineSource) -> None:
        explanation = Explanation(source_engine=source_engine, summary="valid")
        with pytest.raises(AttributeError):
            explanation.summary = "changed"  # type: ignore[misc]
