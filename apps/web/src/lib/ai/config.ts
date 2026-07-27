import { env } from "@/lib/env";
import type { AIProviderId } from "./types";

export type AIPlatformConfig = {
  activeProviderId: AIProviderId;
};

export const DEFAULT_AI_CONFIG: AIPlatformConfig = {
  activeProviderId: "deterministic",
};

export function resolveAIConfig(): AIPlatformConfig {
  const candidate = env.aiProviderId;
  if (candidate === "mock" || candidate === "deterministic" || candidate === "backend") {
    return { activeProviderId: candidate };
  }
  return DEFAULT_AI_CONFIG;
}
