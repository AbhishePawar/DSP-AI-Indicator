"""Generic client share-research engine."""

from dsp_platform.share_research.engine import ShareResearchEngine, research_shares
from dsp_platform.share_research.gemini import (
    FixedShareResearchGemini,
    GeminiShareResearchAdapter,
    ShareResearchGeminiError,
)
from dsp_platform.share_research.models import (
    ShareResearchRequest,
    ShareResearchResult,
    ShareResearchStatus,
)
from dsp_platform.share_research.overlay import current_share_research_snapshot
from dsp_platform.share_research.store import (
    ShareResearchStore,
    configure_share_research_store,
    get_share_research_store,
    reset_share_research_store_for_tests,
)

__all__ = [
    "FixedShareResearchGemini",
    "GeminiShareResearchAdapter",
    "ShareResearchEngine",
    "ShareResearchGeminiError",
    "ShareResearchRequest",
    "ShareResearchResult",
    "ShareResearchStatus",
    "ShareResearchStore",
    "configure_share_research_store",
    "current_share_research_snapshot",
    "get_share_research_store",
    "research_shares",
    "reset_share_research_store_for_tests",
]
