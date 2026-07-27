import { createBackendProvider, createDeterministicProvider, createMockProvider } from "./providers";
import type { ProviderRegistry } from "./registry";
import type { AIProvider, AIProviderId } from "./types";

export class ProviderFactory {
  constructor(private readonly registry: ProviderRegistry) {}

  create(id: AIProviderId): AIProvider {
    const existing = this.registry.get(id);
    if (existing) return existing;

    switch (id) {
      case "deterministic":
        return createDeterministicProvider();
      case "mock":
        return createMockProvider();
      case "backend":
        return createBackendProvider();
      default:
        throw new Error(`Unknown AI provider: ${id}`);
    }
  }

  resolve(id: AIProviderId): AIProvider {
    return this.create(id);
  }
}
