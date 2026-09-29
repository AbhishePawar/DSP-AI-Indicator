/**
 * @vitest-environment jsdom
 */
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("next/navigation", () => ({
  usePathname: () => "/analysis/compare",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(""),
}));

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({
    status: "authenticated",
    session: {
      accessToken: "tok",
      role: "research_analyst",
      roles: ["research_analyst"],
      permissions: ["read_research"],
    },
  }),
}));

vi.mock("@/providers/NotificationProvider", () => ({
  useNotifications: () => ({
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  }),
}));

vi.mock("@/lib/api/client", () => ({
  api: {
    analyse: vi.fn(),
    researchIntelligencePerformance: vi.fn(),
    researchIntelligenceCalibration: vi.fn(),
    researchIntelligenceTimeline: vi.fn(),
  },
}));

import { CompanyComparisonWorkspace } from "@/components/company-comparison";

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

describe("CompanyComparisonWorkspace render", () => {
  it("renders empty decision workspace shell", () => {
    wrap(<CompanyComparisonWorkspace />);
    expect(
      screen.getByTestId("company-comparison-workspace"),
    ).toBeInTheDocument();
    // The "Compare" title is owned by the route-level Figma page header, so the
    // workspace must not render a second heading.
    expect(
      screen.queryByRole("heading", { name: /^Compare$/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText(/Comparison sections/i)).toBeInTheDocument();
    expect(screen.getByText(/No comparison yet/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Comparison tickers/i)).toBeInTheDocument();
  });
});
