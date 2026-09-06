/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
}));

import { SearchFirstDashboard } from "@/components/dashboard/SearchFirstDashboard";

describe("SIMPLE-2 SearchFirstDashboard", () => {
  it("renders the search-first prompt without institutional widgets", () => {
    cleanup();
    render(<SearchFirstDashboard />);
    expect(
      screen.getByRole("heading", {
        name: /What company would you like to research\?/i,
      }),
    ).toBeTruthy();
    expect(screen.getByLabelText(/Search a company or stock/i)).toBeTruthy();
    expect(screen.queryByLabelText("Dashboard widgets")).toBeNull();
    expect(screen.queryByRole("heading", { name: "Executive Dashboard" })).toBeNull();
    expect(screen.queryByText(/ready=true/i)).toBeNull();
  });
});
