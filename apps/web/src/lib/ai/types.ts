/**
 * AI provider abstraction — request/response models.
 * Presentation layer only; no network, prompts, or provider SDKs.
 */

import type { AnalyseRequest, AnalyseResponse } from "@/lib/api/compositionTypes";
import type {
  CopilotComposedAnswer,
  CopilotIntent,
  ResearchCitationId,
  SuggestedQuestionId,
} from "@/lib/copilot/types";

export const AI_PROVIDER_IDS = ["mock", "deterministic", "backend"] as const;

export type AIProviderId = (typeof AI_PROVIDER_IDS)[number];

export type AICapability =
  | "chat"
  | "compare"
  | "streaming"
  | "vision"
  | "reasoning";

export type AIProviderStatus = "ready" | "unavailable" | "placeholder";

export type AIProviderConfig = {
  id: AIProviderId;
  label: string;
  description: string;
  status: AIProviderStatus;
  capabilities: readonly AICapability[];
};

export type AIRequest = {
  questionId: SuggestedQuestionId | "freeform";
  freeform?: string;
  primary: {
    request: AnalyseRequest | null;
    response: AnalyseResponse | null;
  };
  secondary?: {
    request: AnalyseRequest | null;
    response: AnalyseResponse | null;
  };
  lastIntent?: CopilotIntent | null;
};

export type AIResponse = {
  content: string;
  citations: ResearchCitationId[];
  intent: CopilotIntent;
  unavailable: boolean;
  providerId: AIProviderId;
  metadata?: {
    composedAt: string;
    simulated?: boolean;
    backendProvider?: string;
  };
};

/** Placeholder streaming chunk — no real stream implementation in EPIC-011. */
export type AIStreamChunk = {
  delta: string;
  done: boolean;
  providerId: AIProviderId;
};

export type AIStreamResult = {
  chunks: AIStreamChunk[];
  final: AIResponse | null;
};

export interface AIProvider {
  readonly config: AIProviderConfig;
  getCapabilities(): readonly AICapability[];
  complete(request: AIRequest): Promise<AIResponse>;
  /** Placeholder — returns empty stream unless provider opts in later. */
  stream?(request: AIRequest): Promise<AIStreamResult>;
}

export function toAIResponse(
  composed: CopilotComposedAnswer,
  providerId: AIProviderId,
  metadata?: AIResponse["metadata"],
): AIResponse {
  return {
    content: composed.content,
    citations: composed.citations,
    intent: composed.intent,
    unavailable: composed.unavailable,
    providerId,
    metadata,
  };
}
