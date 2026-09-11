"""Official NSE/BSE evidence research engine (SIMPLE-14L).

Not a commercial market-data provider. AI agents find and challenge
evidence; official sources remain the authority; DSP judges promotion.
"""

from __future__ import annotations

from data_engine.official_research.agents import (
    ChatGPTVerifyAgent,
    ClaudeReviewAgent,
    DeepSearchAttackAgent,
    GeminiFindAgent,
    UnavailableAgent,
    agent_outcome,
)
from data_engine.official_research.bse_eod import BSE_MIC, BseEodService
from data_engine.official_research.currentness import (
    CapitalEvent,
    EvidenceCache,
    cache_key,
    is_current,
    judge_currentness,
    market_cap_status,
)
from data_engine.official_research.assumption_contract import (
    CanonicalAssumption,
    classify_data_class,
)
from data_engine.official_research.assumption_validator import (
    validate_assumption,
    validate_assumption_pack,
)
from data_engine.official_research.dsp_calculation import run_dsp_calculations
from data_engine.official_research.dsp_gate import dsp_gate
from data_engine.official_research.derived_fields import derive_dsp_fields
from data_engine.official_research.end_to_end import (
    analyse_listing,
    analyse_user_query,
    describe_supported_universe,
)
from data_engine.official_research.documents import (
    DocumentCandidate,
    DocumentStore,
    document_version_relation,
)
from data_engine.official_research.extraction import (
    attack_corporate_actions,
    classify_capital_effect,
    classify_share_count_impact,
    classify_share_semantic_type,
    canonical_share_semantic_type,
)
from data_engine.official_research.field_acquisition import acquire_planned_fields
from data_engine.official_research.provider_router import route_research_roles, select_research_agent
from data_engine.official_research.research_loop import run_research_loop
from data_engine.official_research.research_mesh import run_research_mesh
from data_engine.official_research.research_plan import (
    build_research_plan,
    plan_report_block,
)
from data_engine.official_research.judge import (
    EvidenceJudge,
    ReconciliationDecision,
    classify_conflict_reason,
)
from data_engine.official_research.matching import match_udiff_row
from data_engine.official_research.models import (
    CAPITAL_EVENT_TYPES,
    EvidenceItem,
    PriceSnapshot,
    ResearchClaim,
    ResearchRequest,
    ResearchResult,
    UdiffCashRow,
    new_evidence_id,
    utc_now,
)
from data_engine.official_research.nse_eod import (
    NSE_DAILY_REPORTS_URL,
    NSE_UDIFF_FILE_KEY,
    DiscoveredNseFile,
    NseEodBundle,
    NseEodService,
    NsePublicHttp,
    discover_udiff_final,
    parse_capital_market_state,
    parse_nse_calendar_date,
    unzip_udiff,
)
from data_engine.official_research.nse_primary import (
    NsePrimaryBundle,
    NsePrimaryEvidenceService,
    parse_financial_results,
    parse_quote_equity_shares,
    parse_shareholding_shares,
)
from data_engine.official_research.orchestrator import ResearchOrchestrator
from data_engine.official_research.price import (
    CANONICAL_EOD_FIELD,
    PriceContractError,
    eod_close_snapshot,
    validate_price_snapshot,
)
from data_engine.official_research.prompt_guard import (
    looks_like_injection,
    sanitize_document_text,
)
from data_engine.official_research.semantics import (
    cannot_derive_shares,
    semantic_field_status,
    valuation_gate,
)
from data_engine.official_research.source_policy import (
    SourcePolicy,
    classify_source_url,
)
from data_engine.official_research.udiff import parse_udiff_csv
from data_engine.official_research.verified_dataset import (
    DSPAnalysisResult,
    VerifiedDataset,
)

__all__ = [
    "BSE_MIC",
    "CANONICAL_EOD_FIELD",
    "CAPITAL_EVENT_TYPES",
    "NSE_DAILY_REPORTS_URL",
    "NSE_UDIFF_FILE_KEY",
    "BseEodService",
    "CanonicalAssumption",
    "CapitalEvent",
    "ChatGPTVerifyAgent",
    "ClaudeReviewAgent",
    "DeepSearchAttackAgent",
    "DiscoveredNseFile",
    "DSPAnalysisResult",
    "EvidenceCache",
    "EvidenceItem",
    "EvidenceJudge",
    "ReconciliationDecision",
    "GeminiFindAgent",
    "NseEodBundle",
    "NseEodService",
    "NsePrimaryBundle",
    "NsePrimaryEvidenceService",
    "NsePublicHttp",
    "PriceContractError",
    "PriceSnapshot",
    "ResearchClaim",
    "ResearchOrchestrator",
    "ResearchRequest",
    "ResearchResult",
    "SourcePolicy",
    "UdiffCashRow",
    "UnavailableAgent",
    "VerifiedDataset",
    "analyse_listing",
    "analyse_user_query",
    "describe_supported_universe",
    "acquire_planned_fields",
    "attack_corporate_actions",
    "build_research_plan",
    "cache_key",
    "cannot_derive_shares",
    "classify_capital_effect",
    "classify_conflict_reason",
    "classify_data_class",
    "classify_share_count_impact",
    "classify_share_semantic_type",
    "canonical_share_semantic_type",
    "classify_source_url",
    "derive_dsp_fields",
    "discover_udiff_final",
    "document_version_relation",
    "dsp_gate",
    "eod_close_snapshot",
    "is_current",
    "judge_currentness",
    "looks_like_injection",
    "market_cap_status",
    "match_udiff_row",
    "new_evidence_id",
    "parse_capital_market_state",
    "parse_financial_results",
    "parse_nse_calendar_date",
    "parse_quote_equity_shares",
    "parse_shareholding_shares",
    "parse_udiff_csv",
    "plan_report_block",
    "route_research_roles",
    "run_dsp_calculations",
    "run_research_loop",
    "run_research_mesh",
    "select_research_agent",
    "sanitize_document_text",
    "semantic_field_status",
    "unzip_udiff",
    "utc_now",
    "validate_assumption",
    "validate_assumption_pack",
    "validate_price_snapshot",
    "valuation_gate",
    "DocumentCandidate",
    "DocumentStore",
]
