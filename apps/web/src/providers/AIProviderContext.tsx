"use client";

import {
  createContext,
  useContext,
  useMemo,
  type ReactNode,
} from "react";

import {
  createAIService,
  resolveAIConfig,
  type AIService,
  type AIProviderId,
} from "@/lib/ai";

const AIProviderContext = createContext<AIService | null>(null);

export function AIProviderContextProvider({
  children,
  service,
  activeProviderId,
}: {
  children: ReactNode;
  service?: AIService;
  activeProviderId?: AIProviderId;
}) {
  const value = useMemo(() => {
    if (service) return service;
    const config = activeProviderId
      ? { activeProviderId }
      : resolveAIConfig();
    return createAIService(undefined, config);
  }, [service, activeProviderId]);

  return (
    <AIProviderContext.Provider value={value}>
      {children}
    </AIProviderContext.Provider>
  );
}

export function useAIService(): AIService {
  const ctx = useContext(AIProviderContext);
  if (!ctx) {
    throw new Error("useAIService must be used within AIProviderContextProvider");
  }
  return ctx;
}
