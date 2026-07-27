import { describe, expect, it, beforeEach } from "vitest";

import { getEmptyPortfolio } from "@/lib/portfolio/data";
import {
  _resetPersistenceStorage,
  createEmptyUserData,
  portfolioViewFromUserPortfolio,
  readUserData,
  sortSavedAnalyses,
  toSavedConversation,
  userPortfolioFromView,
  writeUserData,
} from "@/lib/persistence";
import { createConversation } from "@/lib/copilot/conversation";

describe("persistence storage", () => {
  beforeEach(() => {
    _resetPersistenceStorage();
  });

  it("writes and reads user-scoped bundles", () => {
    const bundle = createEmptyUserData("user-1");
    bundle.savedAnalyses.push({
      id: "saved-1",
      ticker: "AAPL",
      company: "Apple",
      exchange: "NASDAQ",
      recommendation: "Buy",
      analysedAt: "2026-07-27T00:00:00.000Z",
      savedAt: "2026-07-27T01:00:00.000Z",
    });
    writeUserData(bundle);
    const loaded = readUserData("user-1");
    expect(loaded?.savedAnalyses).toHaveLength(1);
    expect(loaded?.savedAnalyses[0]?.ticker).toBe("AAPL");
  });

  it("maps portfolio view to user portfolio and back", () => {
    const view = getEmptyPortfolio();
    const userPortfolio = userPortfolioFromView(view);
    const restored = portfolioViewFromUserPortfolio(userPortfolio);
    expect(restored.holdings).toEqual(view.holdings);
    expect(restored.activities.length).toBeGreaterThan(0);
  });

  it("stores copilot metadata without assistant responses", () => {
    const conversation = createConversation("Test");
    const saved = toSavedConversation(conversation);
    expect(saved.questionHistory).toEqual([]);
    expect(saved.referencedTicker).toBeNull();
    expect(saved.title).toBe("Test");
  });

  it("sorts saved analyses by savedAt desc", () => {
    const sorted = sortSavedAnalyses([
      {
        id: "1",
        ticker: "A",
        company: "A",
        exchange: "—",
        recommendation: "Hold",
        analysedAt: "2026-01-01",
        savedAt: "2026-01-01",
      },
      {
        id: "2",
        ticker: "B",
        company: "B",
        exchange: "—",
        recommendation: "Buy",
        analysedAt: "2026-01-02",
        savedAt: "2026-01-03",
      },
    ]);
    expect(sorted[0]?.ticker).toBe("B");
  });
});
