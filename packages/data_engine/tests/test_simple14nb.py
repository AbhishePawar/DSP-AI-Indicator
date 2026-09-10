"""SIMPLE-14N-B — NSE annual-report archive, per-field units, dated CA (MOCK)."""

from __future__ import annotations

from datetime import date

from data_engine.official_research.acquisition import acquire_primary_documents
from data_engine.official_research.annual_report import (
    normalize_financial_year,
    select_annual_documents,
)
from data_engine.official_research.currentness import CapitalEvent
from data_engine.official_research.documents import classify_retrieval_reason
from data_engine.official_research.extraction import (
    extract_labeled_field,
    extract_shares_outstanding,
    nearest_unit_scale,
)
from data_engine.official_research.nse_primary import (
    NseAnnouncementDocument,
    parse_announcement_capital_events,
    parse_annual_report_documents,
)
from data_engine.official_research.orchestrator import ResearchOrchestrator
from data_engine.official_research.models import ResearchRequest
from data_engine.security_master.models import SecurityListing
from dsp_platform.composition.mock_nse_eod import default_master, mock_nse


def _listing(
    ticker: str = "RELIANCE",
    isin: str = "INE002A01018",
    company: str = "Reliance Industries Limited",
) -> SecurityListing:
    return SecurityListing(
        ticker=ticker,
        company_name=company,
        isin=isin,
        exchange="NSE",
        mic="XNSE",
        security_type="equity",
        eligibility=True,
        series="EQ",
    )


class _CaptureHttp:
    def __init__(self, payloads: dict[str, bytes] | None = None) -> None:
        self.payloads = payloads or {}
        self.urls: list[str] = []

    def get_bytes(self, url: str, *, referer: str | None = None) -> bytes:
        _ = referer
        self.urls.append(url)
        if url in self.payloads:
            return self.payloads[url]
        raise LookupError(f"HTTP 404 {url}")


def test_underscore_filename_fy() -> None:
    assert (
        normalize_financial_year(
            "https://nsearchives.nseindia.com/annual_reports/AR_29313_INFY_2025_2026_U.pdf"
        )
        == 2026
    )
    assert (
        normalize_financial_year(
            "SE_Integrated_Annual_Report_2025-26.pdf"
        )
        == 2026
    )


def test_parse_annual_report_archive_json() -> None:
    payload = {
        "data": [
            {
                "companyName": "HDFC Bank Limited",
                "fromYr": "2025",
                "toYr": "2026",
                "submission_type": "New",
                "fileName": "https://nsearchives.nseindia.com/annual_reports/AR_HDFCBANK_2025_2026.pdf",
            }
        ]
    }
    docs = parse_annual_report_documents(payload)
    assert len(docs) == 1
    assert docs[0].kind == "annual_report"
    assert docs[0].source == "nse_annual_reports"
    selected = select_annual_documents(docs, financial_year=2026)
    assert selected
    assert selected[0].url.endswith("AR_HDFCBANK_2025_2026.pdf")
    assert selected[0].financial_year == 2026
    assert selected[0].source == "nse_annual_reports"


def test_nse_annual_reports_preferred_over_letter() -> None:
    announcements = (
        NseAnnouncementDocument(
            title="Shareholders meeting",
            url="https://nsearchives.nseindia.com/corporate/letter.pdf",
            as_of=date(2026, 5, 15),
            kind="other",
        ),
        NseAnnouncementDocument(
            title="Reliance Industries Limited Integrated Annual Report 2025-2026 New",
            url="https://nsearchives.nseindia.com/annual_reports/AR_RELIANCE_2025_2026.pdf",
            as_of=None,
            kind="annual_report",
            source="nse_annual_reports",
        ),
    )
    selected = select_annual_documents(announcements, financial_year=2026, limit=2)
    assert selected[0].url.endswith("AR_RELIANCE_2025_2026.pdf")


def test_per_field_units_skip_early_unlabeled_match() -> None:
    text = (
        "Infosys Limited INE009A01021\n"
        "year ended 31 March 2026\n"
        "consolidated\n"
        "revenue from operations: 1\n"
        "Consolidated Statement of Profit and Loss\n"
        "Rs. crore\n"
        "revenue from operations: 166594\n"
        "MD&A also quotes figures in million\n"
    )
    revenue = extract_labeled_field(text, "revenue")
    assert revenue is not None
    assert revenue.semantic_status == "VERIFIED"
    assert revenue.raw_unit == "crore"
    assert revenue.raw_value == "166594"


def test_statement_heading_required_in_long_mixed_document() -> None:
    text = (
        "Wipro Limited INE075A01022\n"
        "year ended 31 March 2026\n"
        "consolidated and standalone\n"
        "in million\n"
        "revenue from operations: 22\n"
        + ("x\n" * 5000)
        + "Consolidated Statement of Profit and Loss\n"
        "in million\n"
        "revenue from operations: 890860 809648\n"
    )
    revenue = extract_labeled_field(text, "revenue")
    assert revenue is not None
    assert revenue.semantic_status == "VERIFIED"
    assert revenue.raw_value == "890860"


def test_long_document_requires_comparative_statement_columns() -> None:
    text = (
        "Wipro Limited INE075A01022\n"
        "year ended 31 March 2026\n"
        "consolidated\n"
        + ("x\n" * 5000)
        + "Consolidated Statement of Profit and Loss\n"
        "in million\n"
        "revenue from operations: 22\n"
    )
    revenue = extract_labeled_field(text, "revenue")
    assert revenue is None or revenue.semantic_status != "VERIFIED"

    text = (
        "Wipro Limited INE075A01022\n"
        "year ended 31 March 2026\n"
        "consolidated\n"
        + ("x\n" * 5000)
        + "Consolidated Statement of Profit and Loss\n"
        "in million\n"
        "revenue from operations: 890860 809648\n"
    )
    revenue = extract_labeled_field(text, "revenue")
    assert revenue is not None
    assert revenue.semantic_status == "VERIFIED"
    assert revenue.raw_value == "890860"


def test_long_document_conflicting_statement_values_do_not_promote() -> None:
    text = (
        "Wipro Limited INE075A01022\n"
        "year ended 31 March 2026\n"
        "consolidated\n"
        + ("x\n" * 5000)
        + "Consolidated Statement of Profit and Loss\n"
        "in million\n"
        "revenue from operations: 890860 809648\n"
        "notes after the statement still inside the window\n"
        "revenue from operations: 22 20\n"
    )
    revenue = extract_labeled_field(text, "revenue")
    assert revenue is not None
    assert revenue.semantic_status == "CONFLICT"
    assert revenue.value == ""


def test_per_field_units_in_mixed_document() -> None:
    text = (
        "Infosys Limited INE009A01021\n"
        "year ended 31 March 2026\n"
        "Consolidated Statement of Profit and Loss\n"
        "Rs. crore\n"
        "revenue from operations: 166594\n"
        "also mentions USD million in the MD&A narrative\n"
        "Consolidated Balance Sheet\n"
        "in INR million\n"
        "total assets: 15000000\n"
    )
    revenue = extract_labeled_field(text, "revenue")
    assets = extract_labeled_field(text, "total_assets")
    assert revenue is not None
    assert revenue.semantic_status == "VERIFIED"
    assert revenue.raw_unit == "crore"
    assert revenue.value == "1665940000000"
    assert assets is not None
    assert assets.semantic_status == "VERIFIED"
    assert assets.raw_unit == "million"
    assert nearest_unit_scale(text, text.lower().index("revenue from operations"))[1] == "crore"


def test_dated_announcement_ca_not_undated_narrative() -> None:
    payload = [
        {
            "desc": "Post Buyback Public Announcement",
            "an_dt": "26-Jun-2026 18:10:57",
            "attchmntFile": "https://nsearchives.nseindia.com/wipro-buyback.pdf",
        },
        {
            "desc": "Updates",
            "an_dt": "10-Apr-2026 10:00:00",
            "attchmntFile": "https://nsearchives.nseindia.com/other.pdf",
        },
    ]
    events = parse_announcement_capital_events(payload)
    assert any(item.event_type == "buyback" and item.event_date == date(2026, 6, 26) for item in events)
    from data_engine.official_research.extraction import attack_corporate_actions

    undated = attack_corporate_actions("the company completed a buyback in prior years")
    assert undated == ()


def test_wipro_buyback_stales_shares_not_revenue() -> None:
    text = (
        "Wipro Limited INE075A01022\n"
        "consolidated\n"
        "unit: actual\n"
        "year ended 31 March 2026\n"
        "revenue from operations: 890000000000\n"
        "equity shares outstanding: 10488412458\n"
        "as_of: 2026-03-31\n"
    )
    orch = ResearchOrchestrator(
        security_master=default_master(),
        nse_eod=mock_nse(),
        production=False,
    )
    result = orch.research(
        ResearchRequest(
            ticker="WIPRO",
            isin="INE075A01022",
            mic="XNSE",
            fields=("revenue", "shares_outstanding"),
            mode="MOCK",
            document_url="https://www.wipro.com/investors/annual-report.pdf",
        ),
        document_text=text,
        corporate_actions=(CapitalEvent("buyback", date(2026, 6, 26)),),
    )
    revenue = result.evidence_for("revenue")[0]
    shares = result.evidence_for("shares_outstanding")[0]
    assert revenue.status == "VERIFIED"
    assert shares.status == "REFRESH_REQUIRED"
    assert shares.as_of == date(2026, 3, 31)


def test_acquire_uses_nse_annual_archive_for_domain_only() -> None:
    annual = (
        b"Reliance Industries Limited INE002A01018\n"
        b"consolidated\nRs. crore\nyear ended 31 March 2026\n"
        b"revenue from operations: 100000\n"
        b"equity shares outstanding: 6760000000\n"
        b"as_of: 2026-03-31\n"
    )
    docs = parse_annual_report_documents(
        {
            "data": [
                {
                    "companyName": "Reliance Industries Limited",
                    "fromYr": "2025",
                    "toYr": "2026",
                    "fileName": "https://nsearchives.nseindia.com/annual_reports/AR_RELIANCE_2025_2026.pdf",
                }
            ]
        }
    )
    http = _CaptureHttp(
        {
            "https://nsearchives.nseindia.com/annual_reports/AR_RELIANCE_2025_2026.pdf": annual,
        }
    )
    acquired = acquire_primary_documents(
        _listing(),
        transport=http,
        extra_announcements=docs,
        fields=("revenue", "shares_outstanding"),
    )
    assert acquired.selected_url and acquired.selected_url.endswith("AR_RELIANCE_2025_2026.pdf")
    assert acquired.fields["revenue"].semantic_status == "VERIFIED"
    assert extract_shares_outstanding(acquired.sanitized_text).as_of == date(2026, 3, 31)


def test_retrieval_failure_classes() -> None:
    assert classify_retrieval_reason("HTTP 403 for official URL", 403) == "403"
    assert classify_retrieval_reason("HTML instead of PDF") == "html_instead_of_pdf"
    assert classify_retrieval_reason("unapproved redirect to yahoo.com") == "redirect_rejection"
