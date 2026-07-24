"""Business Quality engine framework tests."""

from __future__ import annotations

import pytest

import business_quality as bq
from business_quality import (
    BUSINESS_QUALITY_VERSION,
    FRAMEWORK_VERSION,
    BusinessQualityEngine,
    BusinessQualityValidationError,
)


class TestEngine:
    def test_shell_analysis(self) -> None:
        engine = BusinessQualityEngine()
        assert engine.version == BUSINESS_QUALITY_VERSION
        assert engine.framework_version == FRAMEWORK_VERSION
        shell = engine.create_shell_analysis(company="Acme", ticker="ACM")
        assert shell.score is None
        assert shell.metadata.company == "Acme"
        assert shell.metadata.ticker == "ACM"
        assert shell.validation.ok
        assert shell.research_disclaimer
        assert shell.to_dict()["score"] is None

    def test_analyze_requires_financial_analysis(self) -> None:
        engine = BusinessQualityEngine()
        with pytest.raises(BusinessQualityValidationError):
            engine.analyze({"anything": True})

    def test_package_exports(self) -> None:
        assert bq.__version__ == "0.3.0"
        assert bq.BUSINESS_QUALITY_VERSION.startswith("0.3.0")
        assert hasattr(bq, "BusinessQualityEngine")
        assert hasattr(bq, "EarningsQualityEngine")
        assert hasattr(bq, "CapitalAllocationEngine")
        assert hasattr(bq, "Score")
        assert hasattr(bq, "validate_required_inputs")
