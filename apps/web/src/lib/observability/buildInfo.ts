/**
 * Build & module metadata for diagnostics — placeholders where CI is not wired.
 */

import { getPrimaryNav } from "@/lib/navigation";
import { env } from "@/lib/env";

export type EnabledModule = {
  id: string;
  label: string;
  route: string;
  status: "enabled" | "placeholder";
};

export type FeatureFlagPlaceholder = {
  id: string;
  label: string;
  enabled: boolean;
  note: string;
};

/** Placeholder until CI injects NEXT_PUBLIC_BUILD_TIMESTAMP. */
export const BUILD_TIMESTAMP =
  process.env.NEXT_PUBLIC_BUILD_TIMESTAMP ?? "Not set (local development)";

export const APPLICATION_VERSION = env.frontendVersion;

export function getEnabledModules(): EnabledModule[] {
  return getPrimaryNav().map((item) => ({
    id: item.href.replace(/^\//, "").replace(/\//g, "-") || "root",
    label: item.label,
    route: item.href,
    status: "enabled" as const,
  }));
}

/** Placeholder feature flags — no backend flag service in EPIC-007. */
export function getFeatureFlagPlaceholders(): FeatureFlagPlaceholder[] {
  return [
    {
      id: "research_mode",
      label: "Research Mode",
      enabled: true,
      note: "Always on — compliance default",
    },
    {
      id: "advisor_demo",
      label: "Advisor Demo",
      enabled: process.env.NEXT_PUBLIC_ADVISOR_DEMO === "true",
      note: "NEXT_PUBLIC_ADVISOR_DEMO",
    },
    {
      id: "copilot_llm",
      label: "Copilot LLM",
      enabled: process.env.NEXT_PUBLIC_AI_PROVIDER === "backend",
      note: "Backend-routed via /api/v1/copilot (EPIC-012)",
    },
    {
      id: "live_market_data",
      label: "Authenticated Market Data",
      enabled: true,
      note: "GET /api/v1/market/quote only; never fabricated (P0-03)",
    },
    {
      id: "external_telemetry",
      label: "External Telemetry",
      enabled: false,
      note: "Logger abstraction ready; no exporter wired",
    },
  ];
}

export function getBuildInfo() {
  return {
    applicationVersion: APPLICATION_VERSION,
    frontendVersion: env.frontendVersion,
    appName: env.appName,
    environment: env.environment,
    apiBaseUrl: env.apiBaseUrl,
    buildTimestamp: BUILD_TIMESTAMP,
    nodeEnv: process.env.NODE_ENV ?? "development",
  };
}
