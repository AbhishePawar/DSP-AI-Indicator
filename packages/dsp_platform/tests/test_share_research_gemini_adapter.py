"""SIMPLE-11 — Gemini share-research adapter classification and DSP gates."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from copilot.enums import LanguageModelStatus
from copilot.models import LanguageModelResult

from dsp_platform.share_count_refresh import InstrumentIdentity
from dsp_platform.share_research.engine import ShareResearchEngine
from dsp_platform.share_research.gemini import (
    FixedShareResearchGemini,
    GeminiShareResearchAdapter,
    ShareResearchGeminiError,
    classify_share_research_gemini_failure,
)
from dsp_platform.share_research.models import (
    ShareResearchCheck,
    ShareResearchRequest,
    ShareResearchStatus,
)
from dsp_platform.share_research.store import ShareResearchStore
from dsp_platform.share_research.validation import parse_gemini_payload

_HORIZON = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
_PROVENANCE = ("test.simple11",)


def _identity() -> InstrumentIdentity:
    return InstrumentIdentity(
        symbol="TCS",
        exchange="NSE",
        mic="XNSE",
        isin="INE467B01029",
        issuer="Tata Consultancy Services Limited",
    )


def _result(
    *,
    status: LanguageModelStatus,
    text: str | None = None,
    limitations: tuple[str, ...] = (),
    structured_sections: tuple[str, ...] = (),
) -> LanguageModelResult:
    return LanguageModelResult(
        result_id="simple11",
        status=status,
        provenance=_PROVENANCE,
        narrative_text=text,
        structured_sections=structured_sections,
        limitations=limitations,
        model_label="gemini-2.5-flash",
    )


class _FakeWebResearch:
    def __init__(self, result: LanguageModelResult) -> None:
        self.model_label = "gemini-2.5-flash"
        self._result = result

    def is_configured(self) -> bool:
        return True

    def invoke_web_research(self, request: Any) -> tuple[LanguageModelResult, Any]:
        del request
        return self._result, MagicMock(model_label="gemini-2.5-flash")


def _adapter(result: LanguageModelResult) -> GeminiShareResearchAdapter:
    return GeminiShareResearchAdapter(_FakeWebResearch(result))


def _research(adapter: GeminiShareResearchAdapter) -> Any:
    return adapter.research(
        identity=_identity(),
        stored=None,
        horizon_iso=_HORIZON.date().isoformat(),
        user_prompt="Research TCS outstanding shares.",
    )


def _ok_payload(**overrides: Any) -> dict[str, Any]:
    through = _HORIZON.date().isoformat()
    payload: dict[str, Any] = {
        "STATUS": "CURRENT",
        "COMPANY": "Tata Consultancy Services Limited",
        "TICKER": "TCS",
        "ISIN": "INE467B01029",
        "EXCHANGE": "NSE",
        "MIC": "XNSE",
        "SECURITY_TYPE": "common_equity",
        "OUTSTANDING_SHARES": 3618087518,
        "AS_OF": "2026-06-30",
        "CURRENT_THROUGH": through,
        "NEW_PRIMARY_SOURCE_1": "https://www.tcs.com/investor-relations/investor-faqs",
        "NEW_PRIMARY_SOURCE_2": "https://www.nseindia.com/get-quotes/equity?symbol=TCS",
        "SOURCE_URLS": [
            "https://www.tcs.com/investor-relations/investor-faqs",
            "https://www.nseindia.com/get-quotes/equity?symbol=TCS",
        ],
        "CORPORATE_ACTIONS_FOUND": [
            {
                "description": "Interim Dividend - Rs 12 Per Share",
                "effective_date": "2026-07-15",
            }
        ],
        "EVIDENCE": ["official outstanding disclosure"],
        "CA_COVERAGE_START": "2026-06-30",
        "CA_COVERAGE_END": through,
        "CA_PAGINATION_EXHAUSTED": True,
        "CA_SOURCE_URL": "https://www.nseindia.com/get-quotes/equity?symbol=TCS",
        "CONFIDENCE": "HIGH",
        "UNRESOLVED_ISSUES": [],
    }
    payload.update(overrides)
    return payload


def _engine(tmp_path: Path, gemini: Any) -> ShareResearchEngine:
    return ShareResearchEngine(
        store=ShareResearchStore(tmp_path / "share_research"),
        gemini=gemini,
    )


class TestValidStructuredGeminiResult:
    def test_parse_pass_on_json_object(self) -> None:
        body = '{"STATUS":"REFRESH_REQUIRED","COMPANY":"Tata Consultancy Services Limited","TICKER":"TCS"}'
        got = _research(
            _adapter(_result(status=LanguageModelStatus.COMPLETE, text=body))
        )
        assert got.payload["STATUS"] == "REFRESH_REQUIRED"
        assert got.payload["TICKER"] == "TCS"

    def test_parse_pass_on_fenced_json(self) -> None:
        body = "```json\n{\"STATUS\":\"UNKNOWN\",\"TICKER\":\"TCS\"}\n```"
        got = _research(
            _adapter(_result(status=LanguageModelStatus.COMPLETE, text=body))
        )
        assert got.payload["STATUS"] == "UNKNOWN"


class TestProseWithoutStructuredEvidence:
    def test_reject_as_malformed(self) -> None:
        with pytest.raises(ShareResearchGeminiError) as exc:
            _research(
                _adapter(
                    _result(
                        status=LanguageModelStatus.COMPLETE,
                        text="TCS currently has about 362 crore outstanding shares.",
                    )
                )
            )
        assert exc.value.kind == "malformed"


class TestToolOnlyResult:
    def test_empty_provider_result_is_not_malformed(self) -> None:
        with pytest.raises(ShareResearchGeminiError) as exc:
            _research(
                _adapter(
                    _result(
                        status=LanguageModelStatus.FAILED,
                        limitations=("empty Gemini response",),
                    )
                )
            )
        assert exc.value.kind == "empty"

    def test_engine_maps_empty_to_refresh_required(self, tmp_path: Path) -> None:
        result = _engine(
            tmp_path, FixedShareResearchGemini(kind="empty", message="empty")
        ).research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.status is ShareResearchStatus.REFRESH_REQUIRED
        assert "malformed" not in result.record.reason
        assert result.record.valuation_eligible is False


class TestInvalidSchema:
    def test_non_object_json_is_malformed(self) -> None:
        with pytest.raises(ShareResearchGeminiError) as exc:
            _research(
                _adapter(_result(status=LanguageModelStatus.COMPLETE, text="true"))
            )
        assert exc.value.kind == "malformed"

    def test_object_missing_research_fields_fails_dsp_schema(self, tmp_path: Path) -> None:
        result = _engine(
            tmp_path, FixedShareResearchGemini({"STATUS": "CURRENT"})
        ).research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.status is not ShareResearchStatus.CURRENT
        assert result.record.valuation_eligible is False
        parsed = parse_gemini_payload({"STATUS": "CURRENT"})
        assert parsed is not None


class TestProviderHttpError:
    def test_http_400_is_http_4xx_not_malformed(self) -> None:
        kind = classify_share_research_gemini_failure(
            LanguageModelStatus.FAILED,
            (
                "http_error: HTTPStatusError:400:INVALID_ARGUMENT:"
                "STRUCTURED_OUTPUT_WITH_TOOLS",
            ),
        )
        assert kind == "http_4xx"
        with pytest.raises(ShareResearchGeminiError) as exc:
            _research(
                _adapter(
                    _result(
                        status=LanguageModelStatus.FAILED,
                        limitations=(
                            "http_error: HTTPStatusError:400:INVALID_ARGUMENT:"
                            "STRUCTURED_OUTPUT_WITH_TOOLS",
                        ),
                    )
                )
            )
        assert exc.value.kind == "http_4xx"

    def test_engine_maps_http_4xx_to_refresh_required(self, tmp_path: Path) -> None:
        result = _engine(
            tmp_path, FixedShareResearchGemini(kind="http_4xx", message="Gemini HTTP 4xx")
        ).research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.status is ShareResearchStatus.REFRESH_REQUIRED
        assert result.record.reason == "Gemini research failed (http_4xx)"
        assert result.record.valuation_eligible is False


class TestNonAuthoritativeSources:
    def test_secondary_hosts_are_dsp_rejected(self, tmp_path: Path) -> None:
        payload = _ok_payload(
            NEW_PRIMARY_SOURCE_1="https://www.screener.in/company/TCS/",
            NEW_PRIMARY_SOURCE_2="https://finance.yahoo.com/quote/TCS.NS",
            SOURCE_URLS=[
                "https://www.screener.in/company/TCS/",
                "https://finance.yahoo.com/quote/TCS.NS",
            ],
            CA_SOURCE_URL="https://www.screener.in/company/TCS/",
        )
        result = _engine(tmp_path, FixedShareResearchGemini(payload)).research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.status is not ShareResearchStatus.CURRENT
        assert result.record.cross_check is ShareResearchCheck.FAIL
        assert result.record.valuation_eligible is False


class TestStaleCurrentness:
    def test_valid_primary_evidence_not_through_checkpoint_is_refresh_required(
        self, tmp_path: Path
    ) -> None:
        payload = _ok_payload(
            CURRENT_THROUGH="2026-09-05",
            CA_COVERAGE_END="2026-09-05",
        )
        result = _engine(tmp_path, FixedShareResearchGemini(payload)).research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.status is ShareResearchStatus.REFRESH_REQUIRED
        assert result.record.valuation_eligible is False


class TestIdentityMismatch:
    def test_wrong_isin_is_rejected(self, tmp_path: Path) -> None:
        payload = _ok_payload(ISIN="INE009A01021")
        result = _engine(tmp_path, FixedShareResearchGemini(payload)).research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.status is ShareResearchStatus.INVALID
        assert result.record.identity_check is ShareResearchCheck.FAIL
        assert result.record.valuation_eligible is False


class TestCorporateActionAmbiguity:
    def test_unclassified_acquisition_blocks_currentness(self, tmp_path: Path) -> None:
        payload = _ok_payload(
            CORPORATE_ACTIONS_FOUND=[
                {"description": "Acquisition", "effective_date": "2026-08-24"}
            ]
        )
        result = _engine(tmp_path, FixedShareResearchGemini(payload)).research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.status is not ShareResearchStatus.CURRENT
        assert result.record.corporate_action_check is ShareResearchCheck.UNRESOLVED
        assert result.record.valuation_eligible is False


class TestLiveCurrentFixtureForbidden:
    def test_no_fabricated_live_tcs_current_fixture(self) -> None:
        """Live TCS CURRENT requires primary evidence through 2026-09-07.

        This suite does not include such a fixture.
        """
        source = Path(__file__).read_text(encoding="utf-8")
        assert "promote TCS" not in source.casefold()
