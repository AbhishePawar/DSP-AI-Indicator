import type { PortfolioView } from "@/lib/portfolio/model";
import { buildPortfolioView } from "@/lib/portfolio/data";
import type { CopilotConversation } from "@/lib/copilot/types";
import type { SavedAnalysis, SavedConversation, UserPortfolio } from "./types";
import { createEmptyUserPortfolio } from "./types";

export function userPortfolioFromView(
  view: PortfolioView,
  existing?: UserPortfolio | null,
): UserPortfolio {
  const now = new Date().toISOString();
  const base = existing ?? createEmptyUserPortfolio();
  return {
    ...base,
    holdings: view.holdings,
    activities: view.activities,
    metadata: {
      createdAt: base.metadata.createdAt,
      updatedAt: now,
    },
  };
}

export function portfolioViewFromUserPortfolio(
  portfolio: UserPortfolio,
): PortfolioView {
  return buildPortfolioView(portfolio.holdings, portfolio.activities);
}

export function toSavedConversation(
  conversation: CopilotConversation,
): SavedConversation {
  return {
    id: conversation.id,
    title: conversation.title,
    createdAt: conversation.createdAt,
    updatedAt: conversation.updatedAt,
    referencedTicker: conversation.context.lastTicker,
    questionHistory: conversation.messages
      .filter((message) => message.role === "user")
      .map((message) => message.content),
  };
}

export function createSavedAnalysisId(): string {
  return `saved-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function sortSavedAnalyses(analyses: SavedAnalysis[]): SavedAnalysis[] {
  return [...analyses].sort(
    (a, b) => new Date(b.savedAt).getTime() - new Date(a.savedAt).getTime(),
  );
}
