"""SIMPLE-15 — controlled research mesh. Issuers are fixtures, not workflows."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from statistics import median

from data_engine.official_research.agent_port import ResearchContext
from data_engine.official_research.agents import GeminiFindAgent, UnavailableResearchPort
from data_engine.official_research.evidence_identity import dedupe_evidence, evidence_fingerprint
from data_engine.official_research.judge import EvidenceJudge
from data_engine.official_research.models import EvidenceItem, ResearchClaim, ResearchRequest, new_evidence_id
from data_engine.official_research.nse_mcp import NSE_MCP_COMMERCIAL_STATUS
from data_engine.official_research.openai_nse_agent import OpenAINseMcpAgent, nse_remote_mcp_tools
from data_engine.official_research.provider_router import (
    RouterInputs,
    count_independent_agents,
    route_research_roles,
    select_research_agent,
)
from data_engine.official_research.research_failures import (
    classify_openai_failure,
    is_transport_failure,
)
from data_engine.official_research.research_mesh import run_research_mesh
from data_engine.official_research.research_plan import build_research_plan
from data_engine.official_research.research_trace import MESH_STEPS
from data_engine.official_research.tool_policy import classify_tool_authority, nse_mcp_allowed_tool_names
from data_engine.security_master import SecurityMasterService, load_default_catalog
from data_engine.security_master.models import SecurityListing

_ENGINE = Path(__file__).resolve().parents[1] / "src" / "data_engine" / "official_research"
_NAMED = (
    ("TCS", "INE467B01029", "XNSE"),
    ("INFY", "INE009A01021", "XNSE"),
    ("RELIANCE", "INE002A01018", "XNSE"),
    ("HDFCBANK", "INE040A01034", "XNSE"),
    ("WIPRO", "INE075A01022", "XNSE"),
    ("20MICRONS", "INE144J01027", "XNSE"),
)
_PRIMARY = "https://nsearchives.nseindia.com/annual.pdf"
_AS_OF = date(2026, 3, 31)
_RETRIEVED = datetime(2026, 9, 11, tzinfo=UTC)
_STATEMENT = (
    "consolidated audited financial statements\nunit: actual\n₹ INR\n"
    "year ended 31 March 2026\nas_of: 2026-03-31\n"
    "Statement of profit and loss\nRevenue from operations 100000\n"
    "Profit for the year 20000\nequity shares outstanding 1000000\n"
)


def _master() -> SecurityMasterService:
    return SecurityMasterService(load_default_catalog())


def _listing(ticker: str, isin: str, mic: str = "XNSE") -> SecurityListing:
    resolved = _master().resolve(isin, isin=isin, mic=mic)
    assert resolved.status == "RESOLVED" and resolved.identity is not None
    return resolved.identity


def _request(listing: SecurityListing, fields: tuple[str, ...]) -> ResearchRequest:
    return ResearchRequest(
        fields=fields,
        isin=listing.isin,
        mic=listing.mic,
        ticker=listing.ticker,
        mode="MOCK",
        request_id=f"15-{listing.ticker}",
    )


def _raw(listing: SecurityListing, field: str, value: str, **kwargs) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=new_evidence_id(),
        company=listing.company_name,
        ticker=listing.ticker,
        isin=listing.isin,
        mic=listing.mic,
        field=field,
        value=value,
        as_of=kwargs.get("as_of", _AS_OF),
        retrieved_at=_RETRIEVED,
        source=kwargs.get("source", "NSE"),
        source_type=kwargs.get("source_type", "regulator"),
        source_url=kwargs.get("source_url", _PRIMARY),
        document_date=kwargs.get("as_of", _AS_OF),
        evidence_locator=kwargs.get("locator", "row"),
        currency="INR",
        unit=kwargs.get("unit", "actual"),
        statement_basis=kwargs.get("basis", "consolidated"),
        agent=kwargs.get("agent", "official_research"),
        identity_status=kwargs.get("identity", "PASS"),
        semantic_status=kwargs.get("semantic", "PASS"),
        freshness_status=kwargs.get("freshness", "PASS"),
        corporate_action_status=kwargs.get("ca", "PASS"),
        confidence=None,
        stage="RAW",
        status="UNKNOWN",
        mode="MOCK",
        current_through=kwargs.get("as_of", _AS_OF),
        document_hash=kwargs.get("document_hash", "h1"),
    )


class _FakeOpenAI:
    provider = "openai"
    model_label = "configurable-research-model"

    def __init__(self, *, available: bool = True, evidence: tuple[EvidenceItem, ...] = ()) -> None:
        self._available = available
        self._evidence = evidence

    def available(self) -> bool:
        return self._available

    def research(self, request, plan, context):
        from data_engine.official_research.models import ResearchResult

        _ = request, plan, context
        if not self._available:
            return ResearchResult(
                identity_status="UNKNOWN",
                isin=None,
                mic=None,
                company=None,
                ticker=None,
                evidence=(),
                price=None,
                claims=(),
                unresolved=("OPENAI_UNAVAILABLE",),
                mode="MOCK",
                failures=("OPENAI_UNAVAILABLE",),
            )
        return ResearchResult(
            identity_status="UNKNOWN",
            isin=None,
            mic=None,
            company=None,
            ticker=None,
            evidence=self._evidence,
            price=None,
            claims=(
                ResearchClaim(
                    field="research_narrative",
                    value="model prose is not evidence",
                    source_url=None,
                    document_locator="narrative",
                    agent="openai_nse_mcp",
                    verification_status="REJECT",
                ),
            ),
            unresolved=(),
            mode="MOCK",
            status="RAW",
            provider="openai",
            model_label=self.model_label,
            research_trace={"usage": {"input_tokens": 10, "output_tokens": 4}},
        )


def test_research_agent_contract_and_router() -> None:
    gemini = UnavailableResearchPort("gemini")
    claude = UnavailableResearchPort("claude")
    assert gemini.available() is False
    assert claude.available() is False
    assert GeminiFindAgent().available() is False
    assigned = route_research_roles(
        {"gemini": False, "chatgpt": True, "claude": True, "deep_search": False}
    )
    assert assigned["FIND"] == "chatgpt"
    assert assigned["VERIFY"] == "claude"
    cheap = select_research_agent(
        RouterInputs(
            availability={"openai": True, "gemini": True},
            capabilities={"openai": ("mcp", "search"), "gemini": ("search",)},
            cost_weight={"openai": 0.2, "gemini": 0.1},
            required_capabilities=("mcp",),
            preferred_model="configurable-research-model",
        )
    )
    assert cheap.provider == "openai"
    assert cheap.independent_agents == 1
    assert count_independent_agents({"openai": True, "gemini": True, "claude": True}) == 1
    none = select_research_agent(RouterInputs(availability={"gemini": True, "claude": True}))
    assert none.provider is None
    assert none.independent_agents == 0


def test_openai_responses_research_call_mocked() -> None:
    class _Client:
        model_label = "configurable-research-model"

        def is_configured(self) -> bool:
            return True

        def invoke(self, payload):
            from llm_adapters.openai_responses import OpenAIResponsesResult

            assert payload["model"] == "configurable-research-model"
            assert payload["tools"][0].get("allowed_tools")
            return OpenAIResponsesResult(
                status="complete",
                output_text="narrative only",
                mcp_list_tools=(),
                mcp_calls=(
                    {
                        "name": "get_ltp_by_date",
                        "server_label": "nse_bhavcopy",
                        "output": {"content": [{"type": "text", "text": "2204.1"}]},
                    },
                ),
                usage={"input_tokens": 12, "output_tokens": 3},
                raw={},
            )

    listing = _listing("TCS", "INE467B01029")
    agent = OpenAINseMcpAgent(client=_Client(), enabled=True, model_label="configurable-research-model")
    plan = build_research_plan(listing, _request(listing, ("PRICE",)))
    result = agent.research(
        _request(listing, ("PRICE",)),
        plan,
        ResearchContext(listing=listing),
    )
    assert result.claims[0].verification_status == "REJECT"
    assert result.evidence
    assert all(item.stage == "RAW" for item in result.evidence)
    tools = nse_remote_mcp_tools(("get_ltp_by_date",))
    assert tools[0]["allowed_tools"] == ["get_ltp_by_date"]


def test_nse_tool_selection_and_authority() -> None:
    listing = _listing("INFY", "INE009A01021")
    plan = build_research_plan(listing, _request(listing, ("PRICE", "SHARES")))
    names = nse_mcp_allowed_tool_names(plan)
    assert "get_ltp_by_date" in names
    assert "get_corporate_actions" in names
    assert classify_tool_authority("get_ltp_by_date", "https://mcp.nseindia.in/bhavcopy/cm/mcp") == "PRIMARY"
    assert classify_tool_authority("openai", None) == "DISCOVERY_ONLY"
    assert classify_tool_authority("yahoo", "https://finance.yahoo.com/x") == "SECONDARY"


def test_research_trace_and_structured_claims() -> None:
    listing = _listing("WIPRO", "INE075A01022")
    run = run_research_mesh(
        _request(listing, ("PRICE", "FINANCIALS", "SHARES")),
        listing=listing,
        agent=_FakeOpenAI(),
        availability={"openai": True},
        document_text=_STATEMENT,
        document_url=_PRIMARY,
        tool_calls=(
            {
                "name": "get_ltp_by_date",
                "arguments": {"symbol": listing.ticker},
                "response": "250.0",
                "source_url": "https://mcp.nseindia.in/bhavcopy/cm/mcp",
                "provider": "nse_mcp",
            },
        ),
        context=ResearchContext(listing=listing, preferred_model="configurable-research-model"),
    )
    assert [step.name for step in run.trace.steps] == list(MESH_STEPS)
    assert run.trace.tool_calls[0].authority == "PRIMARY"
    assert run.result.research_agents == 1
    assert "no_manufactured_consensus" in run.trace.decisions
    assert run.trace.cost is not None
    assert run.trace.cost.input_tokens == 10
    public = run.trace.to_public_dict()
    assert "sk-" not in str(public)
    assert run.result.claims[0].field == "research_narrative"


def test_evidence_mapping_and_deduplication() -> None:
    listing = _listing("TCS", "INE467B01029")
    nse = _raw(listing, "eod_close", "2204.1", as_of=date(2026, 9, 11), unit=None, basis=None)
    ai = _raw(
        listing,
        "eod_close",
        "2204.1",
        as_of=date(2026, 9, 11),
        unit=None,
        basis=None,
        agent="openai_nse_mcp",
        source_type="llm",
        source_url="https://nsearchives.nseindia.com/annual.pdf",
    )
    assert evidence_fingerprint(nse) == evidence_fingerprint(ai)
    deduped = dedupe_evidence((ai, nse))
    assert len(deduped) == 1
    assert deduped[0].agent == "official_research"


def test_identity_attack() -> None:
    listing = _listing("TCS", "INE467B01029")
    mismatched = run_research_mesh(
        ResearchRequest(fields=("PRICE",), ticker="INFY", isin=listing.isin, mic=listing.mic, mode="MOCK"),
        listing=listing,
    )
    assert mismatched.result.status == "REJECT"
    assert "SECURITY_AMBIGUOUS" in mismatched.result.failures
    missing = run_research_mesh(
        ResearchRequest(fields=("PRICE",), ticker="NOTAREALTICKERZZ", isin="INE000000000", mic="XNSE", mode="MOCK")
    )
    assert missing.result.status == "REJECT"
    assert missing.result.failures[0] in {"SECURITY_NOT_FOUND", "SECURITY_UNKNOWN"}


def test_stale_conflict_hallucination_injection() -> None:
    listing = _listing("RELIANCE", "INE002A01018")
    stale = run_research_mesh(
        _request(listing, ("net_income",)),
        listing=listing,
        availability={"openai": True},
        agent=_FakeOpenAI(),
        candidates={
            "net_income": (
                _raw(listing, "net_income", "20", freshness="FAIL"),
            )
        },
    )
    assert stale.result.refresh_required == ("net_income",) or stale.acquisition.outcomes[0].status in {
        "REFRESH_REQUIRED",
        "UNKNOWN",
    }
    conflict = run_research_mesh(
        _request(listing, ("net_income",)),
        listing=listing,
        availability={"openai": True},
        agent=_FakeOpenAI(),
        candidates={
            "net_income": (
                _raw(listing, "net_income", "10", source_url="https://nsearchives.nseindia.com/a.pdf"),
                _raw(listing, "net_income", "11", source_url="https://www.bseindia.com/b.pdf"),
            )
        },
    )
    assert conflict.result.conflicts == ("net_income",)
    hallucinated = run_research_mesh(
        _request(listing, ("SHARES",)),
        listing=listing,
        availability={"openai": True},
        agent=_FakeOpenAI(),
        context=ResearchContext(
            listing=listing,
            user_assumptions=("Assume the company has 5 billion outstanding shares.",),
        ),
    )
    assert hallucinated.result.claims[0].verification_status == "REJECT"
    assert "shares_outstanding" not in hallucinated.result.verified_fields
    injected = run_research_mesh(
        _request(listing, ("revenue",)),
        listing=listing,
        availability={"openai": True},
        agent=_FakeOpenAI(),
        context=ResearchContext(
            listing=listing,
            injected_sources=("https://evil.example/company-has-x-shares",),
        ),
        candidates={
            "revenue": (
                _raw(listing, "revenue", "100"),
                _raw(
                    listing,
                    "revenue",
                    "999",
                    source_url="https://www.screener.in/company/ANY/",
                    source_type="approved_research",
                    source="Screener",
                ),
            )
        },
    )
    assert injected.result.claims[0].field == "injected_source"
    revenue = next(item for item in injected.result.evidence if item.field == "revenue")
    assert revenue.value == "100"
    assert revenue.status == "VERIFIED"


def test_provider_and_mcp_failure_taxonomy() -> None:
    listing = _listing("INFY", "INE009A01021")
    run = run_research_mesh(
        _request(listing, ("PRICE",)),
        listing=listing,
        agent=_FakeOpenAI(available=True),
        availability={"openai": False, "gemini": False},
    )
    assert "OPENAI_UNAVAILABLE" in run.trace.errors
    assert is_transport_failure("OPENAI_TIMEOUT")
    assert is_transport_failure("NSE_UNAVAILABLE")
    assert not is_transport_failure("EVIDENCE_CONFLICT")
    assert not is_transport_failure("SECURITY_AMBIGUOUS")
    assert classify_openai_failure("timeout") == "OPENAI_TIMEOUT"
    assert classify_openai_failure("rate_limited") == "OPENAI_RATE_LIMITED"
    assert NSE_MCP_COMMERCIAL_STATUS == "COMMERCIAL_USE_PENDING"


def test_ai_cannot_bypass_evidence_judge() -> None:
    listing = _listing("TCS", "INE467B01029")
    ai_only = _raw(
        listing,
        "net_income",
        "42",
        source_type="llm",
        agent="openai_nse_mcp",
        source_url="https://example.invalid/ai",
    )
    run = run_research_mesh(
        _request(listing, ("net_income",)),
        listing=listing,
        availability={"openai": True},
        agent=_FakeOpenAI(evidence=(ai_only,)),
    )
    promoted = EvidenceJudge().promote(ai_only)
    assert promoted.status != "VERIFIED"
    assert all(item.status != "VERIFIED" or item.source_type != "llm" for item in run.result.evidence)


def test_universal_multi_security_same_mesh() -> None:
    catalog = load_default_catalog()
    named = {isin for _, isin, _ in _NAMED}
    dynamic = next(
        item
        for item in catalog.all()
        if item.eligibility and item.mic == "XNSE" and item.isin not in named
    )
    tickers = []
    for ticker, isin, mic in _NAMED:
        listing = _listing(ticker, isin, mic)
        run = run_research_mesh(
            _request(listing, ("PRICE", "FINANCIALS", "SHARES")),
            listing=listing,
            availability={"openai": True},
            agent=_FakeOpenAI(),
            document_text=_STATEMENT,
            document_url=_PRIMARY,
            candidates={
                "eod_close": (
                    _raw(
                        listing,
                        "eod_close",
                        "100",
                        as_of=date(2026, 9, 11),
                        unit=None,
                        basis=None,
                        source_type="exchange_eod",
                    ),
                )
            },
        )
        assert run.result.identity_status == "VERIFIED"
        assert "PLAN" in [step.name for step in run.trace.steps]
        tickers.append(listing.ticker)
    dynamic_run = run_research_mesh(
        _request(dynamic, ("SHARES",)),
        listing=dynamic,
        availability={"openai": True},
        agent=_FakeOpenAI(),
        document_text=_STATEMENT,
        document_url=_PRIMARY,
    )
    assert dynamic.ticker not in tickers
    assert dynamic_run.result.identity_status == "VERIFIED"


def test_cost_and_performance_mock_path() -> None:
    listing = _listing("HDFCBANK", "INE040A01034")
    samples = []
    for _ in range(11):
        run = run_research_mesh(
            _request(listing, ("FINANCIALS",)),
            listing=listing,
            availability={"openai": True},
            agent=_FakeOpenAI(),
            document_text=_STATEMENT,
            document_url=_PRIMARY,
            router_inputs=RouterInputs(
                availability={"openai": True},
                capabilities={"openai": ("mcp", "search")},
                input_token_usd=0.15 / 1_000_000,
                output_token_usd=0.60 / 1_000_000,
                preferred_model="configurable-research-model",
            ),
        )
        samples.append(run.trace.cost.latency_ms if run.trace.cost else 0.0)
    ordered = sorted(samples)
    p50 = median(ordered)
    p95 = ordered[int(0.95 * (len(ordered) - 1))]
    assert p50 >= 0
    assert p95 >= p50
    assert run.trace.cost.estimated_cost is not None
    bottleneck = max(run.trace.timings, key=run.trace.timings.get)
    assert bottleneck in {name.lower() for name in MESH_STEPS}


def test_no_ticker_specific_mesh_logic() -> None:
    forbidden = ("TCS", "INFY", "HDFCBANK", "RELIANCE", "WIPRO", "20MICRONS", "21STCENMGM")
    for name in (
        "research_mesh.py",
        "agent_port.py",
        "tool_policy.py",
        "evidence_identity.py",
        "provider_router.py",
        "research_trace.py",
    ):
        text = (_ENGINE / name).read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text
        compact = text.replace(" ", "").lower()
        assert "ifticker==" not in compact
        assert "ifcompany==" not in compact
        assert "ifisin==" not in compact
