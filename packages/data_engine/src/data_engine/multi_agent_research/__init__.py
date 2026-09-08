"""SIMPLE-14H multi-agent research boundary.

AI finds evidence. Approved sources establish evidence. DSP calculates.
"""

from __future__ import annotations

from data_engine.multi_agent_research.agents import (
    AgentCapabilityState,
    AgentFailureClass,
    AgentRole,
    AgentRunResult,
    ResearchAgentPort,
    ScriptedResearchAgent,
    UnavailableResearchAgent,
    classify_http_agent_failure,
)
from data_engine.multi_agent_research.contracts import (
    AUTHORITATIVE_FINANCIAL_FIELDS,
    BUSINESS_RESEARCH_FIELDS,
    CurrentnessStatus,
    EvidenceRecord,
    ResearchClaim,
    ResearchRequest,
    ShareCapitalKind,
)
from data_engine.multi_agent_research.injection import (
    InjectionScan,
    scan_untrusted_text,
)
from data_engine.multi_agent_research.orchestrator import (
    DEFAULT_AGENT_CAPABILITIES,
    ResearchOrchestrator,
    ResearchOutcomeStatus,
    ResearchRunResult,
    default_unavailable_agents,
)
from data_engine.multi_agent_research.reconciliation import (
    AgreementReport,
    ReconciliationResult,
    ReconciliationStatus,
    compare_agents,
    reconcile_field,
)
from data_engine.multi_agent_research.source_urls import (
    UrlClassification,
    classify_source_url,
)

__all__ = [
    "AUTHORITATIVE_FINANCIAL_FIELDS",
    "BUSINESS_RESEARCH_FIELDS",
    "DEFAULT_AGENT_CAPABILITIES",
    "AgentCapabilityState",
    "AgentFailureClass",
    "AgentRole",
    "AgentRunResult",
    "AgreementReport",
    "CurrentnessStatus",
    "EvidenceRecord",
    "InjectionScan",
    "ReconciliationResult",
    "ReconciliationStatus",
    "ResearchAgentPort",
    "ResearchClaim",
    "ResearchOrchestrator",
    "ResearchOutcomeStatus",
    "ResearchRequest",
    "ResearchRunResult",
    "ScriptedResearchAgent",
    "ShareCapitalKind",
    "UnavailableResearchAgent",
    "UrlClassification",
    "classify_http_agent_failure",
    "classify_source_url",
    "compare_agents",
    "default_unavailable_agents",
    "reconcile_field",
    "scan_untrusted_text",
]
