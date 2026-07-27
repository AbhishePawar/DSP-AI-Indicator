import { createBackendProvider, createDeterministicProvider, createMockProvider } from "./providers";
import type { AIProvider, AIProviderConfig, AIProviderId } from "./types";

export class ProviderRegistry {
  private readonly providers = new Map<AIProviderId, AIProvider>();

  register(provider: AIProvider): void {
    this.providers.set(provider.config.id, provider);
  }

  get(id: AIProviderId): AIProvider | undefined {
    return this.providers.get(id);
  }

  has(id: AIProviderId): boolean {
    return this.providers.has(id);
  }

  list(): AIProviderConfig[] {
    return [...this.providers.values()].map((provider) => provider.config);
  }

  listCapabilities(): Record<AIProviderId, readonly string[]> {
    const result = {} as Record<AIProviderId, readonly string[]>;
    for (const provider of this.providers.values()) {
      result[provider.config.id] = provider.getCapabilities();
    }
    return result;
  }
}

export function createDefaultRegistry(): ProviderRegistry {
  const registry = new ProviderRegistry();
  registry.register(createDeterministicProvider());
  registry.register(createMockProvider());
  registry.register(createBackendProvider());
  return registry;
}
