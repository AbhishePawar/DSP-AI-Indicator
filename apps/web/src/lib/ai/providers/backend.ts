import { api } from "@/lib/api/client";
import type {
  CopilotCompleteRequestBody,
  CopilotCompleteResponseBody,
  CopilotStreamChunkBody,
} from "@/lib/api/copilotTypes";
import type { AIRequest, AIResponse } from "@/lib/ai";
import type {
  AIProvider,
  AIProviderConfig,
  AIStreamResult,
} from "@/lib/ai/types";
import type { CopilotIntent, ResearchCitationId } from "@/lib/copilot/types";

const CONFIG: AIProviderConfig = {
  id: "backend",
  label: "Backend Copilot",
  description:
    "Routes all AI requests through /api/v1/copilot — never calls vendors from the browser.",
  status: "ready",
  capabilities: ["chat", "compare", "streaming"],
};

function toRequestBody(request: AIRequest): CopilotCompleteRequestBody {
  return {
    question_id: request.questionId,
    freeform: request.freeform,
    request: request.primary.request,
    response: request.primary.response,
    secondary_request: request.secondary?.request ?? null,
    secondary_response: request.secondary?.response ?? null,
    last_intent: request.lastIntent ?? null,
  };
}

function mapResponse(body: {
  content: string;
  citations: string[];
  intent: string;
  unavailable: boolean;
  provider_id: string;
}): AIResponse {
  return {
    content: body.content,
    citations: body.citations as ResearchCitationId[],
    intent: body.intent as CopilotIntent,
    unavailable: body.unavailable,
    providerId: "backend",
    metadata: {
      composedAt: new Date().toISOString(),
      backendProvider: body.provider_id,
    },
  };
}

export class BackendProvider implements AIProvider {
  readonly config = CONFIG;

  getCapabilities() {
    return this.config.capabilities;
  }

  async complete(request: AIRequest): Promise<AIResponse> {
    const body = await api.copilotComplete(toRequestBody(request));
    return mapResponse(body);
  }

  async stream(request: AIRequest): Promise<AIStreamResult> {
    const chunks = await api.copilotStream(toRequestBody(request));
    const finalChunk = chunks.at(-1);
    return {
      chunks: chunks.map((chunk) => ({
        delta: chunk.delta,
        done: chunk.done,
        providerId: "backend",
      })),
      final: finalChunk
        ? {
            content: chunks.map((c) => c.delta).join(""),
            citations: [],
            intent: "unknown",
            unavailable: false,
            providerId: "backend",
          }
        : null,
    };
  }
}

export function createBackendProvider(): BackendProvider {
  return new BackendProvider();
}
