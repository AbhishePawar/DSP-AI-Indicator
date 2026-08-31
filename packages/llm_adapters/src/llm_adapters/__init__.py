"""External LLM provider adapters — outside frozen copilot domain."""

from llm_adapters.config import LLMPlatformConfig, load_llm_config
from llm_adapters.cost_scoring import (
    ScoredEvaluation,
    calculate_cost_score,
    calculate_estimated_cost,
    calculate_overall_score,
    calculate_quality_score,
    score_evaluations,
)
from llm_adapters.evaluation import (
    ErrorCategory,
    EvaluationRequest,
    EvaluationResult,
    EvaluationStatus,
    QualityEvaluation,
    TokenUsage,
)
from llm_adapters.model_catalog import (
    DEFAULT_CATALOG,
    ModelCapabilities,
    ModelInfo,
    ModelLimits,
    ModelPricing,
    get_model_info,
    list_identities,
)
from llm_adapters.registry import ProviderRegistry, build_default_registry
from llm_adapters.service import CopilotCompleteService, CopilotCompleteResult

__version__ = "0.1.0"

__all__ = [
    "CopilotCompleteResult",
    "CopilotCompleteService",
    "DEFAULT_CATALOG",
    "ErrorCategory",
    "EvaluationRequest",
    "EvaluationResult",
    "EvaluationStatus",
    "LLMPlatformConfig",
    "ModelCapabilities",
    "ModelInfo",
    "ModelLimits",
    "ModelPricing",
    "ProviderRegistry",
    "QualityEvaluation",
    "ScoredEvaluation",
    "TokenUsage",
    "__version__",
    "build_default_registry",
    "calculate_cost_score",
    "calculate_estimated_cost",
    "calculate_overall_score",
    "calculate_quality_score",
    "get_model_info",
    "list_identities",
    "load_llm_config",
    "score_evaluations",
]
