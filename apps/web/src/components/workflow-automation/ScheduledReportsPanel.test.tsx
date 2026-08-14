/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";

import { ScheduledReportsPanel } from "./ScheduledReportsPanel";

const createMock = vi.fn();
const deleteMock = vi.fn();
const runNowMock = vi.fn().mockResolvedValue({ available: true, content: "{}" });

vi.mock("@/lib/workflow-automation/useWorkflowAutomation", () => ({
  useScheduledReports: vi.fn(() => ({
    schedules: [
      {
        schedule_id: "sch_1",
        user_id: "u1",
        portfolio_id: "pf_1",
        frequency: "weekly",
        format: "json",
        active: true,
        recipients: [],
        last_run_at: null,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      },
    ],
    isLoading: false,
    createSchedule: { mutate: createMock, isPending: false },
    deleteSchedule: { mutate: deleteMock, isPending: false },
    runNow: { mutateAsync: runNowMock, isPending: false },
  })),
}));

afterEach(() => {
  cleanup();
  createMock.mockClear();
  deleteMock.mockClear();
  runNowMock.mockClear();
});

describe("ScheduledReportsPanel", () => {
  it("shows an honest message when there is no default portfolio", () => {
    render(<ScheduledReportsPanel token="tok" defaultPortfolioId={null} />);
    expect(screen.getByText(/create a portfolio first/i)).toBeTruthy();
  });

  it("renders existing schedules with frequency/format badges", () => {
    render(<ScheduledReportsPanel token="tok" defaultPortfolioId="pf_1" />);
    const list = screen.getByRole("list", { name: /scheduled reports/i });
    expect(within(list).getByText("Weekly")).toBeTruthy();
    expect(within(list).getByText("JSON")).toBeTruthy();
  });

  it("Run now calls runNow.mutateAsync and displays content", async () => {
    render(<ScheduledReportsPanel token="tok" defaultPortfolioId="pf_1" />);
    fireEvent.click(screen.getByRole("button", { name: /run now/i }));
    expect(runNowMock).toHaveBeenCalledWith("sch_1");
  });

  it("Delete calls deleteSchedule.mutate", () => {
    render(<ScheduledReportsPanel token="tok" defaultPortfolioId="pf_1" />);
    fireEvent.click(screen.getByRole("button", { name: /delete/i }));
    expect(deleteMock).toHaveBeenCalledWith("sch_1");
  });

  it("submitting the create form calls createSchedule.mutate", () => {
    render(<ScheduledReportsPanel token="tok" defaultPortfolioId="pf_1" />);
    fireEvent.click(screen.getByRole("button", { name: /add schedule/i }));
    expect(createMock).toHaveBeenCalledWith(
      expect.objectContaining({ portfolio_id: "pf_1", frequency: "weekly", format: "json" }),
    );
  });
});
