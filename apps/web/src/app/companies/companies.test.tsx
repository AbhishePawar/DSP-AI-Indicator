/**
 * @vitest-environment jsdom
 */
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const push = vi.fn();
const directoryMock = vi.fn();
const searchMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
}));

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({ session: { accessToken: "tok" } }),
}));

vi.mock("@/lib/analysis/recentAnalyses", () => ({
  loadRecentAnalyses: () => [],
}));

vi.mock("@/lib/api/client", () => ({
  api: {
    coverageDirectory: (...args: unknown[]) => directoryMock(...args),
    searchSecurities: (...args: unknown[]) => searchMock(...args),
  },
}));

import CompaniesPage from "./page";

function wrap(ui: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

const directory = {
  ok: true,
  count: 1,
  sectors: ["Technology", "Banking"],
  ratings: ["A+", "A", "B"],
  items: [
    {
      symbol: "INFY",
      company_name: "Infosys Limited",
      exchange: "NSE",
      sector: "Technology",
      industry: null,
      market_cap: 1000,
      rating: "A",
      price: 1500,
      change: null,
      change_percent: null,
      as_of: "2026-01-01T00:00:00Z",
    },
  ],
};

describe("company directory", () => {
  afterEach(() => {
    cleanup();
    directoryMock.mockReset();
    searchMock.mockReset();
    push.mockReset();
  });

  it("loads analysed companies and applies sector and rating filters", async () => {
    directoryMock.mockResolvedValue(directory);
    wrap(<CompaniesPage />);
    expect(await screen.findByText("INFY")).toBeInTheDocument();
    expect(screen.getByText("1,500")).toBeInTheDocument();
    expect(screen.getAllByText("Technology").length).toBeGreaterThan(0);
    expect(screen.getByRole("option", { name: "Banking" })).toBeInTheDocument();
    expect(screen.getAllByText("Data unavailable.").length).toBeGreaterThan(0);

    expect(screen.getByRole("option", { name: "A+" })).toBeInTheDocument();
    expect(screen.getByLabelText("DSP rating")).toBeEnabled();
    fireEvent.change(screen.getByLabelText("Sector"), { target: { value: "Banking" } });
    await waitFor(() =>
      expect(directoryMock).toHaveBeenCalledWith(
        expect.objectContaining({ sector: "Banking", rating: null }),
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "Reset" }));
    await waitFor(() =>
      expect(directoryMock).toHaveBeenLastCalledWith(
        expect.objectContaining({ sector: null, rating: null, q: null }),
      ),
    );

    fireEvent.click(screen.getByRole("button", { name: /INFY/ }));
    expect(push).toHaveBeenCalledWith("/analysis?symbol=INFY&exchange=NSE");
  });

  it("shows an empty state and does not invent a listing", async () => {
    directoryMock.mockResolvedValue({ ...directory, items: [], count: 0, sectors: [] });
    searchMock.mockResolvedValue({ status: "UNKNOWN", results: [] });
    wrap(<CompaniesPage />);
    expect(await screen.findByText("No analysed companies are on record yet.")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Search by name or ticker"), { target: { value: "NOPE" } });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    expect(await screen.findByText("No listings matched this search and these filters.")).toBeInTheDocument();
    expect(screen.queryByText("TCS")).not.toBeInTheDocument();
  });
});
