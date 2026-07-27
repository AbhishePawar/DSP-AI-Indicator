/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ToastViewport } from "@/components/notifications/ToastViewport";
import type { Notification } from "@/providers/NotificationProvider";

const sample: Notification[] = [
  {
    id: "t1",
    message: "Saved",
    title: "Success",
    tone: "success",
    createdAt: new Date().toISOString(),
    durationMs: 5000,
  },
];

describe("ToastViewport", () => {
  it("renders notifications", () => {
    render(<ToastViewport notifications={sample} onDismiss={() => {}} />);
    expect(screen.getByText("Saved")).toBeTruthy();
    expect(screen.getByLabelText("Notifications")).toBeTruthy();
  });
});
