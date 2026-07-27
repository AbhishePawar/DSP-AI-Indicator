import type {
  AIProvider,
  AIProviderConfig,
  AIRequest,
  AIResponse,
  AIStreamResult,
} from "../types";

const CONFIG: AIProviderConfig = {
  id: "mock",
  label: "Mock Provider",
  description: "Test double for provider swapping — no copilot intelligence.",
  status: "ready",
  capabilities: ["chat", "compare", "streaming"],
};

export class MockProvider implements AIProvider {
  readonly config = CONFIG;

  getCapabilities() {
    return this.config.capabilities;
  }

  async complete(request: AIRequest): Promise<AIResponse> {
    const ticker = request.primary.request?.ticker ?? "unknown";

    return {
      content: `[mock:${this.config.id}] Acknowledged ${request.questionId} for ${ticker}.`,
      citations: [],
      intent: "unknown",
      unavailable: false,
      providerId: "mock",
      metadata: {
        composedAt: new Date().toISOString(),
        simulated: true,
      },
    };
  }

  async stream(request: AIRequest): Promise<AIStreamResult> {
    const full = await this.complete(request);
    const parts = full.content.split(" ");
    const chunks = parts.map((word, index) => ({
      delta: index === 0 ? word : ` ${word}`,
      done: index === parts.length - 1,
      providerId: "mock" as const,
    }));
    return { chunks, final: full };
  }
}

export function createMockProvider(): MockProvider {
  return new MockProvider();
}
