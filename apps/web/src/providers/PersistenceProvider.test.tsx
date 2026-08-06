/**
 * @vitest-environment jsdom
 * RC1 Milestone 3 — Migration strategy tests for PersistenceProvider.
 *
 * Verifies: IF server portfolio exists -> use it. ELSE IF local exists ->
 * migrate to server, notify success, keep local copy. Never silently
 * deletes local data.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";

const apiMock = vi.hoisted(() => ({
  portfolioList: vi.fn(),
  portfolioListHoldings: vi.fn(),
  portfolioMigrate: vi.fn(),
  portfolioUpsertHolding: vi.fn(),
  portfolioRemoveHolding: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({ api: apiMock }));

vi.mock("@/providers/ThemeProvider", () => ({
  useTheme: () => ({ mode: "system", resolved: "light", setMode: vi.fn(), cycleMode: vi.fn() }),
}));

let mockStatus: "authenticated" | "unauthenticated" = "authenticated";
let mockSubject = "u1";

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({
    status: mockStatus,
    session:
      mockStatus === "authenticated"
        ? { accessToken: "tok", subject: mockSubject }
        : null,
  }),
}));

import {
  _resetPersistenceStorage,
  readUserData,
  writeUserData,
} from "@/lib/persistence";
import { createEmptyUserData } from "@/lib/persistence/types";
import { PersistenceProvider, usePersistence } from "./PersistenceProvider";

function Probe() {
  const {
    isLoaded,
    portfolioView,
    serverPortfolioId,
    portfolioSyncStatus,
    portfolioSyncError,
  } = usePersistence();
  return (
    <div>
      <span data-testid="loaded">{String(isLoaded)}</span>
      <span data-testid="server-id">{serverPortfolioId ?? "none"}</span>
      <span data-testid="sync-status">{portfolioSyncStatus}</span>
      <span data-testid="sync-error">{portfolioSyncError ?? "none"}</span>
      <span data-testid="holding-count">{portfolioView?.holdings.length ?? 0}</span>
      <ul data-testid="holdings">
        {portfolioView?.holdings.map((h) => <li key={h.ticker}>{h.ticker}</li>)}
      </ul>
    </div>
  );
}

function renderProbe() {
  return render(
    <PersistenceProvider>
      <Probe />
    </PersistenceProvider>,
  );
}

beforeEach(() => {
  cleanup();
  vi.clearAllMocks();
  _resetPersistenceStorage();
  mockStatus = "authenticated";
  mockSubject = "u1";
});

describe("PersistenceProvider — migration strategy", () => {
  it("uses the server portfolio when one already exists", async () => {
    apiMock.portfolioList.mockResolvedValue({
      ok: true,
      result: [
        {
          portfolio_id: "pf_server",
          user_id: "u1",
          org_id: null,
          name: "Server Portfolio",
          is_default: true,
          benchmark_symbol: "SPY",
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
          metadata: {},
        },
      ],
    });
    apiMock.portfolioListHoldings.mockResolvedValue({
      ok: true,
      result: [
        {
          holding_id: "hld_1",
          portfolio_id: "pf_server",
          symbol: "AAPL",
          weight: 1,
          units: null,
          cost_basis_per_unit: null,
          purchase_date: null,
          sector: "Technology",
          country: null,
          exchange: null,
          value_score: null,
          quality_score: null,
          momentum_score: null,
          size_score: null,
          volatility_score: null,
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
        },
      ],
    });

    renderProbe();

    await waitFor(() => {
      expect(screen.getByTestId("server-id").textContent).toBe("pf_server");
    });
    expect(screen.getByTestId("sync-status").textContent).toBe("synced");
    expect(screen.getByTestId("holdings").textContent).toContain("AAPL");
    expect(apiMock.portfolioMigrate).not.toHaveBeenCalled();
  });

  it("migrates the local snapshot to the server when none exists yet", async () => {
    const bundle = createEmptyUserData("u1");
    bundle.portfolio.holdings = [
      {
        company: "Apple",
        ticker: "AAPL",
        sector: "Technology",
        allocationPercent: 100,
        recommendation: "Data unavailable.",
        researchAvailable: false,
      },
    ];
    writeUserData(bundle);

    apiMock.portfolioList.mockResolvedValue({ ok: true, result: [] });
    apiMock.portfolioMigrate.mockResolvedValue({
      ok: true,
      result: {
        migrated: true,
        portfolio: {
          portfolio_id: "pf_migrated",
          user_id: "u1",
          org_id: null,
          name: "My Portfolio",
          is_default: true,
          benchmark_symbol: null,
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
          metadata: {},
        },
      },
    });

    renderProbe();

    await waitFor(() => {
      expect(screen.getByTestId("server-id").textContent).toBe("pf_migrated");
    });
    expect(apiMock.portfolioMigrate).toHaveBeenCalledTimes(1);
    expect(apiMock.portfolioMigrate).toHaveBeenCalledWith(
      expect.objectContaining({
        holdings: [{ symbol: "AAPL", weight: 1, sector: "Technology" }],
      }),
      { token: "tok" },
    );

    // Never silently deletes local data — the localStorage copy still exists.
    const local = readUserData("u1");
    expect(local?.portfolio.holdings).toHaveLength(1);
  });

  it("migrates even an empty local portfolio (creates an empty default)", async () => {
    apiMock.portfolioList.mockResolvedValue({ ok: true, result: [] });
    apiMock.portfolioMigrate.mockResolvedValue({
      ok: true,
      result: {
        migrated: true,
        portfolio: {
          portfolio_id: "pf_empty",
          user_id: "u1",
          org_id: null,
          name: "My Portfolio",
          is_default: true,
          benchmark_symbol: null,
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
          metadata: {},
        },
      },
    });

    renderProbe();

    await waitFor(() => {
      expect(screen.getByTestId("server-id").textContent).toBe("pf_empty");
    });
    expect(apiMock.portfolioMigrate).toHaveBeenCalledWith(
      expect.objectContaining({ holdings: [] }),
      { token: "tok" },
    );
  });

  it("degrades honestly (keeps local data) when the server call fails", async () => {
    const bundle = createEmptyUserData("u1");
    bundle.portfolio.holdings = [
      {
        company: "Apple",
        ticker: "AAPL",
        sector: "Technology",
        allocationPercent: 100,
        recommendation: "Data unavailable.",
        researchAvailable: false,
      },
    ];
    writeUserData(bundle);

    apiMock.portfolioList.mockRejectedValue(new Error("network down"));

    renderProbe();

    await waitFor(() => {
      expect(screen.getByTestId("sync-status").textContent).toBe("error");
    });
    expect(screen.getByTestId("server-id").textContent).toBe("none");
    expect(screen.getByTestId("sync-error").textContent).toBe("network down");
    // Local data remains fully intact and visible.
    expect(screen.getByTestId("holding-count").textContent).toBe("1");
    const local = readUserData("u1");
    expect(local?.portfolio.holdings).toHaveLength(1);
  });

  it("does not attempt any server call when unauthenticated", async () => {
    mockStatus = "unauthenticated";
    renderProbe();
    await waitFor(() => {
      expect(screen.getByTestId("loaded").textContent).toBe("true");
    });
    expect(apiMock.portfolioList).not.toHaveBeenCalled();
    expect(apiMock.portfolioMigrate).not.toHaveBeenCalled();
  });

  it("only attempts migration once per subject (no duplicate calls on rerender)", async () => {
    apiMock.portfolioList.mockResolvedValue({ ok: true, result: [] });
    apiMock.portfolioMigrate.mockResolvedValue({
      ok: true,
      result: {
        migrated: true,
        portfolio: {
          portfolio_id: "pf_once",
          user_id: "u1",
          org_id: null,
          name: "My Portfolio",
          is_default: true,
          benchmark_symbol: null,
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
          metadata: {},
        },
      },
    });

    const { rerender } = renderProbe();
    await waitFor(() => {
      expect(screen.getByTestId("server-id").textContent).toBe("pf_once");
    });

    rerender(
      <PersistenceProvider>
        <Probe />
      </PersistenceProvider>,
    );

    await act(async () => {
      await Promise.resolve();
    });
    expect(apiMock.portfolioMigrate).toHaveBeenCalledTimes(1);
  });
});
