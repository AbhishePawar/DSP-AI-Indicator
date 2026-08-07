/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { CopilotLayout } from "@/components/copilot/CopilotLayout";
import { modeForQuestion } from "@/lib/copilot/modeMap";
import {
  appendExchange,
  conversationToMarkdown,
  createConversation,
} from "@/lib/copilot/conversation";

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({
    status: "authenticated",
    session: { accessToken: "tok" },
  }),
}));

vi.mock("@/providers/PersistenceProvider", () => ({
  usePersistence: () => ({
    persistCopilotConversations: vi.fn(),
  }),
}));

vi.mock("@/lib/research/sessionStore", () => ({
  loadResearchSession: () => null,
}));

vi.mock("@/lib/copilot/sessionArchive", () => ({
  archiveResearchSession: vi.fn(),
  listArchivedSessions: () => [],
}));

const copilotV2Chat = vi.fn(async () => ({
  ok: true,
  result: {
    conversation_id: "srv-1",
    intent: "valuation",
    answer: "## Margin of Safety\n0.2",
    unavailable: false,
    sources: [{ engine: "valuation_engine", detail: "analyse_or_research_object" }],
  },
}));

vi.mock("@/lib/api/client", () => ({
  api: {
    copilotV2Chat: (...args: unknown[]) => copilotV2Chat(...args),
    copilotHistoryList: vi.fn(async () => ({ ok: true, conversations: [] })),
    copilotHistoryDelete: vi.fn(async () => ({ ok: true, deleted: true })),
  },
}));

describe("copilot v2 helpers", () => {
  it("maps suggested questions to modes", () => {
    expect(modeForQuestion("explain_valuation")).toBe("valuation");
    expect(modeForQuestion("analyze_portfolio")).toBe("portfolio");
    expect(modeForQuestion("buffett")).toBe("buffett");
  });

  it("exports markdown with sources", () => {
    let conv = createConversation("Test");
    conv = appendExchange(conv, "Explain MoS", "## Margin of Safety\n0.2", {
      sources: [{ engine: "valuation_engine" }],
      markdown: true,
    });
    const md = conversationToMarkdown(conv);
    expect(md).toContain("Margin of Safety");
    expect(md).toContain("valuation_engine");
  });
});

describe("CopilotLayout 2.0", () => {
  beforeEach(() => {
    cleanup();
    copilotV2Chat.mockClear();
    Element.prototype.scrollIntoView = vi.fn();
  });

  it("sends chat through Copilot 2.0 orchestration API", async () => {
    render(<CopilotLayout />);
    expect(screen.getByTestId("copilot-v2-layout")).toBeTruthy();
    const input = screen.getByLabelText("Copilot message");
    fireEvent.change(input, { target: { value: "Explain valuation" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    await waitFor(() => expect(copilotV2Chat).toHaveBeenCalled());
    await waitFor(() => {
      expect(screen.getByTestId("copilot-sources")).toBeTruthy();
    });
  });
});
