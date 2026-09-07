"use client";

import { useEffect, useState } from "react";

import { api, type SecuritySearchCandidate } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";

export type SecuritySearchState = {
  query: string;
  loading: boolean;
  available: boolean;
  resolution: string;
  message: string;
  candidates: SecuritySearchCandidate[];
};

const EMPTY: SecuritySearchState = {
  query: "",
  loading: false,
  available: true,
  resolution: "",
  message: "",
  candidates: [],
};

export function analysisHref(candidate: SecuritySearchCandidate): string {
  const params = new URLSearchParams();
  params.set("symbol", candidate.trading_symbol);
  if (candidate.exchange) params.set("exchange", candidate.exchange);
  if (candidate.isin) params.set("isin", candidate.isin);
  return `/analysis?${params.toString()}`;
}

export function useSecurityMasterSearch(query: string): SecuritySearchState {
  const { session } = useAuth();
  const token = session?.accessToken;
  const [state, setState] = useState<SecuritySearchState>(EMPTY);

  useEffect(() => {
    const trimmed = query.trim();
    if (!trimmed) {
      setState(EMPTY);
      return;
    }
    if (!token) {
      setState({
        query: trimmed,
        loading: false,
        available: false,
        resolution: "UNAVAILABLE",
        message: "Sign in required to search the official security universe.",
        candidates: [],
      });
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setState((prev) => ({ ...prev, query: trimmed, loading: true }));
      void api
        .searchSecurities({ q: trimmed, limit: 12 }, { token, signal: controller.signal })
        .then((payload) => {
          setState({
            query: trimmed,
            loading: false,
            available: Boolean(payload.available),
            resolution: payload.resolution,
            message: payload.message || "",
            candidates: payload.candidates ?? [],
          });
        })
        .catch((error: unknown) => {
          if (controller.signal.aborted) return;
          const message =
            error instanceof Error ? error.message : "Data unavailable.";
          setState({
            query: trimmed,
            loading: false,
            available: false,
            resolution: "UNAVAILABLE",
            message: message || "Data unavailable.",
            candidates: [],
          });
        });
    }, 250);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [query, token]);

  return state;
}
