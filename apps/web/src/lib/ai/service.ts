import type { AIPlatformConfig } from "./config";
import { resolveAIConfig } from "./config";
import { ProviderFactory } from "./factory";
import { createDefaultRegistry, type ProviderRegistry } from "./registry";
import type {
  AICapability,
  AIProvider,
  AIProviderConfig,
  AIProviderId,
  AIRequest,
  AIResponse,
  AIStreamResult,
} from "./types";

export class AIService {
  private activeId: AIProviderId;
  private readonly factory: ProviderFactory;

  constructor(
    private readonly registry: ProviderRegistry,
    config: AIPlatformConfig = resolveAIConfig(),
  ) {
    this.factory = new ProviderFactory(registry);
    this.activeId = config.activeProviderId;
  }

  getActiveProviderId(): AIProviderId {
    return this.activeId;
  }

  setActiveProvider(id: AIProviderId): void {
    this.factory.create(id);
    this.activeId = id;
  }

  getActiveProvider(): AIProvider {
    const existing = this.registry.get(this.activeId);
    if (existing) return existing;
    const created = this.factory.create(this.activeId);
    this.registry.register(created);
    return created;
  }

  listProviders(): AIProviderConfig[] {
    return this.registry.list();
  }

  getCapabilities(providerId?: AIProviderId): readonly AICapability[] {
    const id = providerId ?? this.activeId;
    const provider =
      this.registry.get(id) ?? this.factory.create(id);
    return provider.getCapabilities();
  }

  supportsCapability(
    capability: AICapability,
    providerId?: AIProviderId,
  ): boolean {
    return this.getCapabilities(providerId).includes(capability);
  }

  async complete(request: AIRequest): Promise<AIResponse> {
    return this.getActiveProvider().complete(request);
  }

  async stream(request: AIRequest): Promise<AIStreamResult> {
    const provider = this.getActiveProvider();
    if (provider.stream) {
      return provider.stream(request);
    }
    const final = await provider.complete(request);
    return {
      chunks: [{ delta: final.content, done: true, providerId: final.providerId }],
      final,
    };
  }
}

export function createAIService(
  registry: ProviderRegistry = createDefaultRegistry(),
  config?: AIPlatformConfig,
): AIService {
  return new AIService(registry, config);
}
