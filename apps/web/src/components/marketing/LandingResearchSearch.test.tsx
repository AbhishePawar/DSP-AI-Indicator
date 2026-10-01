/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { useDashboardPrefsStore } from "@/lib/dashboard/dashboardPrefsStore";

const push = vi.fn();
const authState = { status: "unauthenticated" as "authenticated" | "unauthenticated" };

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({ status: authState.status }),
}));

import { LandingResearchSearch } from "./LandingResearchSearch";

beforeEach(() => {
  cleanup();
  push.mockReset();
  authState.status = "unauthenticated";
  useDashboardPrefsStore.setState({ recentSearches: [] });
});

describe("Landing research search", () => {
  it("does not invent trending tickers", () => {
    render(<LandingResearchSearch />);
    expect(screen.getByText("Trending unavailable.")).toBeTruthy();
    expect(screen.queryByText("TCS")).toBeNull();
    expect(screen.queryByText(/Your Recent Searches/i)).toBeNull();
  });

  it("shows the signed-in user's saved searches and records a new one", () => {
    authState.status = "authenticated";
    useDashboardPrefsStore.setState({
      recentSearches: [{ query: "INFY", at: "2026-10-01T00:00:00.000Z" }],
    });
    render(<LandingResearchSearch />);
    expect(screen.getByRole("button", { name: "INFY" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "INFY" }));
    fireEvent.click(screen.getByRole("button", { name: /simple research/i }));
    expect(push).toHaveBeenCalledWith("/analysis?symbol=INFY&mode=simple");
    expect(useDashboardPrefsStore.getState().recentSearches[0]?.query).toBe("INFY");
  });
});
