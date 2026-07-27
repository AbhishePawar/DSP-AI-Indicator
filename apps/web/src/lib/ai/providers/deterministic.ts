import { composeCopilotAnswer } from "@/lib/copilot/placeholderAnswers";
import type { AIProvider, AIProviderConfig, AIRequest, AIResponse } from "../types";
import { toAIResponse } from "../types";

const CONFIG: AIProviderConfig = {
  id: "deterministic",
  label: "Deterministic Copilot",
  description:
    "Wraps existing copilot intelligence — intent, context, and template composition.",
  status: "ready",
  capabilities: ["chat", "compare"],
};

export class DeterministicProvider implements AIProvider {
  readonly config = CONFIG;

  getCapabilities() {
    return this.config.capabilities;
  }

  async complete(request: AIRequest): Promise<AIResponse> {
    const composed = composeCopilotAnswer(request.questionId, {
      request: request.primary.request,
      response: request.primary.response,
      freeform: request.freeform,
      secondaryRequest: request.secondary?.request ?? null,
      secondaryResponse: request.secondary?.response ?? null,
      lastIntent: request.lastIntent,
    });

    return toAIResponse(composed, "deterministic", {
      composedAt: new Date().toISOString(),
    });
  }
}

export function createDeterministicProvider(): DeterministicProvider {
  return new DeterministicProvider();
}
