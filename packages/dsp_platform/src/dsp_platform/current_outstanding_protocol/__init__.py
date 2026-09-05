"""AI-assisted current-outstanding protocol (production blocked).

AI discovers/extracts. DSP validates/accepts/calculates. Production AI
execution remains blocked. Test doubles live in ``testing.py``.
"""

from __future__ import annotations

from dsp_platform.current_outstanding_protocol.gated_discovery import (
    ActivationGatedEvidenceDiscovery,
    AiAssistedShareCountWebDiscovery,
)
from dsp_platform.current_outstanding_protocol.models import (
    CurrentOutstandingDiagnostic,
    CurrentOutstandingProtocolResult,
    UntrustedShareCountAiCandidate,
)
from dsp_platform.current_outstanding_protocol.promotion import (
    dsp_accept_untrusted_share_count_candidate,
)
from dsp_platform.current_outstanding_protocol.protocol import (
    CurrentOutstandingProtocol,
    production_current_outstanding_protocol,
)
from dsp_platform.current_outstanding_protocol.queries import (
    share_count_web_research_queries,
)
from dsp_platform.current_outstanding_protocol.web_research import (
    UntrustedWebEvidenceClaim,
    discovery_result_from_untrusted_web_claims,
    untrusted_web_claims_from_ai_draft,
)

__all__ = [
    "ActivationGatedEvidenceDiscovery",
    "AiAssistedShareCountWebDiscovery",
    "CurrentOutstandingDiagnostic",
    "CurrentOutstandingProtocol",
    "CurrentOutstandingProtocolResult",
    "UntrustedShareCountAiCandidate",
    "UntrustedWebEvidenceClaim",
    "discovery_result_from_untrusted_web_claims",
    "dsp_accept_untrusted_share_count_candidate",
    "production_current_outstanding_protocol",
    "share_count_web_research_queries",
    "untrusted_web_claims_from_ai_draft",
]
