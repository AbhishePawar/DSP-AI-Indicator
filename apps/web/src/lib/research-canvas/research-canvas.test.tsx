/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  usePathname: () => "/research/canvas",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams("tab=overview"),
}));

vi.mock("@/lib/a11y", () => ({
  useCollapsePanelsBelowLg: () => undefined,
}));

import {
  CANVAS_TABS,
  NOTEBOOK_KINDS,
  asCanvasTabId,
  composeResearchTimeline,
  filterResearchQuickActions,
  isCanvasTabId,
  searchResearchCanvas,
  useResearchNotebookStore,
} from "@/lib/research-canvas";
import { filterShellNav, searchableRoutes } from "@/lib/shell/navigationRegistry";
import { featureFlags } from "@/lib/featureFlags";
import { ResearchCanvasWorkspace } from "@/components/research-canvas";

describe("EPIC-014 Research Canvas", () => {
  beforeEach(() => {
    cleanup();
    useResearchNotebookStore.setState({
      entries: [],
      savedSessions: [],
      bookmarks: [],
    });
  });

  it("registers institutional workspace tabs", () => {
    const ids = CANVAS_TABS.map((t) => t.id);
    expect(ids).toEqual(
      expect.arrayContaining([
        "overview",
        "financials",
        "valuation",
        "bq",
        "management",
        "moat",
        "risk",
        "researchIntelligence",
        "comparison",
        "timeline",
        "committee",
        "explainability",
        "evidence",
        "notes",
      ]),
    );
    expect(isCanvasTabId("valuation")).toBe(true);
    expect(asCanvasTabId("nope")).toBe("overview");
  });

  it("keeps notebook entries user-authored and isolated", () => {
    const { addEntry, entries } = useResearchNotebookStore.getState();
    addEntry("thesis", "My thesis", "AAPL");
    addEntry("note", "  ", "AAPL"); // ignored
    const next = useResearchNotebookStore.getState().entries;
    expect(next).toHaveLength(1);
    expect(next[0].kind).toBe("thesis");
    expect(next[0].symbol).toBe("AAPL");
    expect(NOTEBOOK_KINDS).toContain("thesis");
    // Isolation: notebook store never claims to be institutional research
    expect(entries).not.toBe(next);
    expect(next[0].text).not.toMatch(/institutional research output/i);
  });

  it("composes honest timeline when empty", () => {
    const events = composeResearchTimeline({ symbol: "ZZZZ" });
    expect(events.some((e) => e.kind === "unavailable")).toBe(true);
    expect(events[0].detail.toLowerCase()).toContain("unavailable");
  });

  it("searches companies and tabs client-side", () => {
    useResearchNotebookStore.getState().addEntry("question", "Moat durability?", "AAPL");
    const hits = searchResearchCanvas({
      query: "aapl",
      notebookEntries: useResearchNotebookStore.getState().entries,
    });
    expect(hits.some((h) => h.group === "Companies")).toBe(true);
    expect(hits.some((h) => h.group === "Notes")).toBe(true);
  });

  it("RBAC-filters quick actions and surfaces canvas in shell nav", () => {
    const actions = filterResearchQuickActions(
      ["read_research"],
      ["research_analyst"],
    );
    expect(actions.map((a) => a.id)).toEqual(
      expect.arrayContaining([
        "qa-open-company",
        "qa-canvas",
        "qa-portfolio",
        "qa-notes",
      ]),
    );

    const visible = filterShellNav(["read_research"], ["research_analyst"]);
    const research = visible.find((n) => n.id === "research");
    expect(
      research?.children?.some((c) => c.href === "/research/canvas"),
    ).toBe(featureFlags.researchCanvas);

    const routes = searchableRoutes(
      ["read_research"],
      ["research_analyst"],
    ).map((r) => r.path);
    if (featureFlags.researchCanvas) {
      expect(routes).toContain("/research/canvas");
    }
  });

  it("renders canvas shell with navigator and notebook regions", () => {
    if (!featureFlags.researchCanvas) return;
    render(<ResearchCanvasWorkspace />);
    expect(
      screen.getByRole("navigation", { name: /research navigator/i }),
    ).toBeTruthy();
    expect(
      screen.getByRole("tablist", { name: /research workspace tabs/i }),
    ).toBeTruthy();
    expect(
      screen.getByLabelText(/research notebook/i),
    ).toBeTruthy();
  });
});
