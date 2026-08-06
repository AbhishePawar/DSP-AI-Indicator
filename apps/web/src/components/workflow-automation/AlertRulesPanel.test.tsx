/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { AlertRulesPanel } from "./AlertRulesPanel";

const mutateMock = vi.fn();
const evaluateMutateMock = vi.fn();

vi.mock("@/lib/workflow-automation/useWorkflowAutomation", () => ({
  useAlertRules: vi.fn(() => ({
    rules: [
      {
        rule_id: "alr_1",
        user_id: "u1",
        rule_type: "price_above",
        symbol: "AAPL",
        portfolio_id: null,
        active: true,
        params: { threshold_price: 200 },
        last_evaluated_at: null,
        last_status: null,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      },
    ],
    isLoading: false,
    createRule: { mutate: mutateMock, isPending: false },
    updateRule: { mutate: vi.fn(), isPending: false },
    deleteRule: { mutate: vi.fn(), isPending: false },
  })),
  useEvaluateAlerts: vi.fn(() => ({
    mutate: evaluateMutateMock,
    isPending: false,
    data: undefined,
  })),
}));

afterEach(() => {
  cleanup();
});

describe("AlertRulesPanel", () => {
  it("renders existing alert rules with type label and params summary", () => {
    render(<AlertRulesPanel token="tok" defaultPortfolioId={null} />);
    expect(screen.getByText("AAPL")).toBeTruthy();
    expect(screen.getByText("Threshold 200")).toBeTruthy();
  });

  it("has a Check now button that triggers evaluation", () => {
    render(<AlertRulesPanel token="tok" defaultPortfolioId={null} />);
    fireEvent.click(screen.getByRole("button", { name: /check now/i }));
    expect(evaluateMutateMock).toHaveBeenCalledWith(null);
  });

  it("submitting the create form calls createRule.mutate", () => {
    render(<AlertRulesPanel token="tok" defaultPortfolioId={null} />);
    const symbolInput = screen.getByLabelText(/symbol/i);
    fireEvent.change(symbolInput, { target: { value: "MSFT" } });
    fireEvent.click(screen.getByRole("button", { name: /add rule/i }));
    expect(mutateMock).toHaveBeenCalledWith(
      expect.objectContaining({ rule_type: "price_above", symbol: "MSFT" }),
    );
  });
});
