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

/** RC1 Milestone 7 — Copilot 2.0 orchestration request. */
export type CopilotV2RequestBody = {
  message?: string;
  user_text?: string;
  mode?: string;
  conversation_id?: string | null;
  symbol?: string | null;
  symbols?: string[] | null;
  portfolio_id?: string | null;
  analyse_response?: Record<string, unknown> | null;
  secondary_analyse_response?: Record<string, unknown> | null;
  research_object?: Record<string, unknown> | null;
  report?: Record<string, unknown> | null;
  portfolio?: Record<string, unknown> | null;
  portfolio_intelligence?: Record<string, unknown> | null;
  committee_result?: Record<string, unknown> | null;
  comparison_result?: Record<string, unknown> | null;
  document_kind?: string | null;
  workspace?: string | null;
  buffett_mode?: boolean;
};

export type CopilotV2Source = {
  engine?: string;
  detail?: string | null;
  note?: string | null;
};

export type CopilotV2ResponseBody = {
  ok: boolean;
  result?: {
    response_id?: string;
    conversation_id?: string;
    created_at?: string;
    intent?: string;
    answer?: string;
    unavailable?: boolean;
    sources?: CopilotV2Source[];
    context?: Record<string, unknown>;
    suggested_questions?: Array<{ id: string; label: string }>;
    provenance?: Record<string, unknown>;
  };
  message?: string | null;
  error?: string;
};
