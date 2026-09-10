"""Deterministic MOCK NSE UDiFF + verified book evidence for SIMPLE-14M tests.

Never used as LIVE. Production judge / preload refuse MOCK.
"""

from __future__ import annotations

import json
import zipfile
from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO

from data_engine.official_research.models import EvidenceItem, new_evidence_id
from data_engine.official_research.nse_eod import NseEodService
from data_engine.security_master.catalog import load_default_catalog
from data_engine.security_master.service import SecurityMasterService
from dsp_platform.composition.models import CompositionRequest

NOW = datetime(2026, 9, 9, 8, 20, tzinfo=UTC)
EOD_AS_OF = date(2026, 9, 8)
INFY_ISIN = "INE009A01021"
INFY_TICKER = "INFY"
INFY_EOD = Decimal("1082.00")

UDIFF_CSV = """TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,FininstrmActlXpryDt,StrkPric,OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,LastPric,PrvsClsgPric,UndrlygPric,SttlmPric,OpnIntrst,ChngInOpnIntrst,TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd,SsnId,NewBrdLotQty,Rmks,Rsvd1,Rsvd2,Rsvd3,Rsvd4
2026-09-08,2026-09-08,CM,NSE,STK,1,INE009A01021,INFY,EQ,,,,,INFOSYS LIMITED,1095.00,1095.00,1078.90,1082.00,1082.00,1087.50,,1082.00,,,6269037,0,151673,1,1,,,,
2026-09-08,2026-09-08,CM,NSE,STK,2,INE467B01029,TCS,EQ,,,,,TATA CONSULTANCY SERV LT,2270.00,2274.50,2244.00,2255.50,2255.50,2270.00,,2255.52,,,2148114,0,70112,1,1,,,,
2026-09-08,2026-09-08,CM,NSE,STK,3,INE075A01022,WIPRO,EQ,,,,,WIPRO LTD,172.80,172.90,171.13,171.50,171.50,172.80,,171.50,,,6948945,0,70344,1,1,,,,
2026-09-08,2026-09-08,CM,NSE,STK,4,INE040A01034,HDFCBANK,EQ,,,,,HDFC BANK LTD,707.10,708.90,703.00,703.00,703.00,710.50,,703.00,,,19883515,0,248573,1,1,,,,
2026-09-08,2026-09-08,CM,BSE,STK,500209,INE009A01021,INFY,A,,,,,INFOSYS LTD.,1095.65,1095.65,1079.05,1082.95,1082.95,1087.00,,1082.00,,,162671,0,1,1,1,,,,
"""

_DAILY_REPORTS = {
    "PreviousDay": [
        {
            "fileKey": "CM-UDIFF-BHAVCOPY-CSV",
            "displayName": "CM-UDiFF Common Bhavcopy Final (zip)",
            "fileActlName": "BhavCopy_NSE_CM_0_0_0_20260908_F_0000.csv.zip",
            "filePath": "https://nsearchives.nseindia.com/content/cm/",
            "tradingDate": "08-Sep-2026",
            "fileSize": "199.65 KB",
        }
    ],
    "CurrentDay": [],
}

_MARKET_OPEN = {
    "marketState": [
        {
            "market": "Capital Market",
            "marketStatus": "Open",
            "tradeDate": "09-Sep-2026 13:50",
            "marketStatusMessage": "Normal Market is Open",
        }
    ]
}

FIXTURES = (
    ("INFY", "INE009A01021", Decimal("1082.00")),
    ("TCS", "INE467B01029", Decimal("2255.50")),
    ("WIPRO", "INE075A01022", Decimal("171.50")),
    ("HDFCBANK", "INE040A01034", Decimal("703.00")),
)


def zip_csv(csv_text: str) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("BhavCopy_NSE_CM_0_0_0_20260908_F_0000.csv", csv_text)
    return buffer.getvalue()


class FakeNseHttp:
    def get_bytes(self, url: str, *, referer: str | None = None) -> bytes:
        _ = referer
        if "marketStatus" in url:
            return json.dumps(_MARKET_OPEN).encode()
        if "daily-reports" in url:
            return json.dumps(_DAILY_REPORTS).encode()
        if "BhavCopy_NSE_CM" in url:
            return zip_csv(UDIFF_CSV)
        raise LookupError(f"unexpected URL {url}")


def mock_nse() -> NseEodService:
    return NseEodService(FakeNseHttp(), mode="MOCK")


def default_master() -> SecurityMasterService:
    return SecurityMasterService(load_default_catalog())


def evidence_item(
    *,
    field: str,
    value: str,
    isin: str,
    ticker: str,
    as_of: date,
    status: str = "VERIFIED",
    stage: str = "VERIFIED",
    source: str = "Company IR",
    source_type: str = "company_ir",
    source_url: str = "https://www.infosys.com/investors/annual-report.pdf",
    ca: str = "PASS",
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=new_evidence_id(),
        company="fixture",
        ticker=ticker,
        isin=isin,
        mic="XNSE",
        field=field,
        value=value,
        as_of=as_of,
        retrieved_at=NOW,
        source=source,
        source_type=source_type,
        source_url=source_url,
        document_date=as_of,
        evidence_locator=field,
        currency="INR",
        unit=None,
        statement_basis="consolidated",
        agent="document_extract",
        identity_status="PASS",
        semantic_status="PASS",
        freshness_status="PASS",
        corporate_action_status=ca,
        confidence="high",
        stage=stage,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        mode="MOCK",
        current_through=as_of,
        last_verified_at=NOW,
        period=as_of.isoformat(),
    )


def book_evidence(
    isin: str = INFY_ISIN,
    ticker: str = INFY_TICKER,
    as_of: date = EOD_AS_OF,
) -> tuple[EvidenceItem, ...]:
    return (
        evidence_item(field="equity", value="80000000000", isin=isin, ticker=ticker, as_of=as_of),
        evidence_item(
            field="shares_outstanding",
            value="1000000000",
            isin=isin,
            ticker=ticker,
            as_of=as_of,
        ),
        evidence_item(field="net_income", value="20000000000", isin=isin, ticker=ticker, as_of=as_of),
        evidence_item(field="cfo", value="25000000000", isin=isin, ticker=ticker, as_of=as_of),
        evidence_item(field="capex", value="5000000000", isin=isin, ticker=ticker, as_of=as_of),
        evidence_item(field="revenue", value="50000000000", isin=isin, ticker=ticker, as_of=as_of),
        evidence_item(field="total_assets", value="120000000000", isin=isin, ticker=ticker, as_of=as_of),
        evidence_item(field="total_liabilities", value="40000000000", isin=isin, ticker=ticker, as_of=as_of),
    )


def verified_book_request(**overrides: object) -> CompositionRequest:
    """INFY MOCK EOD + verified book inputs. Client price/FS must not win."""
    payload = dict(
        ticker=INFY_TICKER,
        isin=INFY_ISIN,
        mic="XNSE",
        exchange="NSE",
        company="Infosys Limited",
        research_mode="MOCK",
        nse_eod=mock_nse(),
        security_master=default_master(),
        extra_evidence=book_evidence(),
    )
    payload.update(overrides)
    return CompositionRequest(**payload)  # type: ignore[arg-type]
