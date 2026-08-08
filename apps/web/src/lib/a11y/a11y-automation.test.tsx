/**
 * @vitest-environment jsdom
 *
 * EPIC-010 / GA-003 — Accessibility automation (axe + interaction contracts).
 * Quality-only: no product feature or business-logic coverage.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import path from "node:path";

import { A11Y_AUTOMATION_SCOPE, runAxe } from "@/lib/a11y/runAxe";
import { EmptyState } from "@/components/ds/feedback/empty-state";
import { LoadingOverlay } from "@/components/ds/feedback/loading-overlay";
import { Skeleton } from "@/components/ds/feedback/skeleton";
import { ConfirmationDialog } from "@/components/ds/dialogs/confirmation-dialog";
import { Modal } from "@/components/ui/Modal";

describe("EPIC-010 / GA-003 a11y automation catalogue", () => {
  it("documents automated accessibility coverage scope", () => {
    expect([...A11Y_AUTOMATION_SCOPE]).toEqual([
      "keyboard-escape-dialogs",
      "aria-dialog-modal",
      "aria-live-loading",
      "empty-state-status",
      "skeleton-decorative",
      "reduced-motion-hooks",
      "touch-target-conventions",
      "axe-core-component-scan",
    ]);
  });
});

describe("EPIC-010 empty / loading states", () => {
  beforeEach(() => {
    cleanup();
  });

  it("EmptyState exposes polite status role and honest default copy", async () => {
    const { container } = render(
      <EmptyState description="No holdings in this session." />,
    );
    expect(screen.getByRole("status")).toBeTruthy();
    expect(screen.getByText("Data unavailable.")).toBeTruthy();
    expect(await runAxe(container)).toHaveNoViolations();
  });

  it("LoadingOverlay announces busy polite status", async () => {
    const { container } = render(
      <div className="relative h-40">
        <LoadingOverlay label="Loading analysis" />
      </div>,
    );
    // Overlay + Spinner both expose role=status; assert the busy live region.
    const busy = screen
      .getAllByRole("status")
      .find((el) => el.getAttribute("aria-busy") === "true");
    expect(busy).toBeTruthy();
    expect(busy?.getAttribute("aria-live")).toBe("polite");
    expect(await runAxe(container)).toHaveNoViolations();
  });

  it("Skeleton is decorative (aria-hidden) and motion-reduce aware", () => {
    const { container } = render(<Skeleton className="h-8 w-full" />);
    const el = container.firstElementChild as HTMLElement;
    expect(el.getAttribute("aria-hidden")).toBe("true");
    expect(el.className).toContain("motion-reduce:animate-none");
  });
});

describe("EPIC-010 dialogs / keyboard", () => {
  beforeEach(() => {
    cleanup();
  });

  it("Modal exposes dialog semantics and closes on Escape", () => {
    const onClose = vi.fn();
    render(
      <Modal open title="Confirm research action" onClose={onClose}>
        <p>Dialog body</p>
      </Modal>,
    );
    const dialog = screen.getByRole("dialog", { name: "Confirm research action" });
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });

  it("ConfirmationDialog has labelled dialog content and axe-clean surface", async () => {
    const { baseElement } = render(
      <ConfirmationDialog
        open
        onOpenChange={() => undefined}
        title="Discard draft?"
        description="Unsaved research notes will be lost."
        onConfirm={() => undefined}
      />,
    );
    expect(
      screen.getByRole("dialog", { name: "Discard draft?" }),
    ).toBeTruthy();
    expect(screen.getByText("Unsaved research notes will be lost.")).toBeTruthy();
    expect(await runAxe(baseElement)).toHaveNoViolations();
  });
});

describe("EPIC-010 reduced motion + contrast hooks", () => {
  it("applies reduce / more contrast document datasets", async () => {
    const { applyAppearanceToDocument } = await import("@/lib/settings");
    applyAppearanceToDocument({
      density: "comfortable",
      fontSize: "md",
      motionPreference: "reduce",
      contrastPreference: "more",
      focusVisible: true,
    });
    expect(document.documentElement.dataset.motion).toBe("reduce");
    expect(document.documentElement.dataset.contrast).toBe("more");
    expect(document.documentElement.dataset.focusVisible).toBe("on");
  });
});

describe("EPIC-010 touch target conventions (source contracts)", () => {
  it("shell chrome keeps min-h-11 (≥44px) interactive controls", () => {
    const root = path.resolve(__dirname, "../../components/layout");
    const topbar = readFileSync(path.join(root, "Topbar.tsx"), "utf8");
    const sidebar = readFileSync(path.join(root, "Sidebar.tsx"), "utf8");
    expect(topbar).toMatch(/min-h-11/);
    expect(sidebar).toMatch(/min-h-11/);
  });
});
