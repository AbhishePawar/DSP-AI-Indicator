"use client";

import { useEffect, useState } from "react";

import { api, type SecuritySearchCandidate } from "@/lib/api/client";
import { ApiClientError } from "@/lib/api/types";
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

const UNAVAILABLE_COPY = "Company search is temporarily unavailable.";
const SIGN_IN_COPY = "Sign in to search the official security universe.";

export function analysisHref(candidate: SecuritySearchCandidate): string {
  const params = new URLSearchParams();
  params.set("symbol", candidate.trading_symbol);
  if (candidate.exchange) params.set("exchange", candidate.exchange);
  if (candidate.isin) params.set("isin", candidate.isin);
  return `/analysis?${params.toString()}`;
}

export function publicSearchMessage(
  resolution: string,
  serverMessage: string,
  status?: number,
): string {
  const internal =
    /http\s*\d|cloud run|traceback|exception|postgres|sql|internal/i.test(
      serverMessage,
    );
  if (status === 401 || status === 403) return SIGN_IN_COPY;
  if (status === 404 || status === 503 || status === 502 || status === 0) {
    return UNAVAILABLE_COPY;
  }
  if (internal) return UNAVAILABLE_COPY;
  if (resolution === "UNSUPPORTED") {
    return "This security is not currently supported for DSP analysis.";
  }
  if (resolution === "AMBIGUOUS" || resolution === "DUAL_LISTING_CANDIDATES") {
    return serverMessage.trim() || "Multiple securities found. Select the exchange.";
  }
  if (resolution === "NONE" || resolution === "EMPTY") {
    return "No supported security found.";
  }
  return serverMessage.trim() || UNAVAILABLE_COPY;
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
        message: SIGN_IN_COPY,
        candidates: [],
      });
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setState((prev) => ({ ...prev, query: trimmed, loading: true }));
      void api
        .searchSecurities(
          { q: trimmed, limit: 12 },
          { token, signal: controller.signal },
        )
        .then((payload) => {
          const resolution = payload.resolution || "";
          setState({
            query: trimmed,
            loading: false,
            available: Boolean(payload.available),
            resolution,
            message: publicSearchMessage(
              resolution,
              payload.message || "",
            ),
            candidates: payload.candidates ?? [],
          });
        })
        .catch((error: unknown) => {
          if (controller.signal.aborted) return;
          const status = error instanceof ApiClientError ? error.status : undefined;
          const raw =
            error instanceof Error ? error.message : UNAVAILABLE_COPY;
          setState({
            query: trimmed,
            loading: false,
            available: false,
            resolution: "UNAVAILABLE",
            message: publicSearchMessage("UNAVAILABLE", raw, status),
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
