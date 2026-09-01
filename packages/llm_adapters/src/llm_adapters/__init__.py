"""External LLM provider adapters — outside frozen copilot domain."""

from llm_adapters.benchmark import (
    BenchmarkRow,
    build_benchmark_table,
    run_case_against_model,
)
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
from llm_adapters.model_tiers import (
    DEFAULT_TIERS,
    ModelTier,
    TierConfig,
    get_tier_config,
)
from llm_adapters.privacy_boundary import (
    PrivateInternalResult,
    PublicDecisionPack,
    assert_no_private_leakage,
)
from llm_adapters.quality_gate import (
    GateOutcome,
    GateVerdict,
    evaluate_gate,
    run_with_escalation,
)
from llm_adapters.registry import ProviderRegistry, build_default_registry
from llm_adapters.routing import (
    ComplexitySignal,
    RoutingDecision,
    decide_routing,
)
from llm_adapters.service import CopilotCompleteService, CopilotCompleteResult
from llm_adapters.tools import (
    DEFAULT_TOOL_NAMES,
    DSPToolBackend,
    ToolInputField,
    ToolOutputField,
    ToolRegistry,
    ToolResult,
    ToolSpec,
    ToolStatus,
    assert_no_tool_leakage,
)

__version__ = "0.1.0"

__all__ = [
    "BenchmarkRow",
    "ComplexitySignal",
    "CopilotCompleteResult",
    "CopilotCompleteService",
    "DEFAULT_CATALOG",
    "DEFAULT_TIERS",
    "DEFAULT_TOOL_NAMES",
    "DSPToolBackend",
    "ErrorCategory",
    "EvaluationRequest",
    "EvaluationResult",
    "EvaluationStatus",
    "GateOutcome",
    "GateVerdict",
    "LLMPlatformConfig",
    "ModelCapabilities",
    "ModelInfo",
    "ModelLimits",
    "ModelPricing",
    "ModelTier",
    "PrivateInternalResult",
    "ProviderRegistry",
    "PublicDecisionPack",
    "QualityEvaluation",
    "RoutingDecision",
    "ScoredEvaluation",
    "TierConfig",
    "TokenUsage",
    "ToolInputField",
    "ToolOutputField",
    "ToolRegistry",
    "ToolResult",
    "ToolSpec",
    "ToolStatus",
    "__version__",
    "assert_no_private_leakage",
    "assert_no_tool_leakage",
    "build_benchmark_table",
    "build_default_registry",
    "calculate_cost_score",
    "calculate_estimated_cost",
    "calculate_overall_score",
    "calculate_quality_score",
    "decide_routing",
    "evaluate_gate",
    "get_model_info",
    "get_tier_config",
    "list_identories",
    "load_llm_config",
    "run_case_against_model",
    "run_with_escalation",
    "score_evaluations",
]
