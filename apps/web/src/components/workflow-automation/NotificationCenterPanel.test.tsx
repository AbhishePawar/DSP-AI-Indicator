/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { NotificationCenterPanel } from "./NotificationCenterPanel";

const markReadMock = vi.fn();
let notificationsFixture: unknown[] = [];

vi.mock("@/lib/workflow-automation/useWorkflowAutomation", () => ({
  useNotifications: vi.fn(() => ({
    notifications: notificationsFixture,
    isLoading: false,
    markRead: { mutate: markReadMock, isPending: false },
  })),
}));

afterEach(() => {
  cleanup();
  notificationsFixture = [];
  markReadMock.mockClear();
});

describe("NotificationCenterPanel", () => {
  it("shows an honest empty state with no notifications", () => {
    render(<NotificationCenterPanel token="tok" />);
    expect(screen.getByText(/no notifications yet/i)).toBeTruthy();
  });

  it("renders unread notifications with a Mark read action", () => {
    notificationsFixture = [
      {
        notification_id: "ntf_1",
        user_id: "u1",
        kind: "alert",
        title: "Price alert",
        message: "AAPL hit $200",
        related_rule_id: "alr_1",
        related_schedule_id: null,
        read_at: null,
        created_at: "2024-01-01T00:00:00Z",
      },
    ];
    render(<NotificationCenterPanel token="tok" />);
    expect(screen.getByText("Price alert")).toBeTruthy();
    expect(screen.getByText("New")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /mark read/i }));
    expect(markReadMock).toHaveBeenCalledWith("ntf_1");
  });

  it("does not show Mark read for already-read notifications", () => {
    notificationsFixture = [
      {
        notification_id: "ntf_2",
        user_id: "u1",
        kind: "alert",
        title: "Old alert",
        message: "message",
        related_rule_id: null,
        related_schedule_id: null,
        read_at: "2024-01-02T00:00:00Z",
        created_at: "2024-01-01T00:00:00Z",
      },
    ];
    render(<NotificationCenterPanel token="tok" />);
    expect(screen.queryByRole("button", { name: /mark read/i })).toBeNull();
  });
});
