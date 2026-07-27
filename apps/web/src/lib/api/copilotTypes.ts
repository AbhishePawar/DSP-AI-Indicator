import type { AnalyseRequest, AnalyseResponse } from "@/lib/api/compositionTypes";
import type { CopilotIntent, SuggestedQuestionId } from "@/lib/copilot/types";

export type CopilotCompleteRequestBody = {
  question_id: SuggestedQuestionId | "freeform";
  freeform?: string;
  request: AnalyseRequest | null;
  response: AnalyseResponse | null;
  secondary_request?: AnalyseRequest | null;
  secondary_response?: AnalyseResponse | null;
  last_intent?: CopilotIntent | null;
  market_context?: Record<string, string | number | null> | null;
};

export type CopilotCompleteResponseBody = {
  content: string;
  citations: string[];
  intent: CopilotIntent;
  unavailable: boolean;
  provider_id: string;
  limitations: string[];
};

export type CopilotStreamChunkBody = {
  delta: string;
  done: boolean;
  provider_id?: string;
};

export type CopilotProvidersResponseBody = {
  providers: Array<{
    id: string;
    model: string;
    configured: boolean;
    capabilities: string[];
  }>;
  active_provider: string;
};
