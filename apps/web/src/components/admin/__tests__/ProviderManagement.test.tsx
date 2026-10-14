/**
 * @vitest-environment jsdom
 */
import type { ReactElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ProviderManagement } from "@/components/admin/ProviderManagement";
import { api } from "@/lib/api/client";
import type { ProviderRecord, TaskRoutingPolicy } from "@/lib/api/providerTypes";

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({
    status: "authenticated",
    session: { accessToken: "test-admin-token" },
    user: { id: "admin-1", email: "admin@dsp.local" },
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

const mockProviders: ProviderRecord[] = [
  {
    provider_id: "gemini",
    display_name: "Google Gemini",
    category: "ai",
    selected_model: "gemini-2.5-pro",
    available_models: ["gemini-2.5-pro", "gemini-2.5-flash"],
    is_active: true,
    has_credential: true,
    health_status: "healthy",
    supported_capabilities: ["chat", "extraction", "reasoning"],
    last_tested_at: "2026-10-14T10:00:00Z",
    last_latency_ms: 185,
    error_message: null,
    version: 2,
    requires_credential: true,
  },
  {
    provider_id: "openai",
    display_name: "OpenAI",
    category: "ai",
    selected_model: "gpt-5o",
    available_models: ["gpt-5o", "gpt-5-mini"],
    is_active: true,
    has_credential: false,
    health_status: "not_configured",
    supported_capabilities: ["chat", "extraction", "tools"],
    last_tested_at: null,
    last_latency_ms: null,
    error_message: null,
    version: 1,
    requires_credential: true,
  },
  {
    provider_id: "upstox",
    display_name: "Upstox Market Data",
    category: "market_data",
    selected_model: "v2-live",
    available_models: ["v2-live"],
    is_active: true,
    has_credential: true,
    health_status: "healthy",
    supported_capabilities: ["quotes", "historical"],
    last_tested_at: "2026-10-14T09:30:00Z",
    last_latency_ms: 65,
    error_message: null,
    version: 1,
    requires_credential: true,
  },
];

const mockPolicies: TaskRoutingPolicy[] = [
  {
    task_id: "equity_research_synthesis",
    primary_provider: "gemini",
    fallback_providers: ["openai"],
    require_independent_corroboration: true,
    timeout_seconds: 30,
    max_retries: 2,
  },
];

vi.mock("@/lib/api/client", () => ({
  api: {
    adminListProviders: vi.fn(async () => ({
      providers: mockProviders,
      total: mockProviders.length,
    })),
    adminGetRoutingPolicies: vi.fn(async () => ({
      policies: mockPolicies,
    })),
    adminTestProvider: vi.fn(async () => ({
      success: true,
      status: "200 OK",
      latency_ms: 120,
      timestamp: "2026-10-14T10:30:00Z",
    })),
    adminSaveProviderCredential: vi.fn(async () => ({
      ok: true,
      provider_id: "openai",
      health_status: "healthy",
      provider: { ...mockProviders[1], has_credential: true, health_status: "healthy" },
    })),
    adminRevokeProviderCredential: vi.fn(async () => ({
      ok: true,
      provider_id: "gemini",
      health_status: "not_configured",
      provider: { ...mockProviders[0], has_credential: false, health_status: "not_configured" },
    })),
    adminUpdateProviderStatus: vi.fn(async () => ({
      ok: true,
      provider: mockProviders[0],
    })),
    adminUpdateProviderModel: vi.fn(async () => ({
      ok: true,
      provider: mockProviders[0],
    })),
    adminRollbackProvider: vi.fn(async () => ({
      ok: true,
      provider: mockProviders[0],
    })),
    adminGetProviderAudit: vi.fn(async () => ({
      provider_id: "gemini",
      audit_log: [],
    })),
    adminUpdateTaskRouting: vi.fn(async () => ({
      ok: true,
      task: "equity_research_synthesis",
      policy: mockPolicies[0],
    })),
  },
}));

function renderWithClient(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

describe("ProviderManagement UI", () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders provider cards and overview counters", async () => {
    renderWithClient(<ProviderManagement />);

    await waitFor(() => {
      expect(screen.getByText("Google Gemini")).toBeTruthy();
    });

    expect(screen.getByText("OpenAI")).toBeTruthy();
    expect(screen.getByText("Upstox Market Data")).toBeTruthy();

    // Metric counters
    expect(screen.getByText("Total Registered")).toBeTruthy();
    expect(screen.getByText("Active for Routing")).toBeTruthy();
    expect(screen.getByText("Credentials Configured")).toBeTruthy();

    // Check badges
    expect(screen.getAllByText("Connection Verified").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Not Configured")).toBeTruthy();
    expect(screen.getAllByText("● Key Configured").length).toBe(2);
    expect(screen.getByText("○ Missing Key")).toBeTruthy();
  });

  it("filters providers by category", async () => {
    renderWithClient(<ProviderManagement />);

    await waitFor(() => {
      expect(screen.getByText("Google Gemini")).toBeTruthy();
    });

    // Click Market Data filter
    const marketDataTab = screen.getByRole("button", { name: /Market Data/i });
    fireEvent.click(marketDataTab);

    expect(screen.getByText("Upstox Market Data")).toBeTruthy();
    expect(screen.queryByText("Google Gemini")).toBeNull();
    expect(screen.queryByText("OpenAI")).toBeNull();

    // Click AI Models filter
    const aiTab = screen.getByRole("button", { name: /AI Models/i });
    fireEvent.click(aiTab);

    expect(screen.getByText("Google Gemini")).toBeTruthy();
    expect(screen.getByText("OpenAI")).toBeTruthy();
    expect(screen.queryByText("Upstox Market Data")).toBeNull();
  });

  it("opens CredentialModal when Add Key or Replace Key is clicked", async () => {
    renderWithClient(<ProviderManagement />);

    await waitFor(() => {
      expect(screen.getByText("OpenAI")).toBeTruthy();
    });

    const addKeyBtn = screen.getByRole("button", { name: /Add Key/i });
    fireEvent.click(addKeyBtn);

    expect(screen.getByText(/Configure OpenAI Credential/i)).toBeTruthy();
    expect(screen.getByPlaceholderText(/Enter OpenAI key\.\.\./i)).toBeTruthy();
  });

  it("tests candidate connection in CredentialModal", async () => {
    renderWithClient(<ProviderManagement />);

    await waitFor(() => {
      expect(screen.getByText("OpenAI")).toBeTruthy();
    });

    const addKeyBtn = screen.getByRole("button", { name: /Add Key/i });
    fireEvent.click(addKeyBtn);

    const input = screen.getByPlaceholderText(/Enter OpenAI key\.\.\./i);
    fireEvent.change(input, { target: { value: "sk-candidate-test-key-12345" } });

    const testBtn = screen.getByRole("button", { name: /Test Connection First/i });
    fireEvent.click(testBtn);

    await waitFor(() => {
      expect(api.adminTestProvider).toHaveBeenCalledWith(
        "openai",
        expect.objectContaining({ secret: "sk-candidate-test-key-12345" }),
        expect.anything(),
      );
    });

    await waitFor(() => {
      expect(screen.getByText(/Connection Successful/i)).toBeTruthy();
      expect(screen.getByText(/120 ms/i)).toBeTruthy();
    });
  });

  it("calls adminRevokeProviderCredential when Revoke button is clicked", async () => {
    window.confirm = vi.fn().mockReturnValue(true);
    vi.mocked(api.adminRevokeProviderCredential).mockResolvedValueOnce({
      ok: true,
      provider_id: "gemini",
      health_status: "not_configured",
      provider: { ...mockProviders[0], has_credential: false, masked_credential: null },
    });

    renderWithClient(<ProviderManagement />);

    await waitFor(() => {
      expect(screen.getByText("Google Gemini")).toBeTruthy();
    });

    const revokeButtons = screen.getAllByRole("button", { name: /^Revoke$/i });
    expect(revokeButtons.length).toBeGreaterThan(0);
    fireEvent.click(revokeButtons[0]);

    await waitFor(() => {
      expect(api.adminRevokeProviderCredential).toHaveBeenCalledWith("gemini", { token: "test-admin-token" });
    });
  });

  it("renders TaskRoutingPanel with primary and fallback options", async () => {
    renderWithClient(<ProviderManagement />);

    await waitFor(() => {
      expect(screen.getByText("Equity Research Synthesis")).toBeTruthy();
    });

    expect(screen.getByText("Independent Corroboration Active")).toBeTruthy();
  });
});
