/** EPIC-009 — User-owned persistence models (frontend cache, user-scoped). */

import type { AnalyseRequest, AnalyseResponse } from "@/lib/api/compositionTypes";
import type {
  PortfolioActivity,
  PortfolioHolding,
} from "@/lib/portfolio/model";
import type { ThemeMode } from "@/providers/ThemeProvider";

export type SyncStatus =
  | "idle"
  | "loading"
  | "saving"
  | "saved"
  | "error"
  | "conflict";

export type UserPortfolio = {
  id: string;
  name: string;
  holdings: PortfolioHolding[];
  activities: PortfolioActivity[];
  metadata: {
    createdAt: string;
    updatedAt: string;
  };
};

export type SavedAnalysis = {
  id: string;
  ticker: string;
  company: string;
  exchange: string;
  recommendation: string;
  analysedAt: string;
  savedAt: string;
  label?: string;
  request?: AnalyseRequest;
  response?: AnalyseResponse;
};

export type SavedConversation = {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  referencedTicker: string | null;
  questionHistory: string[];
};

export type UserPreference = {
  theme: ThemeMode;
  defaultLandingPage: string;
  /** Placeholder until watchlist epic. */
  preferredWatchlistView: string | null;
};

export type UserDataBundle = {
  version: 1;
  subject: string;
  updatedAt: string;
  portfolio: UserPortfolio;
  savedAnalyses: SavedAnalysis[];
  copilotConversations: SavedConversation[];
  preferences: UserPreference;
};

export const DEFAULT_PREFERENCES: UserPreference = {
  theme: "system",
  defaultLandingPage: "/dashboard",
  preferredWatchlistView: null,
};

export function createEmptyUserPortfolio(): UserPortfolio {
  const now = new Date().toISOString();
  return {
    id: `portfolio-${now}`,
    name: "My Portfolio",
    holdings: [],
    activities: [
      {
        id: `act-${now}`,
        label: "Portfolio Created",
        timestamp: now,
      },
    ],
    metadata: { createdAt: now, updatedAt: now },
  };
}

export function createEmptyUserData(subject: string): UserDataBundle {
  const now = new Date().toISOString();
  return {
    version: 1,
    subject,
    updatedAt: now,
    portfolio: createEmptyUserPortfolio(),
    savedAnalyses: [],
    copilotConversations: [],
    preferences: { ...DEFAULT_PREFERENCES },
  };
}
